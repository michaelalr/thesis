import json
import random
import os
from math import ceil


def split_json_for_users(input_json_file, output_folder, num_users=3):
    # Read the input JSON file
    with open(input_json_file, 'r') as file:
        data = json.load(file)

    # Data is a list of image dictionaries
    images = data

    total_images = len(images)

    # Number of images that should be common to all users
    common_images_count = ceil(total_images * 0.1)

    # Randomly select common images (10% of total images)
    common_images = random.sample(images, common_images_count)

    # Remaining 90% of the images to be distributed among the users
    remaining_images = [image for image in images if image not in common_images]

    # Shuffle remaining images to ensure random distribution
    random.shuffle(remaining_images)

    # Determine how many images each user will get (divide remaining images equally)
    user_images = {f'user_{i + 1}': [] for i in range(num_users)}

    # Distribute remaining images to users
    for idx, image in enumerate(remaining_images):
        user_idx = idx % num_users  # Distribute images cyclically
        user_images[f'user_{user_idx + 1}'].append(image)

    # Create a JSON file for each user, including common images and their respective random images
    os.makedirs(output_folder, exist_ok=True)

    for user_id, images_for_user in user_images.items():
        # Combine common images with the images for the user
        user_data = common_images + images_for_user

        # Save user data to a JSON file
        output_file = os.path.join(output_folder, f'{user_id}.json')
        with open(output_file, 'w') as outfile:
            json.dump(user_data, outfile, indent=4)

        print(f"User data saved to {output_file}")

if __name__ == '__main__':
    # Example usage:
    input_json_file = 'C:\\Users\\user2\\PycharmProjects\\thesis\\image_details_mask.json'  # Path to the input JSON file
    output_folder = 'output_jsons'  # Folder to save the output JSON files
    num_users = 3  # Number of users

    split_json_for_users(input_json_file=input_json_file, output_folder=output_folder, num_users=num_users)
