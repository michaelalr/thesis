import json
import os
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from ast import literal_eval
from PIL import Image
from scripts.users_agreement import compute_iou
from compare_responses import remove_prefix_from_image_path, denormalize_bbox_to_polygon, clean_image_path


def extract_chosen_polygon(response, full_image_path, model_type, polygon_field):
    if "kosmos" in model_type.lower():
        entities = literal_eval(response.get("entities", "[]"))
        if len(entities) > 0:
            chosen_bbox = entities[0][2][0]  # Only first bbox
            return denormalize_bbox_to_polygon(chosen_bbox, full_image_path)
        return []

    elif "gemini" in model_type.lower():
        if response.get(polygon_field) == "[[0, 0], [0, 0], [0, 0], [0, 0]]":
            return []
        return literal_eval(response.get(polygon_field, "[]"))

    else:
        return literal_eval(response.get(polygon_field, "[]"))


def plot_polygons(image_path, correct_poly, model_poly, iou_score, model_type):
    fig, ax = plt.subplots(1)
    img = Image.open(image_path)
    ax.imshow(img)

    # Plot correct polygon - green
    if correct_poly == []:
        print("Correct poly is []")
    else:
        correct_patch = patches.Polygon(correct_poly, closed=True, fill=False, edgecolor='green', linewidth=3,
                                        label='Ground Truth')
        ax.add_patch(correct_patch)

    # Plot model polygon - red
    if model_poly == []:
        print("Model poly is []")
    else:
        model_patch = patches.Polygon(model_poly, closed=True, fill=False, edgecolor='red', linewidth=3, label=f'{model_type}')
        ax.add_patch(model_patch)

    plt.title(f"{os.path.basename(image_path)} - IoU: {iou_score:.3f}")
    plt.legend()
    plt.axis('off')
    plt.show()


def load_data(correct_json_path, model_json_path):
    with open(correct_json_path, 'r') as f:
        correct_data = json.load(f)
    with open(model_json_path, 'r') as f:
        model_data = json.load(f)
    return correct_data, model_data


def match_and_plot(correct_data, model_data, images_folder, polygon_field, model_type, iou_threshold=0.2,
                   sample_size=10):
    # Build a dict from image_path + item to ground truth polygon for quick lookup
    gt_dict = {}
    for entry in correct_data:
        key = (entry["image_path"], entry["chosen_item"])
        gt_poly = literal_eval(entry.get("chosen_polygon", "[]"))
        gt_dict[key] = gt_poly

    # Find model entries with IoU >= threshold
    matched_cases = []
    for entry in model_data:
        image_path = entry["image_path"]
        chosen_item = entry.get("chosen_item", "")

        if "kosmos" in model_type.lower():
            full_image_path = clean_image_path(image_path=image_path, is_test=True)
        else:
            full_image_path = os.path.join(images_folder, image_path)

        try:
            model_poly = extract_chosen_polygon(response=entry, full_image_path=full_image_path, model_type=model_type,
                                                polygon_field=polygon_field)
        except Exception as e:
            print(f"Error extracting polygon for {image_path}, {chosen_item}: {e}")
            model_poly = []

        gt_poly = gt_dict.get((image_path, chosen_item), [])

        try:
            iou = compute_iou(gt_poly, model_poly)
        except Exception as e:
            print(f"Error computing IoU for {image_path}, {chosen_item}: {e}")
            iou = 0.0

        if iou >= iou_threshold:
        # if iou > 0:
            matched_cases.append((full_image_path, chosen_item, gt_poly, model_poly, iou))

    if not matched_cases:
        print(f"No matches found with IoU >= {iou_threshold}")
        return

    print(f"Found {len(matched_cases)} matches with IoU >= {iou_threshold}")

    ious = [entry[4] for entry in matched_cases]
    if ious:
        mean_iou = sum(ious) / len(ious)
        print(f"Mean IoU over {len(ious)} matched cases: {mean_iou:.4f}")
    else:
        print("No matched cases to calculate mean IoU.")

    for full_image_path, item, gt_poly, model_poly, iou in matched_cases:
        if not os.path.isfile(full_image_path):
            print(f"Image not found: {full_image_path}")
            continue
        print(f"Image: {full_image_path} | Item: {item} | IoU: {iou:.3f}")
        plot_polygons(full_image_path, gt_poly, model_poly, iou, model_type)
        input("Press Enter to continue to next sample...")


if __name__ == "__main__":
    # Edit these paths as needed:
    # correct_json_path = "../data/test_data/test_data_no_kitchen.json"
    correct_json_path = "../data/test_data/test_data_kitchen_origin_filenames.json"
    model_type = "gemini-2.5"
    model_json_path = "../models/gemini/test_data_kitchen_origin_gemini_flash_2.5.json"  # or "gpt4o_responses.json", "kosmos2_responses.json", etc.
    images_folder = "../images/test_kitchen_images_original/"

    # The polygon field name differs per model, e.g.:
    polygon_field_per_model = {
        "gemini-1.5": "gemini_bbox_polygon_string",
        "gemini-2.5": "gemini_bbox_polygon_string",
        "gpt-4o": "chosen_polygon",
        "kosmos-2": "chosen_polygon",
        "llama-4": "chosen_polygon",
        "qwen": "chosen_polygon",
        "dino": "chosen_polygon",
    }

    polygon_field = polygon_field_per_model.get(model_type, "chosen_polygon")

    # Start threshold - adjust as needed interactively
    iou_threshold = 0.1
    sample_size = 10

    correct_data, model_data = load_data(correct_json_path, model_json_path)
    match_and_plot(correct_data, model_data, images_folder, polygon_field, model_type, iou_threshold, sample_size)
