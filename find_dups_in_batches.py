import os
import json
from collections import defaultdict

def find_duplicates_in_directory(is_dir, dir_or_json_path):
    duplicates = []
    seen = defaultdict(list)  # Dictionary to store occurrences of each combination
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
                all_data = json.load(file) # Add all objects to the list

    # Find duplicates by "image_path_html" and "chosen_item"
    for entry in all_data:
        key = (entry['image_path'], entry['chosen_item'])
        seen[key].append(entry)

    # Identify keys with more than one occurrence
    for key, occurrences in seen.items():
        if len(occurrences) > 1:
            duplicates.append((key, occurrences))

    return duplicates

# Specify the directory containing JSON files
# dir_or_json_path = "output_batches/user_3"
dir_or_json_path = "upwork_responses.json"
is_dir = False
# Find and print duplicates
duplicates = find_duplicates_in_directory(is_dir, dir_or_json_path)
if duplicates:
    print(f"Found {len(duplicates)} duplicate entries:")
    for (key, occurrences) in duplicates:
        print(f"\nDuplicate Key: {key}")
        for i, entry in enumerate(occurrences, 1):
            print(f"  Entry {i}: {entry}")
else:
    print("No duplicates found.")
