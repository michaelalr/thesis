import os
import json
import re

# Function to clean image_path
def clean_image_path(image_path):
    # Use regex to extract the part starting with 'thesis/images/test/...'
    match = re.search(r'images/kitchen/.*', image_path)
    if match:
        # Replace 'thesis/' with './'
        return match.group(0).replace("thesis/", "")
    return image_path  # Return the original path if no match

def extract_image_paths(json_file, user_id, chosen_item):
    """
    Extract all image paths with a specific user_id and chosen_item.
    """
    image_paths = set()

    if json_file.endswith('.json'):
        with open(json_file, 'r') as file:
            data = json.load(file)
            for entry in data:
                if entry.get('user_id') == user_id and entry.get('chosen_item') == chosen_item:
                    image_paths.add(clean_image_path(entry['image_path']))
    return image_paths


def compare_image_paths(image_paths_1, image_paths_2):
    """
    Compare two sets of image paths and find missing ones.
    """
    missing_paths = image_paths_1 - image_paths_2
    return missing_paths


# Input parameters
json_file = "upwork_responses.json"
comparison_file = "output_batches/user_3/usr_3_Pot_batch_1.json"  # Replace with the JSON file path for comparison
user_id_to_check = 3  # Replace with the desired user_id
chosen_item_to_check = "Pot"  # Replace with the desired chosen_item

# Extract image paths for the specified user_id and chosen_item
image_paths_from_dir = extract_image_paths(json_file, user_id_to_check, chosen_item_to_check)

# Load image paths from the comparison JSON file
with open(comparison_file, 'r') as file:
    comparison_data = json.load(file)
    image_paths_from_comparison = {entry['image_path_html'] for entry in comparison_data}

# Find missing image paths
missing_image_paths = compare_image_paths(image_paths_from_comparison, image_paths_from_dir)

# Output results
if missing_image_paths:
    print(f"Missing image paths ({len(missing_image_paths)}):")
    for path in missing_image_paths:
        print(path)
else:
    print("No missing image paths.")
