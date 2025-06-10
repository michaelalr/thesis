import json
import os

def update_dino_json(dino_json_path, train_test_json_path, output_path):
    # Load the JSON files
    with open(dino_json_path, 'r') as f:
        dino_data = json.load(f)

    with open(train_test_json_path, 'r') as f:
        train_test_data = json.load(f)

    # Create a mapping: filename after 'X_segmented_' -> full train/test entry
    train_test_mapping = {}
    for entry in train_test_data:
        img_path = entry['image_path']
        filename = os.path.basename(img_path)
        # Extract after X_segmented_
        if '_segmented_' in filename:
            key = filename.split('_segmented_')[1]
            train_test_mapping[key] = entry

    results = []

    # Now update DINO data
    for entry in dino_data:
        dino_img_path = entry['image_path_html']
        dino_filename = os.path.basename(dino_img_path)
        if '_segmented_' in dino_filename:
            key = dino_filename.split('_segmented_')[1]
            matching_entry = train_test_mapping.get(key)
            if matching_entry:
                # Add the new 'image_path'
                entry['image_path'] = matching_entry['image_path']
                results.append(entry)

                # Prepare the 'chosen_polygon'
                # containers_mask_polygon = json.loads(entry['containers_mask_polygon'])
                # if isinstance(containers_mask_polygon, list) and len(containers_mask_polygon) == 1:
                #     chosen_polygon = containers_mask_polygon[0]
                #     # Save back as JSON string
                #     entry['chosen_polygon'] = json.dumps(chosen_polygon)
                # else:
                #     print(f"Unexpected containers_mask_polygon format in {dino_img_path}")

    # Save updated DINO JSON
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Updated DINO JSON saved to {output_path}")

if __name__ == '__main__':
    dino_json_path = "./image_details_test_dino_and_sam_no_item.json"
    train_test_json_path = "../../data/test_data/test_data_kitchen.json"
    output_path = "./dino_test_responses_kitchen_no_item.json"
    update_dino_json(dino_json_path, train_test_json_path, output_path)