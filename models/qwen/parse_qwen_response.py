import json
import os
import re
from urllib.parse import urljoin
from PIL import Image

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

def clean_bbox_string_extended(bbox_str):
    if not bbox_str or not any(char.isdigit() for char in bbox_str):
        return []

    # Remove markdown code block markers and escape characters
    bbox_str = bbox_str.replace("```json", "").replace("```", "").replace("\\[", "[").replace("\\]", "]").strip()

    try:
        # Try parsing as JSON (can be list of lists, list of dicts, or list of numbers)
        parsed = json.loads(bbox_str)

        if isinstance(parsed, list):
            bboxes = []

            for entry in parsed:
                if isinstance(entry, dict) and "bbox_2d" in entry:
                    coords = entry["bbox_2d"]
                    if len(coords) == 4:
                        bboxes.append(coords)

                elif isinstance(entry, list):
                    # Support both 4-point bbox or 8-point polygon in one list
                    if len(entry) == 4:
                        bboxes.append(entry)
                    elif len(entry) == 8:
                        polygon = [[entry[0], entry[1]], [entry[2], entry[3]],
                                   [entry[4], entry[5]], [entry[6], entry[7]]]
                        bboxes.append(polygon)

                elif isinstance(entry, (int, float)):
                    # Flat list case (e.g. [x1,y1,x2,y2,...]) not wrapped in sublists
                    # e.g. [349, 33, 510, 463, 686, 452, 885, 1091]
                    flat = parsed
                    if len(flat) == 4:
                        bboxes.append(flat)
                    elif len(flat) == 8:
                        bboxes.append([[flat[0], flat[1]], [flat[2], flat[3]],
                                       [flat[4], flat[5]], [flat[6], flat[7]]])
                    break  # processed as one flat list
            return bboxes

    except Exception:
        pass

    # Fallback: regex for [x1, y1, x2, y2]
    matches = re.findall(r'\[([0-9,\s]+)\]', bbox_str)
    bboxes = []
    for match in matches:
        numbers = [int(n.strip()) for n in match.split(',') if n.strip().isdigit()]
        if len(numbers) == 4:
            bboxes.append(numbers)
        elif len(numbers) == 8:
            polygon = [[numbers[0], numbers[1]], [numbers[2], numbers[3]],
                       [numbers[4], numbers[5]], [numbers[6], numbers[7]]]
            bboxes.append(polygon)

    return bboxes


def fix_bboxes_format(input_json_path, output_json_path, leave_only_filename=False):
    # Load original data
    with open(input_json_path, "r") as f:
        data = json.load(f)

    base_url = "https://michaelalr.github.io/thesis/"
    fixed_data = []
    for image_path, items_list in data.items():
        if leave_only_filename:
            full_image_path = os.path.basename(image_path)
        else:
            relative_path = image_path.lstrip("../")  # remove "../" from the beginning
            full_image_path = urljoin(base_url, relative_path)
        for item_data in items_list:
            item_name = item_data.get("item", "")
            bbox_str = item_data.get("bbox", "")
            cleaned_bbox = clean_bbox_string_extended(bbox_str)

            polygon = []
            try:
                if isinstance(cleaned_bbox, list) and len(cleaned_bbox) > 0:
                    # Case: [[x_min, y_min, x_max, y_max]]
                    if len(cleaned_bbox) == 1 and len(cleaned_bbox[0]) == 4:
                        polygon = convert_bbox_to_points(cleaned_bbox[0])

                    # Case: [x_min, y_min, x_max, y_max]
                    elif len(cleaned_bbox) == 4 and all(isinstance(v, (int, float)) for v in cleaned_bbox):
                        polygon = convert_bbox_to_points(cleaned_bbox)

                    # Case: 4 corner points like [[x,y], [x,y], [x,y], [x,y]]
                    elif all(isinstance(pt, list) and len(pt) == 2 for pt in cleaned_bbox) and len(cleaned_bbox) == 4:
                        polygon = cleaned_bbox

                    # Case: list of bboxes (e.g., multiple candidates), choose the first valid one
                    elif all(isinstance(b, list) and len(b) == 4 for b in cleaned_bbox):
                        polygon = convert_bbox_to_points(cleaned_bbox[0])

            except Exception as e:
                print(f"Failed to parse bbox for {image_path}, error: {e}")


            fixed_data.append({
                "image_path": full_image_path,
                "chosen_item": item_name,
                "chosen_polygon": json.dumps(polygon)
            })

    # Save cleaned version
    with open(output_json_path, "w") as f:
        json.dump(fixed_data, f, indent=2)

    print(f"Finished cleaning. Saved to {output_json_path}")


if __name__ == '__main__':
    leave_only_filename = True
    input_json_path = "qwen_2.5_test_origin_images.json"
    output_json_path = "qwen_2.5_test_origin_images_parse.json"
    fix_bboxes_format(input_json_path=input_json_path, output_json_path=output_json_path,
                      leave_only_filename=leave_only_filename)

    # example = "[[2, 153, 111, 247], [125, 155, 228, 243], [75, 52, 120, 130], [14, 53, 72, 123], [123, 160, 134, 221]]"
    # example = "[[194,309,1025,755]]"
    # example = "[]"
    # example = "json\n[\n\t{\"bbox_2d\": [724, 354, 833, 440], \"label\": \"Bowl\"}\n]\n"\
    # example = "[317,341,473,486]"
    # example = "[[132,48,155,80],[155,48,177,81],[176,48,199,83],[189,47,197,81]]"
    # example = "[349, 33, 510, 463, 686, 452, 885, 1091]"
    # example = "json\n[]\n"
    # example = "[\n    [299,107,533,479]\n]"
    # example = "json\n[[185, 43, 251, 117]]\n"
    # example = "json\n[\n[303, 0, 907, 572],\n[913, 105, 1436, 345],\n[918, 330, 1406, 572],\n[2, 947, 608, 1133]\n]\n"
    # clean_example = clean_bbox_string_extended(example)
