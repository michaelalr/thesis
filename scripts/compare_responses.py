import json
import os
import random
import re
from ast import literal_eval
from collections import defaultdict
from pathlib import Path

import cv2
import firebase_admin
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pingouin as pg
import seaborn as sns
from PIL import Image
from firebase_admin import credentials, firestore
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from statsmodels.stats.anova import AnovaRM
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from scripts.users_agreement import compute_iou


# Function to clean image_path
def clean_image_path(image_path, is_test=False):
    # Use regex to extract the part starting with 'thesis/images/test/...'
    match = re.search(r'images/validation/.*', image_path) if is_test else re.search(r'images/kitchen/.*', image_path)
    if match:
        # Replace 'thesis/' with './'
        return "../" + match.group(0).replace("thesis/", "")
    return image_path  # Return the original path if no match


# Function to group responses by image_path and chosen_item
def group_responses(responses):
    grouped_data = {}
    for response in responses:
        cleaned_path = clean_image_path(response["image_path"])
        key = (cleaned_path, response["chosen_item"])
        if key not in grouped_data:
            grouped_data[key] = []
        grouped_data[key].append(response)
    return grouped_data


# Function to draw polygons on the image
def draw_polygons(image_path, polygons, title):
    image = Image.open(image_path)
    no_polygon_counter = 0
    plt.imshow(image)
    for polygon in polygons:
        if polygon:
            x_coords, y_coords = zip(*polygon)  # Unzip into x and y
            plt.fill(x_coords, y_coords, edgecolor='red', fill=False, linewidth=2)  # Draw polygon
        else:
            no_polygon_counter += 1

    # Title at the top
    plt.suptitle(title, fontsize=14, y=0.98)  # Adjust y for spacing

    # Add subtitle (if there are empty polygons)
    if no_polygon_counter > 0:
        plt.figtext(0.5, 0.90, f"{no_polygon_counter} users chose no container", ha="center", fontsize=12, color="gray")

    plt.axis('off')
    plt.show()


# Main function
def main(json_files_directory):
    all_responses = []

    # Load all JSON files from the directory
    for filename in os.listdir(json_files_directory):
        if filename.endswith(".json"):
            with open(os.path.join(json_files_directory, filename), "r") as file:
                data = json.load(file)
                all_responses.extend(data)

    # Group responses by image_path and chosen_item
    grouped_responses = group_responses(all_responses)

    # Display each image with all related polygons
    for (image_path, chosen_item), responses in grouped_responses.items():
        print(f"Displaying image: {image_path}")
        print(f"Chosen Item: {chosen_item}")
        print(f"Total Responses: {len(responses)}")
        print("=" * 50)

        # Prepare polygons for drawing
        polygons = []
        for response in responses:
            # Convert chosen_polygon string to list of tuples
            polygon = json.loads(response["chosen_polygon"])
            polygons.append(polygon)

        # Draw the image and polygons
        draw_polygons(image_path, polygons, f"Item: {chosen_item} - Responses: {len(responses)}")

        # Display details of each response
        for response in responses:
            # print(f"User ID: {response['user_id']}, Date: {response['date']}, Time: {response['time']}")
            print(f"User ID: {response['user_id']}")
            print(f"Polygon: {response['chosen_polygon']}")
        print("\n")


def plot_images_polygons(responses_by_item_and_user):
    # Ask for the user ID to filter responses
    selected_user_id = input("Enter the user_id to display responses for: ")

    # Ask for the item to filter responses
    selected_item = input("Enter the item to display responses for: ")

    # Check if the selected user_id exists
    if int(selected_user_id) in responses_by_item_and_user:
        if selected_item in responses_by_item_and_user[int(selected_user_id)]:
            user_responses = responses_by_item_and_user[int(selected_user_id)][selected_item]

            # Plot each image with its polygon one by one for each item
            # for item, item_responses in user_responses.items():
            print(f"Displaying images for user {selected_user_id}, item: {selected_item}")

            for idx, response in enumerate(user_responses):
                image_path = response.get('image_path')
                clean_image = clean_image_path(image_path=image_path)
                chosen_polygon = json.loads(response.get('chosen_polygon'))

                # Load image
                img = Image.open(clean_image)

                # Create a new figure for each image
                fig, ax = plt.subplots(figsize=(8, 8))
                ax.imshow(img)
                ax.axis('off')

                # Plot polygon if it exists
                if chosen_polygon:
                    polygon = patches.Polygon(chosen_polygon, closed=True, fill=False, edgecolor='red', linewidth=2)
                    ax.add_patch(polygon)

                ax.set_title(f"User: {selected_user_id}, Item: {selected_item}, Image {idx + 1}")

                plt.show()  # Show each image separately

                # Pause to allow user to view each image before moving to the next one
                input("Press Enter to continue to the next image...")
        else:
            print(f"No responses found for user_id: {selected_user_id} and item: {selected_item}")
    else:
        print(f"No responses found for user_id: {selected_user_id}")


def get_user_responses(responses):
    # Organize responses by 'chosen_item' and 'user_id'
    responses_by_item_and_user = {}

    for response in responses:
        user_id = response.get('user_id')
        chosen_item = response.get('chosen_item')
        if user_id not in responses_by_item_and_user:
            responses_by_item_and_user[user_id] = {}
        if chosen_item not in responses_by_item_and_user[user_id]:
            responses_by_item_and_user[user_id][chosen_item] = []
        responses_by_item_and_user[user_id][chosen_item].append(response)

    return responses_by_item_and_user


def save_firebase_as_json():
    # Initialize the Firebase Admin SDK
    cred = credentials.Certificate(
        'C:\\Users\\user2\\OneDrive - Bar-Ilan University - Students\\Documents\\miki\\biu\\thesis\\images\\application\\stored-items-containers-firebase-adminsdk-pf64z-5c7c8c19e1.json')
    firebase_admin.initialize_app(cred)

    # Fetch data from Firestore
    db = firestore.client()
    responses_ref = db.collection('user_responses')  # Replace with your collection name
    responses = responses_ref.stream()

    # Collect all responses in a list
    all_responses = [response.to_dict() for response in responses]

    # Save the responses to a JSON file
    json_filename = '../data/upwork/upwork_responses.json'
    with open(json_filename, 'w') as f:
        json.dump(all_responses, f, indent=4)

    print("Data saved to upwork_responses.json")

    return json_filename


def show_annotation_per_user_and_item():
    # json_filename = save_firebase_as_json()
    json_filename = '../data/upwork/upwork_responses_rotate.json'
    # Load the JSON file
    with open(json_filename, 'r') as f:
        all_responses = json.load(f)

    responses_by_item_and_user = get_user_responses(responses=all_responses)

    plot_images_polygons(responses_by_item_and_user=responses_by_item_and_user)

    # Directory where all JSON response files are stored
    # json_files_directory = "responses"  # Change this to your directory name
    # main(json_files_directory)


def check_empty_responses(all_responses, user_id):
    # Filter responses for user_id
    user_responses = [response for response in all_responses if response.get('user_id') == user_id]
    # Count responses with "chosen_polygon": "[]"
    empty_polygon_count = sum(1 for response in user_responses if response.get('chosen_polygon') == "[]")
    print(
        f"User {user_id} has {empty_polygon_count} responses with 'chosen_polygon': '[]' out of {len(user_responses)}.")


def save_validation_gt(user_response_json, image_details_json, image_folder, output_folder):
    # Create output folder if not exists
    os.makedirs(output_folder, exist_ok=True)

    # Load JSON files
    with open(user_response_json, "r") as f:
        user_responses = json.load(f)

    with open(image_details_json, "r") as f:
        image_details = json.load(f)

    # Function to convert polygon string to list
    def parse_polygon(polygon_str):
        return json.loads(polygon_str.replace("'", "\""))

    # Process user responses
    for response in user_responses:
        image_url = response["image_path"]  # URL in the JSON
        image_name = os.path.basename(image_url)  # Extract filename
        image_path = os.path.join(image_folder, image_name)  # Local path

        chosen_polygon = parse_polygon(response["chosen_polygon"])  # Convert string to list

        if os.path.exists(image_path):
            # Load image
            img = cv2.imread(image_path)

            # Draw chosen polygon
            pts = np.array(chosen_polygon, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(img, [pts], isClosed=True, color=(0, 255, 0), thickness=3)

            # Save marked image
            output_image_path = os.path.join(output_folder, image_name)
            cv2.imwrite(output_image_path, img)

    print("Marked images saved successfully.")


def denormalize_bbox_to_polygon(bbox_norm, image_path):
    """Convert normalized bbox to pixel polygon [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]"""
    try:
        # Load image to get its dimensions
        if not os.path.exists(image_path):
            return None
        with Image.open(image_path) as img:
            width, height = img.size
    except:
        return None

    x_min = int(bbox_norm[0] * width)
    y_min = int(bbox_norm[1] * height)
    x_max = int(bbox_norm[2] * width)
    y_max = int(bbox_norm[3] * height)

    # Return as rectangle polygon: top-left, bottom-left, bottom-right, top-right
    return [[x_min, y_min], [x_min, y_max], [x_max, y_max], [x_max, y_min]]


def simplify_bbox(complex_polygon):
    """
    Simplify a complex polygon (with multiple points) to a bounding box
    defined by min_x, min_y, max_x, max_y coordinates.
    """
    all_points = []

    # Flatten the polygon if it's a list of lists (complex polygons)
    if isinstance(complex_polygon, list):
        for sublist in complex_polygon:
            if isinstance(sublist, list):
                all_points.extend(sublist)

    # Extract all x and y coordinates
    x_coords = [point[0] for point in all_points]
    y_coords = [point[1] for point in all_points]

    # Calculate the min and max values of x and y
    min_x = min(x_coords)
    max_x = max(x_coords)
    min_y = min(y_coords)
    max_y = max(y_coords)

    # Return the simplified bounding box as a list of coordinates
    simplified_bbox = [[min_x, min_y], [min_x, max_y], [max_x, max_y], [max_x, min_y]]

    return simplified_bbox


def extract_chosen_polygon(response, image_path, response_type, data_json):
    if "kosmos" in response_type.lower():
        entities = literal_eval(response.get("entities", "[]"))
        if len(entities) > 0:
            chosen_bbox = entities[0][2][0]  # Only first bbox
            suffix_image_path = clean_image_path(image_path=image_path, is_test=("test" in data_json))
            return denormalize_bbox_to_polygon(chosen_bbox, suffix_image_path)
        return []

    elif "gemini" in response_type.lower():
        if response.get("gemini_bbox_polygon_string") == "[[0, 0], [0, 0], [0, 0], [0, 0]]":
            return []
        return literal_eval(response.get("gemini_bbox_polygon_string", "[]"))

    elif "dino" in response_type.lower():
        containers_mask_polygon = json.loads(response.get("containers_mask_polygon", "[]"))
        if isinstance(containers_mask_polygon, list) and len(containers_mask_polygon) > 1:
            return simplify_bbox(containers_mask_polygon)
        elif isinstance(containers_mask_polygon, list) and len(containers_mask_polygon) == 1:
            return containers_mask_polygon[0]
        return []

    else:
        return literal_eval(response.get("chosen_polygon", "[]"))


def give_score_on_data_fixed(data_json, users_responses_json, scores_json, response_type="human", mode="partial"):
    # Load correct annotations
    with open(data_json, "r") as f:
        correct_annotations = json.load(f)

    # Load user responses
    with open(users_responses_json, "r") as f:
        user_responses = json.load(f)

    print(f"Loaded {len(user_responses)} user responses.")

    # ---------------------
    correct_keys = set((entry["image_path"], entry["chosen_item"]) for entry in correct_annotations)

    missing = []
    for r in user_responses:
        key = (r["image_path"], r["chosen_item"])
        if key not in correct_keys:
            missing.append(key)

    print(f"Missing {len(missing)} response keys in correct data:")
    for key in missing[:10]:  # Show first 10
        print(key)
    # ---------------------

    # Create quick lookup dictionaries
    correct_lookup = {
        (entry["image_path"], entry["chosen_item"]): literal_eval(entry["chosen_polygon"])
        for entry in correct_annotations
    }
    response_lookup = {
        (r["image_path"], r["chosen_item"]): r
        for r in user_responses
    }

    user_scores = {}
    total_attempts = {}
    iou_scores = {}

    # Add a dictionary to track per-item stats
    item_stats = {}

    # Evaluate
    data_to_iterate = (
        user_responses if mode == "partial" else correct_annotations
    )

    for entry in data_to_iterate:
        image_path = entry["image_path"]
        chosen_item = entry["chosen_item"]
        if mode == "partial":
            key = (image_path, chosen_item)
            if key not in correct_lookup:
                continue
            correct_polygon = correct_lookup[key]
            response = entry
        else:  # full
            correct_polygon = literal_eval(entry["chosen_polygon"])
            response = response_lookup.get((image_path, chosen_item), None)

        user_id = (
            response["user_id"]
            if response_type == "human" and response and "user_id" in response
            else response_type
        )

        # Track total attempts
        total_attempts[user_id] = total_attempts.get(user_id, 0) + 1

        # Determine chosen polygon
        if response:
            try:
                chosen_polygon = extract_chosen_polygon(response, image_path, response_type, data_json)
            except Exception as e:
                print(f"Error extracting polygon for {image_path}, {chosen_item}: {e}")
                chosen_polygon = []
        else:
            chosen_polygon = []

        # Compute IoU
        try:
            iou = compute_iou(correct_polygon, chosen_polygon)
        except Exception as e:
            print(f"Error computing IoU for {image_path}, {chosen_item}: {e}")
            iou = 0.0

        # Record IoU
        iou_scores[user_id] = iou_scores.get(user_id, []) + [iou]

        # Count correct answers based on IoU thresholds
        # Determine threshold
        if isinstance(user_id, int):  # human
            threshold = 1.0
        else:
            threshold = {
                # "human": 1.0,
                "random": 1.0,
                "chatgpt": 1.0,
                "llama_3.3": 1.0,
                "llama_4": 0.5,
                "qwen": 0.5,
                "gpt-4o": 0.5,
                "kosmos": 0.5,
                "gemini_1.5": 0.5,
                "gemini_2.5": 0.5,
                "dino_1": 1.0,
                "dino_0.95": 0.95,
                "dino_no_item": 1.0,
            }.get(response_type, 1.0)

        is_correct = iou >= threshold
        if is_correct:
            user_scores[user_id] = user_scores.get(user_id, 0) + 1

        # Update per-item stats
        if chosen_item not in item_stats:
            item_stats[chosen_item] = {"correct": 0, "total": 0, "ious": []}
        item_stats[chosen_item]["correct"] += int(is_correct)
        item_stats[chosen_item]["total"] += 1
        item_stats[chosen_item]["ious"].append(iou)

        # --- Collect per-pair results for statistical testing ---
        if "per_pair_results" not in locals():
            per_pair_results = []

        per_pair_results.append({
            "image_path": image_path,
            "item": chosen_item,
            "user_id": user_id,
            "iou": iou,
            "accuracy": 1 if iou >= threshold else 0
        })

    # Compute summary metrics
    user_percentages = {
        user: (user_scores.get(user, 0) / total_attempts[user]) * 100
        for user in total_attempts
    }
    user_iou_avg = {
        user: sum(iou_scores[user]) / len(iou_scores[user]) if user in iou_scores else 0.0
        for user in total_attempts
    }

    df_scores = pd.DataFrame([
        {
            "user_id": user,
            "correct_answers": user_scores.get(user, 0),
            "total_attempts": total_attempts[user],
            "accuracy (%)": round(user_percentages[user], 2),
            "average_IoU": round(user_iou_avg[user], 3)
        }
        for user in total_attempts
    ])

    print(df_scores)

    # Create per-item stats DataFrame
    df_item_stats = pd.DataFrame([
        {
            "item": item,
            "accuracy (%)": round(100 * v["correct"] / v["total"], 2),
            "average IoU": round(sum(v["ious"]) / len(v["ious"]), 3),
            "total samples": v["total"]
        }
        for item, v in item_stats.items()
    ]).sort_values(by="item")

    print("\nPer-item stats:\n", df_item_stats)

    # Optional: save results to file
    if scores_json:
        df_scores.to_json(scores_json, orient="records", indent=2)
        df_item_stats.to_csv(scores_json.replace(".json", "_per_item.csv"), index=False)

    if "per_pair_results" in locals():
        df_per_pair = pd.DataFrame(per_pair_results)
        print(f"Collected {len(df_per_pair)} per-pair results.")
        df_per_pair.to_csv(f"score_per_pair_{response_type}.csv", index=False)


def score_human_users(data_json, responses_json, output_json=None, mode="partial", return_per_item=False):
    """
    Compute per-human-user accuracy and IoU from chosen polygons.

    Args:
        data_json (str): Path to JSON with correct polygons.
        responses_json (str): Path to JSON with human responses.
        output_json (str or None): If given, saves output as JSON.
        mode (str): "partial" for checking only answered entries,
                    "full" for checking all ground truth entries.

    Returns:
        pd.DataFrame: Scores per user.
    """
    # Load data
    with open(data_json, "r") as f:
        correct_data = json.load(f)
    with open(responses_json, "r") as f:
        responses = json.load(f)

    # Create lookup for GT and Responses
    gt_lookup = {
        (d["image_path"], d["chosen_item"]): literal_eval(d["chosen_polygon"])
        for d in correct_data
    }

    response_lookup = {}
    for r in responses:
        key = (r["image_path"], r["chosen_item"])
        response_lookup.setdefault(key, []).append(r)

    # Initialize tracking
    user_scores = {}
    user_attempts = {}
    user_ious = {}

    # NEW: Per-user-per-item tracking
    user_item_scores = defaultdict(lambda: defaultdict(int))
    user_item_attempts = defaultdict(lambda: defaultdict(int))
    user_item_ious = defaultdict(lambda: defaultdict(list))

    # Select items to iterate
    if mode == "partial":
        data_iter = responses
    elif mode == "full":
        data_iter = correct_data
    else:
        raise ValueError("mode must be 'partial' or 'full'")

    # Iterate
    for entry in data_iter:
        image_path = entry["image_path"]
        chosen_item = entry["chosen_item"]
        key = (image_path, chosen_item)

        if key not in gt_lookup:
            continue  # skip unknown GT
        correct_polygon = gt_lookup[key]

        if mode == "partial":
            responses_to_check = [entry]
        else:  # full
            responses_to_check = response_lookup.get(key, [])

        for response in responses_to_check:
            user_id = response["user_id"]
            try:
                chosen_polygon = literal_eval(response["chosen_polygon"])
            except Exception as e:
                print(f"Error parsing chosen_polygon for {key}: {e}")
                continue

            # Compute IoU
            try:
                iou = compute_iou(correct_polygon, chosen_polygon)
            except Exception as e:
                print(f"Error computing IoU for {key}: {e}")
                iou = 0.0

            # Track
            user_attempts[user_id] = user_attempts.get(user_id, 0) + 1
            user_ious[user_id] = user_ious.get(user_id, []) + [iou]
            if iou == 1.0:
                user_scores[user_id] = user_scores.get(user_id, 0) + 1

            # NEW: Per-user-per-item tracking
            user_item_attempts[user_id][chosen_item] += 1
            user_item_ious[user_id][chosen_item].append(iou)
            if iou == 1.0:
                user_item_scores[user_id][chosen_item] += 1

    # Summarize
    result = []
    for user_id in user_attempts:
        total = user_attempts[user_id]
        correct = user_scores.get(user_id, 0)
        avg_iou = sum(user_ious[user_id]) / total if total > 0 else 0
        acc = (correct / total) * 100
        result.append({
            "user_id": user_id,
            "correct_answers": correct,
            "total_attempts": total,
            "accuracy (%)": round(acc, 2),
            "average_IoU": round(avg_iou, 3)
        })

    df = pd.DataFrame(result)
    print(df)

    if output_json:
        df.to_json(output_json, orient="records", indent=2)

    # Optional per-user-per-item DataFrame
    if return_per_item:
        item_records = []
        for user_id in user_item_attempts:
            for item in user_item_attempts[user_id]:
                total = user_item_attempts[user_id][item]
                correct = user_item_scores[user_id][item]
                avg_iou = sum(user_item_ious[user_id][item]) / total if total > 0 else 0
                item_records.append({
                    "user_id": f"human_{user_id}",
                    "item": item,
                    "accuracy (%)": round(acc, 2),
                    "average IoU": round(avg_iou, 3),
                    "total samples": total,
                })
                acc = (correct / total) * 100
        df_user_item = pd.DataFrame(item_records)
        print(df_user_item)
        if output_json:
            df_user_item.to_csv(output_json.replace(".json", "_per_item.csv"), index=False)

    return df


def create_random_baseline(train_or_test_data_json, output_filename=None, train_or_test="train"):
    # Load image details
    with open(train_or_test_data_json, "r") as f:
        image_details = json.load(f)

    random_responses = []

    # Iterate over image details
    for entry in image_details:
        containers = literal_eval(entry["containers_polygons"])  # Convert string to list
        if containers:  # Ensure there are containers to choose from
            containers_with_empty = containers + [[]]  # Add option of "no container"
            chosen_polygon = random.choice(containers_with_empty)  # Select a random container

            # Create response entry
            if train_or_test == "train":
                response_entry = {
                    "image_path": entry["image_path"],
                    "containers_polygons": entry["containers_polygons"],
                    "chosen_polygon": str(chosen_polygon),
                    "chosen_item": entry["chosen_item"],
                    "room_type": entry["room_type"]
                }
            else:
                response_entry = {
                    "image_path": entry["image_path"],
                    "containers_polygons": entry["containers_polygons"],
                    "chosen_polygon": str(chosen_polygon),
                    "chosen_item": entry["chosen_item"]
                }
            random_responses.append(response_entry)

    # Save to JSON file
    file_name = output_filename if output_filename else "../baselines/random/random_" + train_or_test + "_responses.json"
    with open(file_name, "w") as f:
        json.dump(random_responses, f, indent=4)

    print("Random " + train_or_test + " responses JSON generated successfully!")


def check_gemini_bbox():
    # Example data
    image_path = "C:\\Users\\user2\\OneDrive - Bar-Ilan University - Students\\Documents\\miki\\biu\\thesis\\images\\14a.jpg"
    # bbox = [x_min, y_min, width, height]  # Replace with your bbox coordinates
    bbox = [635, 583, 702, 724]  # Replace with your bbox coordinates

    # Load image
    image = Image.open(image_path)

    # Create figure and axis
    fig, ax = plt.subplots(1)
    ax.imshow(image)

    # Create a rectangle patch
    rect = patches.Rectangle((bbox[0], bbox[1]), bbox[2], bbox[3], linewidth=2, edgecolor='red', facecolor='none')

    # Add the rectangle to the plot
    ax.add_patch(rect)

    # Show the image with bbox
    plt.show()


def calculate_user_accuracy(train_data_json, user_responses_json):
    # Load your JSON files
    with open(train_data_json, 'r') as f:
        train_data = json.load(f)

    with open(user_responses_json, 'r') as f:
        user_responses = json.load(f)

    # Step 1: Build a mapping from (image_path, chosen_item) -> chosen_polygon
    train_lookup = {}
    for entry in train_data:
        key = (entry['image_path'], entry['chosen_item'])
        train_lookup[key] = entry['chosen_polygon']

    # Step 2: Find all shared image-item pairs (appeared multiple times in user responses)
    pair_to_users = defaultdict(set)

    for entry in user_responses:
        key = (entry['image_path'], entry['chosen_item'])
        user_id = entry['user_id']
        pair_to_users[key].add(user_id)

    # Shared pairs = pairs with 2 or more different users
    shared_pairs = {key for key, users in pair_to_users.items() if len(users) >= 2}

    print(f"Total shared (image_path, item) pairs: {len(shared_pairs)}")

    # Step 3: Group responses by user
    user_to_responses = defaultdict(list)

    for entry in user_responses:
        user_id = entry['user_id']
        key = (entry['image_path'], entry['chosen_item'])
        if key in shared_pairs:
            user_to_responses[user_id].append(entry)

    # Step 4: Calculate unbiased accuracy per user
    for user_id, responses in user_to_responses.items():
        correct = 0
        total = 0

        print(f"\nEvaluating User {user_id} (only on shared images):")

        for response in responses:
            key = (response['image_path'], response['chosen_item'])

            if key not in train_lookup:
                print(f"Skipping (no train label): {key}")
                continue

            train_polygon = train_lookup[key]
            user_polygon = response['chosen_polygon']

            total += 1

            if user_polygon == train_polygon:
                correct += 1

        if total > 0:
            accuracy = correct / total
        else:
            accuracy = 0

        print(f"User {user_id} - Unbiased Accuracy (shared images only): {accuracy:.2%} ({correct}/{total})")


def split_human_responses_by_user(test_data_json, user_responses_json):
    # Load test data to keep
    with open(test_data_json, "r") as f:
        test_data = json.load(f)

    # Build a set of valid (image_path, chosen_item) tuples
    valid_cases = {
        (entry["image_path"], entry["chosen_item"])
        for entry in test_data
    }

    # Load user responses
    with open(user_responses_json, "r") as f:
        responses = json.load(f)

    # Split by user and filter by valid cases
    users_data = {1: [], 2: [], 3: []}
    all_data = []

    for entry in responses:
        key = (entry["image_path"], entry["chosen_item"])
        if key in valid_cases:
            users_data[entry["user_id"]].append(entry)
            all_data.append(entry)

    with open(f"../baselines/human/test_responses_kitchen.json", "w") as f:
        json.dump(all_data, f, indent=2)

    for user_id, user_entries in users_data.items():
        with open(f"../baselines/human/test_response_user_{user_id}_filtered.json", "w") as f:
            json.dump(user_entries, f, indent=2)

    print("Filtered files saved in 'filtered_responses/' directory.")


def find_missing_responses_dino(test_data_json, responses_json):
    # Load test data
    with open(test_data_json, "r") as f:
        test_data = json.load(f)

    # Create a set of all required cases
    required_cases = {
        (entry["image_path"], entry["chosen_item"])
        for entry in test_data
    }

    with open(responses_json, "r") as f:
        user_data = json.load(f)

    user_answered = {
        (entry["image_path"], entry["chosen_item"])
        for entry in user_data
    }

    missing_cases = required_cases - user_answered

    # Print missing cases per user
    print(f"\nMissing {len(missing_cases)} cases:")
    for image_path, item in sorted(missing_cases):
        print(f"  - {item} in {image_path}")


def find_missing_responses_human_test(test_data_json):
    # Load test data
    with open(test_data_json, "r") as f:
        test_data = json.load(f)

    # Create a set of all required cases
    required_cases = {
        (entry["image_path"], entry["chosen_item"])
        for entry in test_data
    }

    # Directory with filtered user responses
    response_dir = Path("../baselines/human/")

    # Track missing cases per user
    missing_cases_per_user = {}

    for user_id in [1, 2, 3]:
        response_file = response_dir / f"test_response_user_{user_id}_filtered.json"
        with open(response_file, "r") as f:
            user_data = json.load(f)

        user_answered = {
            (entry["image_path"], entry["chosen_item"])
            for entry in user_data
        }

        missing_cases = required_cases - user_answered
        missing_cases_per_user[user_id] = missing_cases

    # Print missing cases per user
    for user_id, missing_cases in missing_cases_per_user.items():
        print(f"\nUser {user_id} is missing {len(missing_cases)} cases:")
        for image_path, item in sorted(missing_cases):
            print(f"  - {item} in {image_path}")


def compute_average_containers(data_json_path):
    # Load your JSON file
    with open(data_json_path, "r") as f:
        json_data = json.load(f)

    total_containers = 0
    total_entries = 0

    for entry in json_data:
        if "containers_polygons" in entry:
            try:
                containers = json.loads(entry["containers_polygons"])
                total_containers += len(containers)
                total_entries += 1
            except json.JSONDecodeError:
                print(f"Skipping entry due to malformed JSON: {entry['image_path']}")

    if total_entries == 0:
        return 0  # avoid division by zero

    average = total_containers / total_entries
    print(f"Average containers per image: {average:.2f}")
    return average


def remove_prefix_from_image_path(path):
    filename = os.path.basename(path)
    filename = re.sub(r"^\d+_segmented_", "", filename)
    filename = filename.replace("Food_containers__", "Food_containers_")
    return filename


def plot_posthoc_pairwise(df):
    df.set_index('B', inplace=True)
    df.sort_values('hedges', ascending=False, inplace=True)

    # --- Normalize colors based on Hedges' g ---
    norm = Normalize(vmin=df['hedges'].min(), vmax=df['hedges'].max())
    colors = plt.cm.coolwarm(norm(df['hedges'].values))

    # --- Create plot ---
    fig, ax = plt.subplots(figsize=(10, 5))
    bar = sns.barplot(
        x=df.index,
        y=df['hedges'],
        palette=colors,
        edgecolor='black',
        ax=ax
    )

    # --- Annotate significance ---
    for i, (p, h) in enumerate(zip(df['p-corr'], df['hedges'])):
        significance = '*' if p < 0.05 else ''
        offset = 0.02 if h >= 0 else -0.02
        ax.text(i, h + offset, significance, ha='center', va='bottom', fontsize=12, color='black')

    # --- Labels and styles ---
    ax.axhline(0, color='gray', linestyle='--')
    ax.set_ylabel("Hedges' g (Effect Size)")
    ax.set_xlabel("Comparison: NOAM GPT-4 vs.")
    ax.set_title("Effect Sizes of NOAM GPT-4 Compared to Other Models\n(Significant differences marked with *)")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45)

    # --- Adjust ylim to keep * inside ---
    ymin, ymax = df['hedges'].min(), df['hedges'].max()
    ax.set_ylim(ymin - 0.1, ymax + 0.1)

    # --- Optional: Add colorbar legend ---
    sm = ScalarMappable(cmap="coolwarm", norm=norm)
    sm.set_array([])  # Required to avoid error
    cbar = plt.colorbar(sm, ax=ax)
    cbar.set_label("Effect Size (Hedges' g)")

    plt.tight_layout()
    plt.savefig("hedges_effect_sizes.png", dpi=300, bbox_inches='tight')
    plt.show()


def t_test():
    # Step 1: Model CSV paths (exclude human for now)
    model_files = {
        "gpt-4o": "./t-test_results/score_per_pair_gpt-4o.csv",
        "chatgpt": "./t-test_results/score_per_pair_chatgpt.csv",
        "llama_3.3": "./t-test_results/score_per_pair_llama_3.3.csv",
        "llama_4": "./t-test_results/score_per_pair_llama_4.csv",
        "qwen": "./t-test_results/score_per_pair_qwen.csv",
        "random": "./t-test_results/score_per_pair_random.csv",
        "kosmos": "./t-test_results/score_per_pair_kosmos.csv",
        "gemini_1.5": "./t-test_results/score_per_pair_gemini_1.5.csv",
        "gemini_2.5": "./t-test_results/score_per_pair_gemini_2.5.csv",
        "dino_1": "./t-test_results/score_per_pair_dino_1.csv",
        "dino_0.95": "./t-test_results/score_per_pair_dino_0.95.csv",
        "dino_no_item": "./t-test_results/score_per_pair_dino_no_item.csv",
        # "human": "./t-test_results/score_per_pair_human.csv",
    }

    # Step 2: Load model data and add 'model' column
    all_dfs = []
    for model, file_path in model_files.items():
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        df = pd.read_csv(file_path)
        df["model"] = model
        all_dfs.append(df)

    # Step 3: Handle human users (1, 2, 3 in same CSV)
    human_path = "./t-test_results/score_per_pair_human.csv"
    if os.path.exists(human_path):
        df_human = pd.read_csv(human_path)
        for uid in [1, 2, 3]:
            df_user = df_human[df_human["user_id"] == uid].copy()
            df_user["model"] = f"human_{uid}"
            all_dfs.append(df_user)
    else:
        print("Human scores file not found:", human_path)

    # Step 4: Merge all
    df_all = pd.concat(all_dfs, ignore_index=True)

    df_all['image_path'] = df_all['image_path'].apply(remove_prefix_from_image_path)

    # Step 5: Create trial ID from image and item
    df_all["trial"] = df_all["image_path"] + " | " + df_all["item"]

    # Step 6: Run repeated measures ANOVA on IoU
    aov = pg.rm_anova(dv='iou', within='model', subject='trial', data=df_all, detailed=True)
    print("🔍 Repeated Measures ANOVA:")
    print(aov)

    # Step 7: Pairwise t-tests with Bonferroni correction
    posthoc = pg.pairwise_ttests(dv='iou', within='model', subject='trial', data=df_all, padjust='bonf')
    print("\n📊 Post-hoc Pairwise t-tests (Bonferroni corrected):")
    print(posthoc)

    # Optional: Save results
    aov.to_csv("./t-test_results/anova_results.csv", index=False)
    posthoc.to_csv("./t-test_results/posthoc_pairwise_ttests.csv", index=False)
    print("\n✅ Saved: './t-test_results/anova_results.csv', './t-test_results/posthoc_pairwise_ttests.csv'")

    # # Filter only comparisons involving "chatgpt"
    # chatgpt_comparisons = posthoc[
    #     (posthoc['A'] == 'chatgpt') | (posthoc['B'] == 'chatgpt')
    #     ]
    #
    # # Show significant comparisons (Bonferroni-corrected)
    # significant_vs_chatgpt = chatgpt_comparisons[chatgpt_comparisons['p-corr'] < 0.05]
    #
    # print("📊 Significant differences between 'chatgpt' and others:")
    # print(significant_vs_chatgpt[['A', 'B', 'T', 'p-corr', 'hedges']])

    # Define the models to compare with 'chatgpt'
    models_to_compare = ['llama_3.3', 'llama_4', 'qwen', 'gpt-4o', 'random', 'kosmos', 'gemini_1.5', 'gemini_2.5', 'dino_1', 'dino_0.95',
                         'dino_no_item', 'human_1', 'human_2', 'human_3']

    # Filter the results where chatgpt is being compared to the other models
    chatgpt_comparisons = posthoc[
        (posthoc['A'] == 'chatgpt') & (posthoc['B'].isin(models_to_compare))]

    # Or vice versa if needed (models compared against chatgpt)
    chatgpt_comparisons_reverse = posthoc[
        (posthoc['B'] == 'chatgpt') & (posthoc['A'].isin(models_to_compare))]

    # Combine both results
    chatgpt_comparisons_all = pd.concat([chatgpt_comparisons, chatgpt_comparisons_reverse])

    # Filter only significant results based on the corrected p-value
    significant_comparisons = chatgpt_comparisons_all[chatgpt_comparisons_all['p-corr'] < 0.05]

    # Display the significant comparisons
    print("Significant comparisons (chatgpt vs other models):")
    print(significant_comparisons[['A', 'B', 'T', 'p-corr', 'hedges']])
    print(significant_comparisons)

    # If needed, you can save this summary to a CSV
    significant_comparisons.to_csv("./t-test_results/significant_comparisons_chatgpt_vs_others.csv", index=False)

    # Assuming `posthoc` is your full pairwise comparison DataFrame
    df = posthoc[posthoc['A'] == 'chatgpt'].copy()
    plot_posthoc_pairwise(df=df)


def summarize_item_difficulty(combined_df, output_dir, metric):
    summary_df = (
        combined_df.groupby("item")[metric]
        .agg(["mean", "std", "min", "max"])
        .rename(columns={"mean": "mean_accuracy", "std": "std_dev", "min": "min_accuracy", "max": "max_accuracy"})
        .sort_values("mean_accuracy", ascending=False)
    )

    plt.figure(figsize=(14, 6))
    plt.bar(summary_df.index, summary_df["mean_accuracy"], yerr=summary_df["std_dev"], capsize=4, color='skyblue')
    plt.xticks(rotation=45, fontsize=14, ha='right')
    plt.ylabel(metric, fontsize=14)
    plt.title(f"{metric} Across Items (Mean ± Std Dev)", fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/item_difficulty_accuracy.png")
    plt.close()

    summary_df.to_csv(f"{output_dir}/item_difficulty_summary.csv")

    return summary_df


def run_anova_posthoc_per_item(comparison_df, output_dir, metric):
    # Melt back to long format for AnovaRM
    long_df = comparison_df.melt(id_vars=["item"], var_name="model", value_name=metric).dropna()

    # statsmodels AnovaRM requires columns: depvar, subject, within-subject factor(s)
    # Here:
    # depvar = metric (accuracy or IoU)
    # subject = item (repeated measure unit)
    # within = model (factor: different models + human)
    aovrm = AnovaRM(long_df, depvar=metric, subject="item", within=["model"])
    res = aovrm.fit()

    print(res)
    with open(
            os.path.join(output_dir, f"anova_summary_{metric.replace(' ', '_').replace('(', '').replace(')', '')}.txt"),
            "w") as f:
        f.write(str(res))

    # Tukey post-hoc (pairwise comparisons)
    posthoc = pairwise_tukeyhsd(long_df[metric], long_df["model"])
    print(posthoc.summary())

    # Save Tukey summary to CSV
    tukey_df = pd.DataFrame(data=posthoc._results_table.data[1:], columns=posthoc._results_table.data[0])
    tukey_df.to_csv(
        os.path.join(output_dir, f"tukey_posthoc_{metric.replace(' ', '_').replace('(', '').replace(')', '')}.csv"),
        index=False)

    print(f"ANOVA and post-hoc results saved in {output_dir}")


def plot_scores_per_item(combined, output_dir, metric):
    # Keep only relevant columns
    combined = combined[["item", metric, "source"]].dropna()

    # Sort items alphabetically for consistent ordering
    combined["item"] = combined["item"].astype(str)
    combined = combined.sort_values("item")

    # Compute mean metric per item (averaged over all models)
    item_mean = combined.groupby("item")[metric].mean().sort_values(ascending=False)
    ordered_items = item_mean.index.tolist()

    plt.figure(figsize=(16, 8))
    sns.barplot(data=combined, x="item", y=metric, hue="source", order=ordered_items)
    plt.xticks(rotation=45, ha="right")
    plt.title(f"Per-Item {metric} for Each Model and Human")
    plt.xlabel("Item")
    plt.ylabel(metric)
    plt.legend(title="Model / Human", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    plt.savefig(os.path.join(output_dir, f"per_item_{metric.replace(' ', '_').replace('(', '').replace(')', '')}.png"))
    plt.close()


def compare_solution_models_per_item(named_model_csvs, human_csv_path, output_dir, metric='accuracy (%)', top_k=3):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # 1. Load all model CSVs and concatenate
    model_dfs = []
    for path, model_name in named_model_csvs:
        df = pd.read_csv(path)
        df['model'] = model_name
        model_dfs.append(df)
    models_df = pd.concat(model_dfs, ignore_index=True)

    # 2. Load human CSV and compute average human scores per item
    human_df = pd.read_csv(human_csv_path)

    # Average human scores per item (mean across user_id)
    human_avg_df = human_df.groupby('item').agg({
        metric: 'mean',
        'average IoU': 'mean',
        'total samples': 'max'  # assuming total samples is same per item, just take max
    }).reset_index()
    human_avg_df['model'] = 'human_avg'

    # 3. Combine models_df with human_avg_df
    combined_df = pd.concat([models_df, human_avg_df], ignore_index=True)

    # 4. Validate total samples per item are consistent
    samples_per_item = combined_df.groupby('item')['total samples'].max()

    # Filter for only rows where accuracy > 0
    combined_df_nonzero = combined_df[combined_df[metric] > 0].copy()

    # Rank only among models with non-zero accuracy
    combined_df_nonzero['rank'] = combined_df_nonzero.groupby('item')[metric].rank(method='min', ascending=False)

    # Mark top-k
    combined_df_nonzero['top_k'] = combined_df_nonzero['rank'] <= top_k

    # Merge rank and top_k back into the original df (with NaN for zero-accuracy models)
    combined_df = combined_df.merge(
        combined_df_nonzero[['item', 'model', 'rank', 'top_k']],
        on=['item', 'model'],
        how='left'
    )

    # Prevent boolean indexing error
    combined_df['top_k'] = combined_df['top_k'].fillna(False)

    sum_item_difficulty = summarize_item_difficulty(combined_df=combined_df, output_dir=output_dir, metric=metric)

    # # 5. Calculate ranking of models per item (descending order, higher is better)
    # # We'll add a column 'rank' per item group
    # combined_df['rank'] = combined_df.groupby('item')[metric].rank(method='min', ascending=False)
    #
    # # 6. Find top_k models per item
    # combined_df['top_k'] = combined_df['rank'] <= top_k

    # 7. Create summary table: for each item, list models ordered by score
    item_model_order = (
        combined_df
        .sort_values(['item', metric], ascending=[True, False])
        .groupby('item')['model']
        .apply(list)
        .reset_index(name='models_ranked')
    )

    # 8. Summary of how many times each model appears in top_k across items
    top_models = combined_df[combined_df['top_k']]
    top_model_counts = top_models['model'].value_counts().reset_index()
    top_model_counts.columns = ['model', 'top_k_count']

    # Save combined results and summary tables
    combined_df.to_csv(output_dir / 'combined_model_scores.csv', index=False)
    item_model_order.to_csv(output_dir / 'item_model_order.csv', index=False)
    top_model_counts.to_csv(output_dir / 'top_model_counts_across_items.csv', index=False)

    # 9. Plot top_k counts (best models across items)
    plt.figure(figsize=(10, 6))
    sns.barplot(data=top_model_counts, x='model', y='top_k_count', palette='viridis')
    plt.xticks(rotation=45, ha='right')
    plt.title(f'Number of times each model appeared in top {top_k} across items')
    plt.tight_layout()
    plt.savefig(output_dir / f'top_{top_k}_model_counts.png')
    plt.close()

    # 10. Plot accuracy per item for each model (heatmap style)
    pivot = combined_df.pivot(index='item', columns='model', values=metric).fillna(0)
    plt.figure(figsize=(12, max(6, len(pivot) * 0.3)))
    sns.heatmap(pivot, annot=True, fmt=".1f", cmap='YlGnBu')
    plt.title(f'{metric} per item per model')
    plt.tight_layout()
    plt.savefig(output_dir / f'{metric.replace(" ", "_")}_heatmap_per_item.png')
    plt.close()

    print(f"Analysis done. Results saved to: {output_dir}")
    return combined_df, item_model_order, top_model_counts


def results_per_item_stat(named_model_csvs, human_csv_path, output_dir, metric="accuracy (%)"):
    os.makedirs(output_dir, exist_ok=True)

    # Load model data
    model_dfs = []
    for path, name in named_model_csvs:
        df = pd.read_csv(path)
        df["source"] = name
        model_dfs.append(df)
    model_all = pd.concat(model_dfs, ignore_index=True)

    # Load human data
    human_df_ = pd.read_csv(human_csv_path)
    human_df_["source"] = human_df_["user_id"]

    # Keep only needed columns and unify
    model_all = model_all[["item", metric, "source", "total samples"]]
    human_df_ = human_df_[["item", metric, "source", "total samples"]]

    # Combine all
    combined = pd.concat([model_all, human_df_], ignore_index=True)

    # Pivot the combined long-format df into wide format (for comparison_df)
    comparison_df = combined.pivot(index="item", columns="source", values="accuracy (%)").reset_index()

    # item difficulty
    # sum_item_difficulty = summarize_item_difficulty(combined_df=combined, output_dir=output_dir, metric=metric)

    # ANOVA and PostHoc stat
    # run_anova_posthoc_per_item(comparison_df=comparison_df, output_dir=output_dir, metric=metric)

    # scores per item
    # plot_scores_per_item(combined=combined, output_dir=output_dir, metric=metric)

    compare_solution_models_per_item(named_model_csvs=named_model_csvs, human_csv_path=human_csv_path,
                                     output_dir=output_dir, metric=metric)


if __name__ == "__main__":
    # data_json = "../data/test_data/test_data_kitchen_origin_filenames.json"
    data_json = "../data/test_data/test_data_kitchen.json"
    responses_json = "../baselines/human/test_responses_kitchen.json"
    output_json = "../baselines/human/scores_test_data.json"
    # mode = "partial"
    mode = "full"
    response_type = "human"

    give_score_on_data_fixed(data_json=data_json,
                       users_responses_json=responses_json,
                       scores_json=output_json,
                       response_type=response_type, mode=mode)

    # score_human_users(data_json=data_json,
    #                   responses_json=responses_json,
    #                   output_json=output_json, mode=mode,
    #                   return_per_item=True)

    named_model_csvs = [("../baselines/random/scores_random_test_data_kitchen_per_item.csv", "random"),
                        ("../models/chat_gpt/scores/scores_chatgpt_test_short_id_pos_lab_anchrs_ratio_per_item.csv",
                         "NOAM GPT-4"),
                        ("../models/dino/scores_dino_1_test_data_kitchen_per_item.csv", "dino_1"),
                        ("../models/dino/scores_dino_0.95_test_data_kitchen_per_item.csv", "dino_0.95"),
                        ("../models/dino/scores_dino_no_item_test_data_kitchen_per_item.csv", "dino_no_item"),
                        ("../models/gemini/scores_gemini_flash_1.5_test_data_kitchen_origin_per_item.csv",
                         "gemini_1.5"),
                        ("../models/gemini/scores_gemini_flash_2.5_test_data_kitchen_origin_per_item.csv",
                         "gemini_2.5"),
                        ("../models/gpt-4o/scores_chatgpt_baseline_test_kitchen_origin_images_parse_per_item.csv",
                         "gpt-4o"),
                        ("../models/kosmos2/scores_kosmos_test_data_kitchen_per_item.csv", "kosmos-2"),
                        ("../models/llama_3.3/scores_llama_test_short_id_pos_lab_anchrs_ratio_per_item.csv", "NOAM LLaMA-3.3"),
                        ("../models/llama_4/scores_llama_4_test_origin_images_parse_per_item.csv", "LLaMA-4"),
                        ("../models/qwen/scores_qwen_2.5_test_origin_images_parse_per_item.csv", "Qwen-2.5")]
    human_csv_path = "../baselines/human/scores_human_test_data_per_item.csv"
    output_dir = "stat_plots_per_item"
    # results_per_item_stat(named_model_csvs=named_model_csvs, human_csv_path=human_csv_path, output_dir=output_dir,
    #                       metric="accuracy (%)")

    # check_gemini_bbox()
    # calculate_user_accuracy(train_data_json="../data/train_data/train_data.json", user_responses_json="../baselines/human/cleaned_responses.json")
    # create_random_baseline(train_or_test_data_json="../data/test_data/test_data_no_kitchen.json", output_filename="../baselines/random/random_test_responses_no_kitchen.json", train_or_test="test")

    # split_human_responses_by_user(test_data_json="../data/test_data/test_data_kitchen.json",
    #                               user_responses_json="../data/upwork/test_cleaned_responses.json")
    # find_missing_responses_human_test(test_data_json="../data/test_data/test_data_kitchen.json")
    # find_missing_responses_dino(test_data_json="../data/test_data/test_data_kitchen.json",
    #                             responses_json="../models/dino/dino_test_responses_kitchen.json")

    # compute_average_containers(data_json_path=data_json)

    # t_test()
