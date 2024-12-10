import json
import os
from itertools import cycle

# Input data
kitchen_items = ["Bottle opener", "Tupperware containers", "Dish towels", "Cutting board", "Bowl", "Spices", "Spoon", "Mug", "Plate", "Pot", "Pan", "Cutting knife", "Cooking oil"]
num_users = 3
images_per_item = 500
common_images_percentage = 0.16  # 16%
common_images_per_item = round(common_images_percentage * images_per_item)
unique_images_per_item = images_per_item - common_images_per_item
unique_images_per_user = unique_images_per_item // num_users
batch_size = (unique_images_per_user + common_images_per_item) // 4  # 4 batches
output_folder = "output_batches"

# Load the input JSON file
with open("image_details.json", "r") as f:
    all_images = json.load(f)

# Filter images with num_detections >= 3
valid_images = [
    img for img in all_images
    if img["num_detections"] >= 3
]

# Ensure enough images are available
if len(valid_images) < unique_images_per_user:
    raise ValueError("Not enough valid images to distribute.")

# Create circular iterator for valid images
image_cycle = cycle(valid_images)

# Generate JSON files
for item_index, item in enumerate(kitchen_items):
    # Allocate common images (without user_id for now)
    common_images = [
        {
            "image_path_html": img["image_path_html"],
            "num_detections": img["num_detections"],
            "containers_mask_polygon": img["containers_mask_polygon"],
            "room_type": img["room_type"],
            "chosen_item": item,
        }
        for img in [next(image_cycle) for _ in range(common_images_per_item)]
    ]

    for user_id in range(1, num_users + 1):
        # Create a user-specific folder
        user_folder = f"{output_folder}/user_{user_id}"
        os.makedirs(user_folder, exist_ok=True)

        # Add user_id to the common images
        user_common_images = [
            {**img, "user_id": user_id} for img in common_images
        ]

        # Allocate unique images
        unique_images = [
            {
                "user_id": user_id,
                "image_path_html": img["image_path_html"],
                "num_detections": img["num_detections"],
                "containers_mask_polygon": img["containers_mask_polygon"],
                "room_type": img["room_type"],
                "chosen_item": item,
            }
            for img in [next(image_cycle) for _ in range(unique_images_per_user)]
        ]

        # Combine common and unique images
        all_batches = user_common_images + unique_images
        print("all_batches = ", len(all_batches))

        # Split into batches
        for batch_num in range(4):
            batch_images = all_batches[batch_num * batch_size:(batch_num + 1) * batch_size]
            batch_filename = f"{user_folder}/item_{item_index + 1}_batch_{batch_num + 1}.json"
            with open(batch_filename, "w") as batch_file:
                json.dump(batch_images, batch_file, indent=4)

print(f"JSON files created successfully in '{output_folder}'.")
