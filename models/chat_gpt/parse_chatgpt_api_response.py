import json
import re
import os
from urllib.parse import urljoin

def convert_bbox_to_points(bbox):
    """Convert bbox [x_min, y_min, x_max, y_max] to rectangle polygon [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]"""

    x_min, y_min, x_max, y_max = bbox

    # Return as rectangle polygon: top-left, bottom-left, bottom-right, top-right
    return [
        [x_min, y_min],
        [x_min, y_max],
        [x_max, y_max],
        [x_max, y_min]
    ]

def clean_bbox_string(bbox_str):
    if not bbox_str or not any(char.isdigit() for char in bbox_str):
        return []

    # Remove unwanted wrappers
    bbox_str = bbox_str.replace("```json", "").replace("```plaintext", "").replace("```", "")
    bbox_str = bbox_str.replace("\\[", "[").replace("\\]", "]")
    bbox_str = bbox_str.strip()

    # Use regular expression to find all groups like [x,y] or lists of numbers
    try:
        list_of_lists = []
        matches = re.findall(r'\[([^\[\]]+)\]', bbox_str)
        for match in matches:
            numbers = [int(num.strip()) for num in match.split(',') if num.strip().isdigit()]
            if len(numbers) == 2:  # [x, y]
                list_of_lists.append(numbers)
            elif len(numbers) == 4:  # [x1, y1, x2, y2]
                list_of_lists.append(numbers)
            elif len(numbers) == 8:  # [x1, y1, x2, y2, x3, y3, x4, y4] - flatten polygon format
                list_of_lists.append([[numbers[0], numbers[1]],
                                      [numbers[2], numbers[3]],
                                      [numbers[4], numbers[5]],
                                      [numbers[6], numbers[7]]])
            else:
                # Ignore invalid or weird entries
                pass

        # If inside 8 numbers we created a list of lists, flatten it
        final_list = []
        for entry in list_of_lists:
            if isinstance(entry[0], list):
                final_list.extend(entry)  # extend if it's list of points
            else:
                final_list.append(entry)

        return final_list

    except Exception as e:
        print(f"Failed to parse bbox: {bbox_str}, error: {e}")
        return []


def fix_bboxes_format(input_json_path, output_json_path):
    # Load original data
    with open(input_json_path, "r") as f:
        data = json.load(f)

    base_url = "https://michaelalr.github.io/thesis/"
    fixed_data = []
    for image_path, items_list in data.items():
        relative_path = image_path.lstrip("../")  # remove "../" from the beginning
        full_image_path = urljoin(base_url, relative_path)
        for item_data in items_list:
            item_name = item_data.get("item", "")
            bbox_str = item_data.get("bbox", "")
            cleaned_bbox = clean_bbox_string(bbox_str)

            # check if the bbox is 4 numbers (one list of 4 numbers)
            if len(cleaned_bbox) == 1 and len(cleaned_bbox[0]) == 4:
                bbox = cleaned_bbox[0]
                try:
                    cleaned_bbox = convert_bbox_to_points(bbox)
                except Exception as e:
                    print(f"Failed to denormalize bbox for {image_path}, error: {e}")
                    cleaned_bbox = []

            fixed_data.append({
                "image_path": full_image_path,
                "chosen_item": item_name,
                "chosen_polygon": json.dumps(cleaned_bbox)
            })


    # Save cleaned version
    with open(output_json_path, "w") as f:
        json.dump(fixed_data, f, indent=2)

    print(f"Finished cleaning. Saved to {output_json_path}")


if __name__ == '__main__':
    input_json_path = "./chatgpt_baseline.json"
    output_json_path = "./chatgpt_baseline_parse.json"
    fix_bboxes_format(input_json_path=input_json_path, output_json_path=output_json_path)
