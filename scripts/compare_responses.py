import json
import os
import re
from ast import literal_eval
import random
import cv2
import firebase_admin
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from PIL import Image
from firebase_admin import credentials, firestore
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


def give_score_on_data(data_json, users_responses_json, scores_json, response_type="human"):
    # Load correct annotations
    with open(data_json, "r") as f:
        correct_annotations = json.load(f)

    # Load user responses
    with open(users_responses_json, "r") as f:
        user_responses = json.load(f)

    # Convert correct annotations to a dictionary for quick lookup
    correct_lookup = {
        (entry["image_path"], entry["chosen_item"]): literal_eval(entry["chosen_polygon"])
        for entry in correct_annotations
    }

    # Count correct responses per user
    user_scores = {}
    total_attempts = {}
    iou_scores = {}

    for response in user_responses:
        if response_type == "human":
            user_id = response["user_id"]
        elif response_type == "kosmos":
            user_id = "kosmos"
        elif response_type == "chatgpt":
            user_id = "chatgpt"
        elif response_type == "gemini":
            user_id = "gemini"
        else:
            user_id = "random"
        image_path = response["image_path"]
        chosen_item = response["chosen_item"]

        if response_type == "kosmos":
            entities = literal_eval(response["entities"])
            if len(entities) > 0:
                chosen_bbox = entities[0][2][0]  # Assuming you only want the first bbox
                suffix_image_path = clean_image_path(image_path=response["image_path"], is_test=("test" in data_json))
                chosen_polygon = denormalize_bbox_to_polygon(chosen_bbox, suffix_image_path)
            else:
                chosen_polygon = []  # or None if no bbox was found
        elif response_type == "gemini":
            if response["gemini_bbox_polygon_string"] == "[[0, 0], [0, 0], [0, 0], [0, 0]]":
                chosen_polygon = []
            else:
                chosen_polygon = literal_eval(response["gemini_bbox_polygon_string"])
        else:
            chosen_polygon = literal_eval(response["chosen_polygon"])

        # Total attempts per user
        total_attempts[user_id] = total_attempts.get(user_id, 0) + 1

        # Check if the chosen polygon matches the correct one
        correct_polygon = correct_lookup.get((image_path, chosen_item))
        if correct_polygon:
            # Compute IoU score
            iou = compute_iou(correct_polygon, chosen_polygon)
            iou_scores[user_id] = iou_scores.get(user_id, []) + [iou]

            # In Random or human cases - if IoU is 1, count it as a correct response
            if response_type == "human" or response_type == "random" or response_type == "chatgpt":
                if iou == 1.0:
                    user_scores[user_id] = user_scores.get(user_id, 0) + 1
            # In other models like kosmos - if IoU >= 0.5, count it as a correct response
            elif response_type == "kosmos":
                if iou >= 0.5:
                    user_scores[user_id] = user_scores.get(user_id, 0) + 1
            elif response_type == "gemini":
                if iou >= 0.5:
                    user_scores[user_id] = user_scores.get(user_id, 0) + 1

    # Compute percentage scores
    user_percentages = {
        user: (user_scores.get(user, 0) / total_attempts[user]) * 100
        for user in total_attempts
    }

    # Compute average IoU per user
    user_iou_avg = {
        user: sum(iou_scores[user]) / len(iou_scores[user]) if user in iou_scores else 0.0
        for user in total_attempts
    }

    # Convert to DataFrame for better visualization
    df_scores = pd.DataFrame([
        {"user_id": user, "correct_answers": user_scores.get(user, 0),
         "total_attempts": total_attempts[user], "accuracy (%)": user_percentages[user],
         "average_IoU": user_iou_avg[user]}
        for user in total_attempts
    ])

    # Print results
    print(df_scores)

    # Save to a JSON file if needed
    df_scores.to_json(scores_json, orient="records", indent=4)

    # ---- PLOT ----
    plt.figure(figsize=(10, 6))
    sns.barplot(x=df_scores["user_id"], y=df_scores["accuracy (%)"], palette="viridis")

    # Customize plot
    plt.xlabel("User ID", fontsize=12)
    plt.ylabel("Accuracy (%)", fontsize=12)
    plt.title("User Accuracy in Choosing the Correct Annotation", fontsize=14)
    plt.ylim(0, 100)
    plt.xticks(rotation=45)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    # Show plot
    plt.show()

def create_random_baseline(train_or_test_data_json, train_or_test="train"):
    # Load image details
    with open(train_or_test_data_json, "r") as f:
        image_details = json.load(f)

    random_responses = []

    # Iterate over image details
    for entry in image_details:
        containers = literal_eval(entry["containers_polygons"])  # Convert string to list
        if containers:  # Ensure there are containers to choose from
            chosen_polygon = random.choice(containers)  # Select a random container

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
    file_name = "random_" + train_or_test + "_responses.json"
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


if __name__ == "__main__":
    give_score_on_data(data_json="../data/train_data/train_data.json", users_responses_json="../models/chat_gpt/chatgpt_train_responses_2.json",
                       scores_json="../models/chat_gpt/scores_chatgpt_train_data_2.json", response_type="chatgpt")
    # check_gemini_bbox()
