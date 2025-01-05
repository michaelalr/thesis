import json
import os
import re

import matplotlib.pyplot as plt
from PIL import Image


# Function to clean image_path
def clean_image_path(image_path):
    # Use regex to extract the part starting with 'thesis/images/test/...'
    match = re.search(r'images/test/.*', image_path)
    print(match)
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


# Run the program
if __name__ == "__main__":
    # Directory where all JSON response files are stored
    json_files_directory = "responses"  # Change this to your directory name
    main(json_files_directory)
