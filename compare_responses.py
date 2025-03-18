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


# Function to clean image_path
def clean_image_path(image_path):
    # Use regex to extract the part starting with 'thesis/images/test/...'
    match = re.search(r'images/kitchen/.*', image_path)
    if match:
        # Replace 'thesis/' with './'
        return "./" + match.group(0).replace("thesis/", "")
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
    json_filename = 'upwork_responses.json'
    with open(json_filename, 'w') as f:
        json.dump(all_responses, f, indent=4)

    print("Data saved to upwork_responses.json")

    return json_filename


def show_annotation_per_user_and_item():
    # json_filename = save_firebase_as_json()
    json_filename = 'upwork_responses_rotate.json'
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


def give_score_on_test_data(test_data_json, users_test_responses_json, is_human=True):
    # Load correct annotations
    with open(test_data_json, "r") as f:
        correct_annotations = json.load(f)

    # Load user responses
    with open(users_test_responses_json, "r") as f:
        user_responses = json.load(f)

    # Convert correct annotations to a dictionary for quick lookup
    correct_lookup = {
        (entry["image_path"], entry["chosen_item"]): literal_eval(entry["chosen_polygon"])
        for entry in correct_annotations
    }

    # Count correct responses per user
    user_scores = {}
    total_attempts = {}

    for response in user_responses:
        user_id = response["user_id"] if is_human else "random"
        image_path = response["image_path"]
        chosen_item = response["chosen_item"]
        chosen_polygon = literal_eval(response["chosen_polygon"])

        # Total attempts per user
        total_attempts[user_id] = total_attempts.get(user_id, 0) + 1

        # Check if the chosen polygon matches the correct one
        correct_polygon = correct_lookup.get((image_path, chosen_item))
        if correct_polygon and chosen_polygon == correct_polygon:
            user_scores[user_id] = user_scores.get(user_id, 0) + 1

    # Compute percentage scores
    user_percentages = {
        user: (user_scores.get(user, 0) / total_attempts[user]) * 100
        for user in total_attempts
    }

    # Convert to DataFrame for better visualization
    df_scores = pd.DataFrame([
        {"user_id": user, "correct_answers": user_scores.get(user, 0),
         "total_attempts": total_attempts[user], "accuracy (%)": user_percentages[user]}
        for user in total_attempts
    ])

    # Print results
    print(df_scores)

    # Save to a JSON file if needed
    df_scores.to_json("user_accuracy_scores_test_data.json", orient="records", indent=4)

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

if __name__ == "__main__":
    give_score_on_test_data(test_data_json="train_data.json", users_test_responses_json="random_train_responses.json", is_human=False)
