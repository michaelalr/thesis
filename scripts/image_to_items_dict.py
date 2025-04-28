import json
from collections import defaultdict
from scripts.compare_responses import clean_image_path

def create_image_to_items_dict(input_json_path, output_json_path):
    with open(input_json_path, 'r') as infile:
        data = json.load(infile)

    image_to_items = defaultdict(list)

    for entry in data:
        image_path = clean_image_path(entry["image_path"], is_test=True)
        chosen_item = entry["chosen_item"]
        image_to_items[image_path].append(chosen_item)

    # Save the result to a new JSON file
    with open(output_json_path, 'w') as outfile:
        json.dump(image_to_items, outfile, indent=2)

    print(f"Created mapping of image_path to chosen_items at: {output_json_path}")

if __name__ == '__main__':
    input_json_path = "../data/test_data/test_data.json"
    output_json_path = "../image_details/image_to_items_dict_test.json"
    create_image_to_items_dict(input_json_path=input_json_path, output_json_path=output_json_path)