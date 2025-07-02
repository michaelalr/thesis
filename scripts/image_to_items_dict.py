import json
import os
from collections import defaultdict

from scripts.compare_responses import clean_image_path


def create_image_to_items_dict(input_json_path, output_json_path):
    with open(input_json_path, 'r') as infile:
        data = json.load(infile)

    image_to_items = defaultdict(list)

    for entry in data:
        image_path = clean_image_path(entry["image_path"], is_test=True)
        # image_path = clean_image_path(entry["image_path_html"], is_test=True)
        # image_path = "../images/test_no_kitchen_original/" + entry["image_path"]
        chosen_item = entry["chosen_item"]
        image_to_items[image_path].append(chosen_item)

    # Save the result to a new JSON file
    with open(output_json_path, 'w') as outfile:
        json.dump(image_to_items, outfile, indent=2)

    print(f"Created mapping of image_path to chosen_items at: {output_json_path}")


def create_subset_data_based_on_dict(image_details_dict_json, data_json, data_subset_json):
    # Load image_dict
    with open(image_details_dict_json, 'r') as f:
        image_dict = json.load(f)

    # Load train_data
    with open(data_json, 'r') as f:
        train_data = json.load(f)

    # Convert image_dict keys to filename → item list mapping
    image_items = {}
    for full_path, items in image_dict.items():
        filename = os.path.basename(full_path)
        image_items[filename] = items

    # Create the filtered subset
    subset = []
    for entry in train_data:
        train_file_path = entry["image_path"]
        chosen_item = entry["chosen_item"]

        # if train_file_path in image_items:
        train_filename = os.path.basename(train_file_path)
        if train_filename in image_items:
            # if chosen_item in image_items[train_file_path]:
            if chosen_item in image_items[train_filename]:
                subset.append(entry)

    # Save the subset
    with open(data_subset_json, 'w') as f:
        json.dump(subset, f, indent=2)

    print(f"Filtered entries: {len(subset)} saved to '{data_subset_json}'")


def find_missing_pairs_from_dict(image_details_dict_json, model_responses_json, missing_pairs_json):
    # Load the image_dict
    with open(image_details_dict_json, "r") as f:
        image_dict = json.load(f)

    # Load the model responses
    with open(model_responses_json, "r") as f:
        model_responses = json.load(f)

    # Step 1: Build the full set of expected (filename, item) pairs
    expected_pairs = set()
    for path, items in image_dict.items():
        filename = os.path.basename(path)  # e.g., "10_segmented_sun_aaslbwtcdcwjukuo.jpg"
        for item in items:
            expected_pairs.add((filename, item))

    # Step 2: Build the set of actual (filename, item) pairs in the responses
    actual_pairs = set()
    for entry in model_responses:
        url_path = entry["image_path"]
        filename = os.path.basename(url_path)  # extract just the filename
        item = entry["chosen_item"]
        actual_pairs.add((filename, item))

    # Step 3: Compute the difference
    missing_pairs = expected_pairs - actual_pairs

    # Step 4: Print or save the missing pairs
    print(f"Missing pairs ({len(missing_pairs)}):")
    for filename, item in sorted(missing_pairs):
        print(f"{filename} -> {item}")

    # Optional: Save to JSON or text file
    # with open(missing_pairs_json, "w") as f:
    #     json.dump(list(missing_pairs), f, indent=2)


if __name__ == '__main__':
    # input_json_path = "../data/test_data/test_data.json"
    # output_json_path = "../image_details/image_to_items_dict_test.json"
    # create_image_to_items_dict(input_json_path=input_json_path, output_json_path=output_json_path)

    # image_details_dict_json = "../image_details/image_to_items_dict_subset_origin_images.json"
    # data_json = "../data/train_data/train_data_origin_filenames.json"
    # data_subset_json = "../data/train_data/train_data_subset_origin_filenames.json"
    # create_subset_data_based_on_dict(image_details_dict_json, data_json, data_subset_json)

    image_details_dict_json = "../image_details/image_to_items_dict_subset.json"
    model_responses_json = "../models/llama/llama_short_id_pos_lab_anchrs_ratio.json"
    missing_pairs_json = ""
    find_missing_pairs_from_dict(image_details_dict_json=image_details_dict_json,
                                 model_responses_json=model_responses_json, missing_pairs_json=missing_pairs_json)
