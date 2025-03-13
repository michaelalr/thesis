import json
import re
import os
from collections import OrderedDict


def extract_number(image_path):
    """Extract the number right before '_a.jpg' in the image filename."""
    match = re.search(r'_(\d+)_a\.jpg', image_path)
    return int(match.group(1)) if match else float('inf')  # Default to inf if no match is found


def reorder_data(data):
    """Reorders JSON data by 'chosen_item' and then sorts by extracted number."""
    grouped_data = {}

    # Group images by chosen_item
    for item in data:
        chosen_item = item.get("chosen_item", "unknown")
        if chosen_item not in grouped_data:
            grouped_data[chosen_item] = []
        grouped_data[chosen_item].append(item)

    # Sort within each group based on the extracted number
    for chosen_item in grouped_data:
        grouped_data[chosen_item].sort(key=lambda x: extract_number(x["image_path_html"]))

    # Flatten the reordered structure
    ordered_list = []
    for chosen_item in sorted(grouped_data.keys()):  # Sort items alphabetically
        ordered_list.extend(grouped_data[chosen_item])

    return ordered_list


def create_batches(json_file, reorder_json=True):
    with open(json_file, 'r') as file:
        data = json.load(file)

    if reorder_json:
        data = reorder_data(data)

    # Initialize lists for each category
    screwdriver_images = []
    painkiller_images = []
    random_images = []
    ear_toothpick_images = []
    iron_images = []
    food_containers_images = []
    bottle_opener_images = []

    # Categorize the items
    for item in data:
        item['user_id'] = 1  # Add user_id field
        if 'screwdriver' in item['image_path_html'].lower():
            screwdriver_images.append(item)
        elif 'painkiller' in item['image_path_html'].lower():
            painkiller_images.append(item)
        elif 'random' in item['image_path_html'].lower():
            random_images.append(item)
        elif 'ear_toothpick' in item['image_path_html'].lower():
            ear_toothpick_images.append(item)
        elif 'iron' in item['image_path_html'].lower():
            iron_images.append(item)
        elif 'food_containers' in item['image_path_html'].lower():
            food_containers_images.append(item)
        elif 'bottle_opener' in item['image_path_html'].lower():
            bottle_opener_images.append(item)

    # Combine lists to form batches
    batch_1 = screwdriver_images + painkiller_images
    batch_2 = random_images + ear_toothpick_images
    batch_3 = iron_images + food_containers_images
    batch_4 = bottle_opener_images

    # Ensure output directory exists
    output_dir = "output_batches/build_test_set"
    os.makedirs(output_dir, exist_ok=True)

    # Save the batches into separate JSON files
    with open(output_dir + '/usr_4_Val_Screwdriver_Painkiller_batch_1.json', 'w') as b1, open(
            output_dir + '/usr_4_Val_Random_Ear_toothpick_batch_2.json', 'w') as b2, open(
            output_dir + '/usr_4_Val_Iron_Tupperware_containers_batch_3.json', 'w') as b3, open(
            output_dir + '/usr_4_Val_Bottle_opener_batch_4.json', 'w') as b4:
        json.dump(batch_1, b1, indent=4)
        json.dump(batch_2, b2, indent=4)
        json.dump(batch_3, b3, indent=4)
        json.dump(batch_4, b4, indent=4)


# Example usage: Set reorder_json=True to enable reordering
create_batches('image_details_validation_new.json', reorder_json=True)
