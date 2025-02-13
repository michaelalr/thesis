import json
import os
import re
from io import BytesIO

import firebase_admin
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
import requests
from PIL import Image, ImageDraw
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
                clean_image = clean_image_path(image_path)
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


def check_empty_responses(all_responses, user_id):
    # Filter responses for user_id
    user_responses = [response for response in all_responses if response.get('user_id') == user_id]
    # Count responses with "chosen_polygon": "[]"
    empty_polygon_count = sum(1 for response in user_responses if response.get('chosen_polygon') == "[]")
    print(
        f"User {user_id} has {empty_polygon_count} responses with 'chosen_polygon': '[]' out of {len(user_responses)}.")


def remove_ips(data):
    # Count occurrences of each IP
    # ip_counts = Counter(entry["ip_address"] for entry in data)

    # Define the IPs to remove
    unwanted_ips = {"46.120.86.255", 'Unknown'}  # Set of IPs to remove
    # Filter out entries with these IPs
    filtered_ips = [entry for entry in data if entry["ip_address"] not in unwanted_ips]
    print(f"Removed {len(data) - len(filtered_ips)} entries.")
    return filtered_ips


def find_duplicates(data):
    # Convert JSON data to a DataFrame
    df = pd.DataFrame(data)
    # Define the fields to check for duplicates
    duplicate_fields = ["image_path", "chosen_polygon", "user_id", "chosen_item", "room_type", "batch_number"]
    # Find duplicate rows based on the specified fields
    df_no_duplicates = df.drop_duplicates(subset=duplicate_fields, keep='first')
    print(f"Removed duplicates. New dataset has {len(df_no_duplicates)} records.")

    # # Find duplicates based on core fields, but keep all occurrences
    # duplicates = df[df.duplicated(subset=duplicate_fields, keep=False)]
    # # Sort the duplicates to compare date and time differences
    # duplicates_sorted = duplicates.sort_values(by=duplicate_fields + ["date", "time"])
    # # Save duplicates to a CSV file for better comparison
    # duplicates_sorted.to_csv("duplicates_with_date_time.csv", index=False)
    return df_no_duplicates


def find_different_answers_per_user(df):
    # Group by key fields and filter groups with multiple distinct polygons
    polygon_groups = df.groupby(["user_id", "image_path", "chosen_item", "room_type", "batch_number"])
    filtered_groups = polygon_groups.filter(lambda x: x['chosen_polygon'].nunique() > 1)

    # Iterate over the filtered groups and display the polygons
    for (user_id, image_path, item, room, batch), group in filtered_groups.groupby(
            ["user_id", "image_path", "chosen_item", "room_type", "batch_number"]):
        try:
            # Load and prepare the image
            response = requests.get(image_path)
            img = Image.open(BytesIO(response.content)).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Draw each polygon with a different color
            colors = ["red", "green", "blue", "purple", "orange"]
            for idx, (_, row) in enumerate(group.iterrows()):
                polygon = json.loads(row['chosen_polygon'])
                polygon_tuples = [tuple(coord) for coord in polygon]
                draw.polygon(polygon_tuples, outline=colors[idx % len(colors)], width=3)
                draw.text(polygon_tuples[0], f"Polygon {idx + 1}", fill=colors[idx % len(colors)])

            # Plot inline in PyCharm
            plt.figure(figsize=(10, 6))
            plt.imshow(img)
            plt.title(f"User: {user_id}, Item: {item}, Room: {room} ,Batch: {batch}")
            plt.axis("off")
            plt.show()

        except Exception as e:
            print(f"Failed to process {image_path}: {e}")

    print("draw all")


def clean_data(all_responses):
    filtered_ips = remove_ips(all_responses)
    df_no_duplicates = find_duplicates(filtered_ips)
    find_different_answers_per_user(df_no_duplicates)

    # Save the cleaned JSON back to the file
    with open("upwork_responses_cleaned.json", "w") as file:
        json.dump(filtered_ips, file, indent=4)


if __name__ == "__main__":
    # json_filename = save_firebase_as_json()
    json_filename = 'upwork_responses.json'
    # Load the JSON file
    with open(json_filename, 'r') as f:
        all_responses = json.load(f)

    check_empty_responses(all_responses, 1)
    check_empty_responses(all_responses, 2)
    check_empty_responses(all_responses, 3)

    clean_data(all_responses)

    responses_by_item_and_user = get_user_responses(responses=all_responses)

    plot_images_polygons(responses_by_item_and_user=responses_by_item_and_user)

    # Directory where all JSON response files are stored
    # json_files_directory = "responses"  # Change this to your directory name
    # main(json_files_directory)
