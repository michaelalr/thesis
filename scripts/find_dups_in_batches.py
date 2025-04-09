import os
import json
from collections import defaultdict


def find_duplicates_in_directory(is_dir, dir_or_json_path, fields_list):
    duplicates = []
    all_data = []  # To store all JSON objects

    if is_dir:
        # Iterate through all JSON files in the directory
        for filename in os.listdir(dir_or_json_path):
            if filename.endswith('.json'):
                file_path = os.path.join(dir_or_json_path, filename)
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    all_data.extend(data)  # Add all objects to the list
    else:
        if dir_or_json_path.endswith('.json'):
            with open(dir_or_json_path, 'r') as file:
                all_data = json.load(file)  # Add all objects to the list

    # Group data by user_id
    user_data = defaultdict(list)
    for entry in all_data:
        user_data[entry['user_id']].append(entry)

    # Find duplicates for each user
    for user_id, entries in user_data.items():
        seen = defaultdict(list)  # Store occurrences of each combination for the user
        for entry in entries:
            key = []
            for field in fields_list:
                key.append(entry[field])
            # key = (entry['image_path'], entry["chosen_polygon"], entry["ip_address"], entry['chosen_item'], entry["room_type"], entry["batch_number"])
            seen[tuple(key)].append(entry)

        # Identify keys with more than one occurrence
        for key, occurrences in seen.items():
            if len(occurrences) > 1:
                duplicates.append((user_id, key, occurrences))

    return duplicates


def main(is_check_responses):
    if is_check_responses:
        dir_or_json_path = "../data/upwork/upwork_responses_cleaned.json"
        is_dir = False
        fields_list = ["image_path", "chosen_polygon", "ip_address", "user_id", "chosen_item", "room_type",
                       "batch_number"]
    else:
        dir_or_json_path = "../output_batches/user_2"
        is_dir = True
        fields_list = ["image_path_html", "num_detections", "containers_mask_polygon", "room_type", "chosen_item"]

    # Find and print duplicates
    duplicates = find_duplicates_in_directory(is_dir=is_dir, dir_or_json_path=dir_or_json_path,
                                              fields_list=fields_list)
    if duplicates:
        print(f"Found {len(duplicates)} duplicate entries:")
        for user_id, key, occurrences in duplicates:
            print(f"\nUser ID: {user_id} | Duplicate Key: {key}")
            for i, entry in enumerate(occurrences, 1):
                print(f"  Entry {i}: {entry}")
    else:
        print("No duplicates found.")


if __name__ == '__main__':
    is_check_responses = False
    main(is_check_responses=is_check_responses)
