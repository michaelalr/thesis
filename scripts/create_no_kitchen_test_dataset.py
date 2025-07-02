import json
import os
import re


def create_no_kitchen_dataset(full_data_json, kitchen_data_json, non_kitchen_data_json):
    # Load first JSON (190 entries)
    with open(full_data_json, "r") as f:
        all_data = json.load(f)

    # Load second JSON (100 entries)
    with open(kitchen_data_json, "r") as f:
        subset_data = json.load(f)

    # Get set of image_paths in the subset to exclude
    subset_paths = set(entry["image_path"] for entry in subset_data)

    # Filter out entries from all_data whose image_path is in subset_paths
    leftover_entries = [entry for entry in all_data if entry["image_path"] not in subset_paths]

    print(f"Total entries in all_data: {len(all_data)}")
    print(f"Entries in subset_data: {len(subset_data)}")
    print(f"Entries leftover: {len(leftover_entries)}")

    # Save leftover entries to new JSON
    with open(non_kitchen_data_json, "w") as f:
        json.dump(leftover_entries, f, indent=2)


def normalize_image_path(path):
    """Normalize image path by removing prefix like 'X_segmented_' or 'XX_segmented_' and return filename."""
    filename = os.path.basename(path)
    # Remove leading digits + '_segmented_' prefix (e.g., "11_segmented_", "26_segmented_")
    filename = re.sub(r"^\d+_segmented_", "", filename)
    # Normalize multiple underscores after 'Food_containers' (e.g. Food_containers__ or Food_containers_)
    filename = re.sub(r"(Food_containers)_{1,2}", r"\1_", filename)
    return filename


def create_no_kitchen_image_details(full_image_details_json, item_dict_no_kitchen_json, no_kitchen_image_details_json):
    # Load your big JSON list (list of dicts)
    with open(full_image_details_json, "r") as f:
        big_data = json.load(f)

    # Load image_to_items dict (keys are normalized image paths)
    with open(item_dict_no_kitchen_json, "r") as f:
        image_to_items = json.load(f)

    # Normalize keys from image_to_items for matching
    normalized_keys = {os.path.basename(k): k for k in image_to_items.keys()}

    filtered_data = []
    for entry in big_data:
        norm_name = normalize_image_path(entry["image_path_html"])
        if norm_name in normalized_keys:
            filtered_data.append(entry)

    print(f"Filtered {len(filtered_data)} entries from {len(big_data)} total.")

    # Save filtered JSON
    with open(no_kitchen_image_details_json, "w") as f:
        json.dump(filtered_data, f, indent=2)


if __name__ == '__main__':
    full_data_json = "../data/test_data/test_data_origin_filenames.json"
    kitchen_data_json = "../data/test_data/test_data_kitchen_origin_filenames.json"
    non_kitchen_data_json = "../data/test_data/test_data_no_kitchen_origin_filenames.json"
    # create_no_kitchen_dataset(full_data_json=full_data_json, kitchen_data_json=kitchen_data_json,
    #                           non_kitchen_data_json=non_kitchen_data_json)

    full_image_details_json = "../image_details/image_details_test_with_labels.json"
    item_dict_no_kitchen_json = "../image_details/image_to_items_dict_test_no_kitchen_origin.json"
    no_kitchen_image_details_json = "../image_details/image_details_test_no_kitchen_with_labels.json"
    create_no_kitchen_image_details(full_image_details_json, item_dict_no_kitchen_json, no_kitchen_image_details_json)
