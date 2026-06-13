import os, sys

os.environ["PATH"] = os.environ["PATH"] + ":/usr/local/cuda/bin/"  # adding this line
sys.path.append(os.path.join(os.getcwd(), "GroundingDINO"))

import argparse
import copy
import locale

import csv
import json
import random

from PIL import Image, ImageDraw, ImageFont
from skimage.measure import find_contours


# Grounding DINO
from GroundingDINO.groundingdino.models import build_model
from GroundingDINO.groundingdino.util import box_ops
from GroundingDINO.groundingdino.util.slconfig import SLConfig
from GroundingDINO.groundingdino.util.utils import clean_state_dict, get_phrases_from_posmap
from GroundingDINO.groundingdino.util.inference import annotate, load_image, predict

import supervision as sv

# segment anything
from GroundedSegmentAnything.segment_anything.build.lib.segment_anything.predictor import SamPredictor
from GroundedSegmentAnything.segment_anything.build.lib.segment_anything.build_sam import build_sam

print(GroundedSegmentAnything.__file__)
print(GroundingDINO.__file__)

import cv2
import numpy as np

import matplotlib.pyplot as plt

# diffusers
import PIL
import requests
import torch
from io import BytesIO
from diffusers import StableDiffusionInpaintPipeline

from huggingface_hub import hf_hub_download
import itertools

import re
from pathlib import Path
import time

print("end of imports")


def load_model_hf(repo_id, filename, ckpt_config_filename, device='cpu'):
    cache_config_file = hf_hub_download(repo_id=repo_id, filename=ckpt_config_filename)

    args = SLConfig.fromfile(cache_config_file)
    args.device = device
    model = build_model(args)

    cache_file = hf_hub_download(repo_id=repo_id, filename=filename)
    checkpoint = torch.load(cache_file, map_location=device)
    log = model.load_state_dict(clean_state_dict(checkpoint['model']), strict=False)
    print("Model loaded from {} \n => {}".format(cache_file, log))
    _ = model.eval()
    return model


def save_image(img_path, image_array, save_folder, num_detections):
    # Extract image name from the path
    img_name = os.path.basename(img_path)

    addition_to_img_name = f"{num_detections}_segmented_{img_name}"
    # Create the save path in the specified folder
    save_img_path = os.path.join(save_folder, addition_to_img_name)

    # Ensure the image is in the correct color space (RGB to BGR for OpenCV saving)
    if len(image_array.shape) == 3 and image_array.shape[2] == 4:  # RGBA
        image_array = cv2.cvtColor(image_array, cv2.COLOR_RGBA2BGR)
    elif len(image_array.shape) == 3 and image_array.shape[2] == 3:  # RGB
        image_array = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)

    # Save the image to the specified path
    cv2.imwrite(save_img_path, image_array)

    return save_img_path


def show_img(image_source):
    rotated_k = 4
    fig = plt.figure(figsize=(14, 14))
    arr = np.rot90(image_source, k=rotated_k)
    plt.imshow(arr)
    plt.show()


def load_img(img_name):
    local_image_path = img_name

    image_source, image = load_image(local_image_path)
    # show_img(image_source=image_source)
    return image_source, image


# detect object using grounding DINO
def detect(image, image_source, text_prompt, model, box_threshold=0.30, text_threshold=0.25):
    boxes, logits, phrases = predict(
        model=model,
        image=image,
        caption=text_prompt,
        box_threshold=box_threshold,
        text_threshold=text_threshold
    )

    annotated_frame = annotate(image_source=image_source, boxes=boxes, logits=logits, phrases=phrases)
    annotated_frame = annotated_frame[..., ::-1]  # BGR to RGB
    return annotated_frame, boxes, phrases, logits


def segment(image, sam_model, boxes, device):
    sam_model.set_image(image)
    H, W, _ = image.shape
    boxes_xyxy = box_ops.box_cxcywh_to_xyxy(boxes) * torch.Tensor([W, H, W, H])

    transformed_boxes = sam_model.transform.apply_boxes_torch(boxes_xyxy.to(device), image.shape[:2])
    masks, _, _ = sam_model.predict_torch(
        point_coords=None,
        point_labels=None,
        boxes=transformed_boxes,
        multimask_output=False,
    )

    mask_polygons = []

    for mask in masks:
        # Convert mask to 2D NumPy array
        mask = mask[0].cpu().numpy()  # Extract the first mask and convert to NumPy
        mask = (mask > 0).astype(np.uint8)  # Binary mask
        mask *= 255  # Scale to 0-255

        # Find contours in the binary mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for contour in contours:
            # Simplify the contour using RDP
            epsilon_factor = 0.02
            epsilon = epsilon_factor * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            # Convert to a list of (x, y) coordinates
            simplified_polygon = [(int(point[0][0]), int(point[0][1])) for point in approx]
            mask_polygons.append(simplified_polygon)

    return masks.cpu(), mask_polygons


def draw_masks(masks, image, random_color=True, alpha=0.6):
    annotated_frame_pil = Image.fromarray(image).convert("RGBA")

    for mask in masks:
        if random_color:
            color = np.concatenate([np.random.random(3), np.array([alpha])], axis=0)
        else:
            color = np.array([30 / 255, 144 / 255, 255 / 255, alpha])

        h, w = mask.shape[-2:]
        mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)

        mask_image_pil = Image.fromarray((mask_image.cpu().numpy() * 255).astype(np.uint8)).convert("RGBA")
        annotated_frame_pil = Image.alpha_composite(annotated_frame_pil, mask_image_pil)

    return np.array(annotated_frame_pil)

def create_labeled_detections_list(polygons, phrases, logits):
    logits_floats = [round(float(logit), 3) for logit in logits]  # Convert tensors to floats
    labeled_triplets = list(zip(phrases, logits_floats, polygons))
    polygons_with_labels_json = json.dumps(labeled_triplets)
    return polygons_with_labels_json

def run_models_on_img(img_path, groundingdino_model, sam_predictor, device, save_folder):
    # Load the image
    image_source, image = load_img(img_name=img_path)

    # Run the detection model (GroundingDINO)
    prompt = "drawer . cabinet door"
    # prompt = "oven . stove . sink . refrigerator . dishwasher . microwave . electronic kettle . dish drying rack . toaster . coffee machine"
    # prompt = "countertop"
    annotated_frame, detected_boxes, phrases, logits = detect(image=image, image_source=image_source,
                                                       text_prompt=prompt,
                                                       model=groundingdino_model)
    num_detections = len(detected_boxes)
    print("number of detections: " + str(num_detections))
    # Check if there are any detected boxes
    if num_detections == 0:
        print(f"No detections found for image: {img_path}")
        save_img_path = save_image(img_path=img_path, image_array=image_source, save_folder=save_folder,
                                  num_detections=num_detections)
        return save_img_path, 0, [], [], []  # Skip further processing and return path, 0 detections and empty list for the detected boxes.
    # show_img(image_source=annotated_frame)

    # Run the SAM segmentation model
    segmented_frame_masks, mask_polygons = segment(image=image_source, sam_model=sam_predictor, boxes=detected_boxes,
                                                   device=device)
    polygons_json = json.dumps(mask_polygons)
    # Draw only segmentation masks, without bounding boxes
    annotated_frame_with_masks = draw_masks(masks=segmented_frame_masks, image=image_source)
    
    # Draw only segmentation masks, with bounding boxes
    # annotated_frame_with_masks = draw_masks(masks=segmented_frame_masks, image=annotated_frame)
    
    # show_img(image_source=annotated_frame_with_masks)

    # Create a unique filename for the segmented image
    # base_filename = os.path.basename(img_path)
    # img_path_after_sam = os.path.join(save_folder, base_filename)  # Save with the same name in the new folder

    # Save the image with segmentation masks
    # save_image(annotated_frame_with_masks, img_path_after_sam)
    
    save_img_path = save_image(img_path=img_path, image_array=annotated_frame_with_masks, save_folder=save_folder,
                               num_detections=num_detections)
    bbox_json = json.dumps(detected_boxes.tolist())  # Convert detected boxes to JSON format
    polygons_with_labels_json = create_labeled_detections_list(polygons=mask_polygons, phrases=phrases, logits=logits)

    # Return path, number of detections, detected boxes and polygons as JSON, and polygons with labels as JSON
    return save_img_path, num_detections, bbox_json, polygons_json, polygons_with_labels_json


# Function to convert paths
def format_image_path(image_path, room_type):
    # Extract the image name from the full path
    image_name = os.path.basename(image_path)
    # Construct the new path
    new_path = f"images/{room_type}/{image_name}"
    return new_path

def extract_item_name(image_path):
    # Extract the filename from the path
    filename = Path(image_path).stem
    
    # Use regular expression to match the item name pattern
    match = re.match(r'(.+?)_\d+_[a-zA-Z]', filename)
    
    # If the filename contains "Random", use a different pattern
    if "Random" in filename:
        match = re.match(r'Random_\d+ - (.+?)_[a-zA-Z]', filename)
    
    if match:
        item_name = match.group(1)
        return item_name
    else:
        return ""

def image_process_object_detection(img_folder_path, groundingdino_model, sam_predictor, device, json_file_path, room_type, save_folder, is_validation=False):
    if not os.path.isdir(img_folder_path):
        print(f"Error: {img_folder_path} is not a valid directory.")
        return

    # Initialize a list to store all data
    data = []

    # Iterate over files in the folder
    for filename in os.listdir(img_folder_path):
        img_path = os.path.join(img_folder_path, filename)
        print(img_path)

        # Check if the file is a regular file and is an image file
        if os.path.isfile(img_path) and any(
                img_path.lower().endswith(image_ext) for image_ext in ['.jpg', '.jpeg', '.png', '.gif']):
            # Call the image processing function with the file path
            save_img_path, num_detections, bbox_json, polygons_json, polygons_with_labels_json = run_models_on_img(
                img_path=img_path,
                groundingdino_model=groundingdino_model,
                sam_predictor=sam_predictor,
                device=device,
                save_folder=save_folder
            )

            if num_detections > 0:
                # Append the data for this image to the list
                if is_validation:
                  data.append({
                      "image_path_html": format_image_path(save_img_path, room_type),
                      "num_detections": num_detections,
                      "containers_mask_polygon": polygons_json,
                      "containers_mask_polygon_with_labels": polygons_with_labels_json,
                      "room_type": room_type,
                      "chosen_item": extract_item_name(img_path)
                  })
                else:
                  data.append({
                      "image_path_html": format_image_path(save_img_path, room_type),
                      "num_detections": num_detections,
                      "containers_mask_polygon": polygons_json,
                      "containers_mask_polygon_with_labels": polygons_with_labels_json,
                      "room_type": room_type
                  })

    # Save the data to a JSON file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)


def run_models_on_train_data(img_path, groundingdino_model, sam_predictor, device, save_folder, item):
    # Load the image
    image_source, image = load_img(img_name=img_path)
    
    # Run the detection model (GroundingDINO)
    prompt = f"drawer for {item} . cabinet door for {item}"
    # prompt = f"drawer . cabinet door"
    annotated_frame, detected_boxes, phrases, logits = detect(image=image, image_source=image_source,
                                                       text_prompt=prompt,
                                                       model=groundingdino_model)
    num_detections = len(detected_boxes)
    print("number of detections: " + str(num_detections))
    
    # Now: pick the highest scoring bbox
    if num_detections > 0:
        best_idx = logits.argmax()
        best_box = detected_boxes[best_idx]
        best_score = logits[best_idx]
        best_label = phrases[best_idx]
        
        # Now you have ONLY ONE box
        print("Best detection: ", best_box, ", with score: ", best_score, ", with label: ", best_label)
    
    # Check if there are any detected boxes
    if num_detections == 0:
        print(f"No detections found for image: {img_path}")
        save_img_path = save_image(img_path=img_path, image_array=image_source, save_folder=save_folder,
                                  num_detections=num_detections)
        return save_img_path, 0, [], [], []
    
    # Run the SAM segmentation model
    segmented_frame_masks, mask_polygons = segment(image=image_source, sam_model=sam_predictor, boxes=best_box,
                                                   device=device)
    polygons_json = json.dumps(mask_polygons)
    # Draw only segmentation masks, without bounding boxes
    annotated_frame_with_masks = draw_masks(masks=segmented_frame_masks, image=image_source)
    
    save_img_path = save_image(img_path=img_path, image_array=annotated_frame_with_masks, save_folder=save_folder,
                               num_detections=num_detections)
    bbox_json = json.dumps(best_box.tolist())  # Convert detected boxes to JSON format
    
    labeled_triplets = [best_label, round(float(best_score), 3), mask_polygons]
    polygons_with_labels_json = json.dumps(labeled_triplets)
    
    # Return path, number of detections, detected boxes and polygons as JSON, and polygons with labels as JSON
    return save_img_path, num_detections, bbox_json, polygons_json, polygons_with_labels_json


def image_process_train_data(img_folder_path, groundingdino_model, sam_predictor, device, json_file_path, room_type, save_folder, output_json_file):
    # Load the JSON
    with open(json_file_path, 'r') as f:
        image_items_dict = json.load(f)
    
    # Initialize a list to store all data
    data = []
    
    # Go over each image and its items
    for json_image_path, items in image_items_dict.items():
        # Extract the file name
        filename = os.path.basename(json_image_path)
        # Remove the prefix like '10_segmented_'
        real_filename = filename.split("segmented_")[-1]

        # Build the actual full image path
        full_image_path = os.path.join(img_folder_path, real_filename)

        # Check if the image exists
        if not os.path.exists(full_image_path):
            print(f"Warning: Image {full_image_path} does not exist. Skipping.")
            continue

        # For each item, call your detection model
        for item in items:
            save_img_path, num_detections, bbox_json, polygons_json, polygons_with_labels_json = run_models_on_train_data(
            img_path=full_image_path, 
            groundingdino_model=groundingdino_model,
            sam_predictor=sam_predictor,
            device=device,
            save_folder=save_folder,
            item=item
            )
            
            if num_detections > 0:
                # Append the data for this image to the list
                data.append({
                    "image_path_html": format_image_path(save_img_path, room_type),
                    "num_detections": num_detections,
                    "containers_mask_polygon": polygons_json,
                    "containers_mask_polygon_with_labels": polygons_with_labels_json,
                    "room_type": room_type,
                    "chosen_item": item
                })

    # Save the data to a JSON file
    with open(output_json_file, 'w') as file:
        json.dump(data, file, indent=4)

def image_process_test_data(img_folder_path, groundingdino_model, sam_predictor, device, json_file_path, room_type, save_folder):
    if not os.path.isdir(img_folder_path):
        print(f"Error: {img_folder_path} is not a valid directory.")
        return

    # Initialize a list to store all data
    data = []

    # Iterate over files in the folder
    for filename in os.listdir(img_folder_path):
        img_path = os.path.join(img_folder_path, filename)
        print(img_path)

        # Check if the file is a regular file and is an image file
        if os.path.isfile(img_path) and any(
                img_path.lower().endswith(image_ext) for image_ext in ['.jpg', '.jpeg', '.png', '.gif']):
            # Call the image processing function with the file path
            item = extract_item_name(img_path)
            print("item: ", item)
            save_img_path, num_detections, bbox_json, polygons_json, polygons_with_labels_json = run_models_on_train_data(
            img_path=img_path, 
            groundingdino_model=groundingdino_model,
            sam_predictor=sam_predictor,
            device=device,
            save_folder=save_folder,
            item=item
            )

            if num_detections > 0:
                # Append the data for this image to the list
                data.append({
                    "image_path_html": format_image_path(save_img_path, room_type),
                    "num_detections": num_detections,
                    "containers_mask_polygon": polygons_json,
                    "containers_mask_polygon_with_labels": polygons_with_labels_json,
                    "room_type": room_type,
                    "chosen_item": item
                })

    # Save the data to a JSON file
    with open(json_file_path, 'w') as file:
        json.dump(data, file, indent=4)

def build_groundingdino_model(device):
    ckpt_repo_id = "ShilongLiu/GroundingDINO"
    ckpt_filenmae = "groundingdino_swinb_cogcoor.pth"
    ckpt_config_filename = "GroundingDINO_SwinB.cfg.py"

    groundingdino_model = load_model_hf(ckpt_repo_id, ckpt_filenmae, ckpt_config_filename, device)
    return groundingdino_model


def build_sam_predictor(device):
    sam_checkpoint = 'sam_vit_h_4b8939.pth'
    sam_predictor = SamPredictor(build_sam(checkpoint=sam_checkpoint).to(device))

    return sam_predictor


def main():
    start_time = time.time()
    is_validation = True
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    groundingdino_model = build_groundingdino_model(device=device)
    sam_predictor = build_sam_predictor(device=device)
    
    if is_validation:
        img_folder_path = '/dsi/dsai-lab/michaela.lr/thesis/organized_images/a_10_time/'
        save_folder = '/dsi/dsai-lab/michaela.lr/thesis/segmented_images_test_10_time_countertop/'  # Set the folder where you want to save the segmented images
        room_type = 'validation'  # Change this based on the actual room type
        # json_file_path = '/home/dsi/michaela.lr/projects/thesis/image_details_validation.json'
        json_file_path = '/dsi/dsai-lab/michaela.lr/thesis/image_details_test_10_time_countertop.json'
    else:
        img_folder_path = '/dsi/scratch/users/glikmao_old/SUN397/k/kitchen/'
        save_folder = '/dsi/dsai-lab/michaela.lr/thesis/segmented_images_train_data_subset/'  # Set the folder where you want to save the segmented images
        room_type = 'kitchen'  # Change this based on the actual room type
        json_file_path = '/dsi/dsai-lab/michaela.lr/thesis/image_to_items_dict_subset.json'
    
    # Ensure the save folder exists
    os.makedirs(save_folder, exist_ok=True)
    
    # To run Grounding-DINO & SAM as object detection (for containers, anchors, and countertop)
    image_process_object_detection(img_folder_path=img_folder_path, 
                  groundingdino_model=groundingdino_model, sam_predictor=sam_predictor, 
                  device=device, json_file_path=json_file_path, room_type=room_type, 
                  save_folder=save_folder, is_validation=is_validation)
    
    # To run Grounding-DINO & SAM to detect a container of an item on the train dataset
    '''
    image_process_train_data(
        img_folder_path=img_folder_path, 
        groundingdino_model=groundingdino_model, 
        sam_predictor=sam_predictor, 
        device=device, 
        json_file_path=json_file_path, 
        room_type=room_type, 
        save_folder=save_folder, 
        output_json_file='/dsi/dsai-lab/michaela.lr/thesis/image_details_dino_and_sam_no_item.json', 
    )
    '''
    
    # To run Grounding-DINO & SAM to detect a container of an item on the test dataset
    '''
    image_process_test_data(
      img_folder_path=img_folder_path, 
      groundingdino_model=groundingdino_model, 
      sam_predictor=sam_predictor, 
      device=device, 
      json_file_path=json_file_path, 
      room_type=room_type, 
      save_folder=save_folder
    )
    '''
    
    print("json file saved.")
    
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")


if __name__ == '__main__':
    main()
