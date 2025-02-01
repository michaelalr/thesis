import json
import os
import re

import firebase_admin
from firebase_admin import credentials, firestore


# Function to clean image_path
def clean_image_path(image_path):
    # Use regex to extract the part starting with 'thesis/images/test/...'
    match = re.search(r'images/.*', image_path)
    if match:
        # Replace 'thesis/' with './'
        cleaned_path = match.group(0).replace("thesis/", "")
        # If "random" or "Random" is in the path, replace "%20" with " "
        if "random" in cleaned_path.lower():
            cleaned_path = cleaned_path.replace("%20", " ")
        return cleaned_path

    return image_path  # Return the original path if no match


def extract_batch_number(file_name):
    # Regular expression to extract the batch number
    match = re.search(r'batch_(\d+)', file_name)
    if match:
        batch_number = int(match.group(1))  # Convert to integer if needed
        return batch_number
    return file_name  # Return the file name if no match


# Function to extract details from a single JSON file
def extract_details_from_file(file_path):
    details = set()
    if file_path.endswith('.json'):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                for entry in data:
                    user_id = entry.get('user_id')
                    chosen_item = entry.get('chosen_item')
                    image_path = clean_image_path(entry.get('image_path_html', ''))
                    batch_num = extract_batch_number(file_path)
                    if user_id and chosen_item and batch_num and image_path:
                        details.add((user_id, chosen_item, batch_num, image_path))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error reading file {file_path}: {e}")
    return details


# Function to extract details from a folder or specific files
def extract_details_from_folder(folder_path, specific_files=None):
    details = set()
    files_to_process = (
        specific_files if specific_files else
        [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith('.json')]
    )
    for file_path in files_to_process:
        if specific_files:
            details.update(extract_details_from_file(folder_path + file_path))
        else:
            details.update(extract_details_from_file(file_path))
    return details


def extract_details_from_db():
    # Initialize the Firebase Admin SDK
    cred = credentials.Certificate(
        'C:\\Users\\user2\\OneDrive - Bar-Ilan University - Students\\Documents\\miki\\biu\\thesis\\images\\application\\stored-items-containers-firebase-adminsdk-pf64z-5c7c8c19e1.json')
    firebase_admin.initialize_app(cred)

    # Fetch data from Firestore
    db = firestore.client()
    responses_ref = db.collection('user_responses')  # Replace with your collection name
    responses = responses_ref.stream()

    # Collect all responses in a list
    data = [response.to_dict() for response in responses]
    details = set()
    for entry in data:
        user_id = entry.get('user_id')
        chosen_item = entry.get('chosen_item')
        image_path = clean_image_path(entry.get('image_path'))
        batch_num = entry.get('batch_number')
        if user_id and chosen_item and batch_num and image_path:
            details.add((user_id, chosen_item, batch_num, image_path))
    return details


# Function to extract details from the large JSON file
def extract_details_from_large_json(large_json_file):
    details = set()
    with open(large_json_file, 'r') as file:
        data = json.load(file)
        for entry in data:
            user_id = entry.get('user_id')
            chosen_item = entry.get('chosen_item')
            image_path = clean_image_path(entry.get('image_path'))
            batch_num = entry.get('batch_number')
            if user_id and chosen_item and batch_num and image_path:
                details.add((user_id, chosen_item, batch_num, image_path))
    return details


# Function to find missing details
def find_missing_details(folder_details, large_json_details):
    return folder_details - large_json_details


# Input parameters
large_json_file = "upwork_responses.json"
# comparison_file = "output_batches/user_1/usr_1_Bottle_opener_batch_4.json"  # Replace with the JSON file path for comparison
# user_id_to_check = 1  # Replace with the desired user_id
# chosen_item_to_check = "Bottle opener"  # Replace with the desired chosen_item
folder_path = "output_batches/user_2/"  # Replace with the folder containing JSON files
specific_files_user_1 = ["usr_1_Bottle_opener_batch_1.json",
                         "usr_1_Bottle_opener_batch_2.json",
                         "usr_1_Bottle_opener_batch_3.json",
                         "usr_1_Bottle_opener_batch_4.json",
                         "usr_1_Bowl_batch_1.json",
                         "usr_1_Bowl_batch_2.json",
                         "usr_1_Bowl_batch_3.json",
                         "usr_1_Bowl_batch_4.json",
                         "usr_1_Cooking_oil_batch_1.json",
                         "usr_1_Cooking_oil_batch_2.json",
                         "usr_1_Cooking_oil_batch_3.json",
                         "usr_1_Cooking_oil_batch_4.json",
                         "usr_1_Cutting_board_batch_1.json",
                         "usr_1_Cutting_board_batch_2.json",
                         "usr_1_Cutting_board_batch_3.json",
                         "usr_1_Cutting_board_batch_4.json",
                         "usr_1_Cutting_knife_batch_1.json",
                         "usr_1_Cutting_knife_batch_2.json",
                         "usr_1_Cutting_knife_batch_3.json",
                         "usr_1_Cutting_knife_batch_4.json",
                         "usr_1_Dish_towels_batch_1.json",
                         "usr_1_Dish_towels_batch_2.json",
                         "usr_1_Dish_towels_batch_3.json",
                         "usr_1_Dish_towels_batch_4.json",
                         "usr_1_Mug_batch_1.json",
                         "usr_1_Mug_batch_2.json",
                         "usr_1_Mug_batch_3.json",
                         "usr_1_Mug_batch_4.json",
                         "usr_1_Pan_batch_1.json",
                         "usr_1_Pan_batch_2.json",
                         "usr_1_Pan_batch_3.json",
                         "usr_1_Pan_batch_4.json",
                         "usr_1_Plate_batch_1.json",
                         "usr_1_Plate_batch_2.json",
                         "usr_1_Plate_batch_3.json",
                         "usr_1_Plate_batch_4.json",
                         "usr_1_Pot_batch_1.json",
                         "usr_1_Pot_batch_2.json",
                         "usr_1_Pot_batch_3.json",
                         "usr_1_Pot_batch_4.json",
                         "usr_1_Spices_batch_1.json",
                         "usr_1_Spices_batch_2.json",
                         "usr_1_Spices_batch_3.json",
                         "usr_1_Spices_batch_4.json",
                         "usr_1_Spoon_batch_1.json",
                         "usr_1_Spoon_batch_2.json",
                         "usr_1_Spoon_batch_3.json",
                         "usr_1_Spoon_batch_4.json",
                         "usr_1_Tupperware_containers_batch_1.json",
                         "usr_1_Tupperware_containers_batch_2.json",
                         "usr_1_Tupperware_containers_batch_3.json",
                         "usr_1_Tupperware_containers_batch_4.json",
                         "usr_1_Val_Bottle_opener_batch_4.json",
                         "usr_1_Val_Iron_Tupperware_containers_batch_3.json",
                         "usr_1_Val_Random_Ear_toothpick_batch_2.json",
                         "usr_1_Val_Screwdriver_Painkiller_batch_1.json"
                         ]
# Set to None to process the whole folder or provide a specific list like ["usr_1_Bottle_opener_batch_4.json"]
specific_files_user_2 = ["usr_2_Cutting_knife_batch_1.json",
                         "usr_2_Cutting_knife_batch_2.json",
                         "usr_2_Cutting_knife_batch_3.json",
                         "usr_2_Cutting_knife_batch_4.json",
                         "usr_2_Dish_towels_batch_1.json",
                         "usr_2_Dish_towels_batch_2.json",
                         "usr_2_Dish_towels_batch_3.json",
                         "usr_2_Dish_towels_batch_4.json",
                         "usr_2_Mug_batch_1.json",
                         "usr_2_Mug_batch_2.json",
                         "usr_2_Mug_batch_3.json",
                         "usr_2_Mug_batch_4.json",
                         "usr_2_Pan_batch_1.json",
                         "usr_2_Pan_batch_2.json",
                         "usr_2_Pan_batch_3.json",
                         "usr_2_Pan_batch_4.json",
                         "usr_2_Plate_batch_1.json",
                         "usr_2_Plate_batch_2.json",
                         "usr_2_Plate_batch_3.json",
                         "usr_2_Plate_batch_4.json",
                         "usr_2_Pot_batch_1.json",
                         "usr_2_Pot_batch_2.json",
                         "usr_2_Pot_batch_3.json",
                         "usr_2_Pot_batch_4.json",
                         "usr_2_Spices_batch_1.json",
                         "usr_2_Spices_batch_2.json",
                         "usr_2_Spices_batch_3.json",
                         "usr_2_Spices_batch_4.json",
                         "usr_2_Spoon_batch_1.json",
                         "usr_2_Spoon_batch_2.json",
                         "usr_2_Spoon_batch_3.json",
                         "usr_2_Spoon_batch_4.json",
                         "usr_2_Tupperware_containers_batch_1.json",
                         "usr_2_Tupperware_containers_batch_2.json",
                         "usr_2_Tupperware_containers_batch_3.json",
                         "usr_2_Tupperware_containers_batch_4.json",
                         "usr_2_Bottle_opener_batch_1.json",
                         "usr_2_Bottle_opener_batch_2.json",
                         "usr_2_Bottle_opener_batch_3.json",
                         "usr_2_Bottle_opener_batch_4.json",
                         "usr_2_Bowl_batch_1.json",
                         "usr_2_Bowl_batch_2.json",
                         "usr_2_Bowl_batch_3.json",
                         "usr_2_Bowl_batch_4.json",
                         "usr_2_Cooking_oil_batch_1.json",
                         "usr_2_Cooking_oil_batch_2.json",
                         "usr_2_Cooking_oil_batch_3.json",
                         "usr_2_Cooking_oil_batch_4.json",
                         "usr_2_Cutting_board_batch_1.json",
                         "usr_2_Cutting_board_batch_2.json",
                         "usr_2_Cutting_board_batch_3.json",
                         "usr_2_Cutting_board_batch_4.json",
                         "usr_2_Val_Bottle_opener_batch_4.json",
                         "usr_2_Val_Iron_Tupperware_containers_batch_3.json",
                         "usr_2_Val_Random_Ear_toothpick_batch_2.json",
                         "usr_2_Val_Screwdriver_Painkiller_batch_1.json"
                         ]
specific_files_user_3 = ["usr_3_Plate_batch_1.json",
                         "usr_3_Plate_batch_2.json",
                         "usr_3_Plate_batch_3.json",
                         "usr_3_Plate_batch_4.json",
                         "usr_3_Pot_batch_1.json",
                         "usr_3_Pot_batch_2.json",
                         "usr_3_Pot_batch_3.json",
                         "usr_3_Pot_batch_4.json",
                         "usr_3_Spices_batch_1.json",
                         "usr_3_Spices_batch_2.json",
                         "usr_3_Spices_batch_3.json",
                         "usr_3_Spices_batch_4.json",
                         "usr_3_Spoon_batch_1.json",
                         "usr_3_Spoon_batch_2.json",
                         "usr_3_Spoon_batch_3.json",
                         "usr_3_Spoon_batch_4.json",
                         "usr_3_Tupperware_containers_batch_1.json",
                         "usr_3_Tupperware_containers_batch_2.json",
                         "usr_3_Tupperware_containers_batch_3.json",
                         "usr_3_Tupperware_containers_batch_4.json",
                         "usr_3_Bottle_opener_batch_1.json",
                         "usr_3_Bottle_opener_batch_2.json",
                         "usr_3_Bottle_opener_batch_3.json",
                         "usr_3_Bottle_opener_batch_4.json",
                         "usr_3_Bowl_batch_1.json",
                         "usr_3_Bowl_batch_2.json",
                         "usr_3_Bowl_batch_3.json",
                         "usr_3_Bowl_batch_4.json",
                         "usr_3_Cooking_oil_batch_1.json",
                         "usr_3_Cooking_oil_batch_2.json",
                         "usr_3_Cooking_oil_batch_3.json",
                         "usr_3_Cooking_oil_batch_4.json",
                         "usr_3_Cutting_board_batch_1.json",
                         "usr_3_Cutting_board_batch_2.json",
                         "usr_3_Cutting_board_batch_3.json",
                         "usr_3_Cutting_board_batch_4.json",
                         "usr_3_Cutting_knife_batch_1.json",
                         "usr_3_Cutting_knife_batch_2.json",
                         "usr_3_Cutting_knife_batch_3.json",
                         "usr_3_Cutting_knife_batch_4.json",
                         "usr_3_Dish_towels_batch_1.json",
                         "usr_3_Dish_towels_batch_2.json",
                         "usr_3_Dish_towels_batch_3.json",
                         "usr_3_Dish_towels_batch_4.json",
                         "usr_3_Mug_batch_1.json",
                         "usr_3_Mug_batch_2.json",
                         "usr_3_Mug_batch_3.json",
                         "usr_3_Mug_batch_4.json",
                         "usr_3_Pan_batch_1.json",
                         "usr_3_Pan_batch_2.json",
                         "usr_3_Pan_batch_3.json",
                         "usr_3_Pan_batch_4.json",
                         "usr_3_Val_Bottle_opener_batch_4.json",
                         "usr_3_Val_Iron_Tupperware_containers_batch_3.json",
                         "usr_3_Val_Random_Ear_toothpick_batch_2.json",
                         "usr_3_Val_Screwdriver_Painkiller_batch_1.json"
                         ]

# Extract details from the folder
# folder_details = extract_details_from_folder(folder_path, specific_files_user_2)
folder_details = extract_details_from_folder(folder_path)

# Extract details from the large JSON file
large_json_details = extract_details_from_large_json(large_json_file)
# large_json_details = extract_details_from_db()

# Find missing details
missing_details = find_missing_details(folder_details, large_json_details)

# Output results
if missing_details:
    print(f"Missing combinations ({len(missing_details)}):")
    for user_id, chosen_item, batch_num, image_path in missing_details:
        print(f"User ID: {user_id}, Chosen Item: {chosen_item}, Batch Number: {batch_num}, Image Path: {image_path}")
else:
    print("No missing combinations.")
