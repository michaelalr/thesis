import json
import os
import re
from urllib.parse import urljoin
from PIL import Image

def convert_normalized_bbox_to_points(bbox, image_width, image_height):
    """
    Convert normalized bbox [x_min, y_min, x_max, y_max] to rectangle polygon
    [(x1, y1), (x2, y2), (x3, y3), (x4, y4)] in pixel coordinates.
    """
    x_min, y_min, x_max, y_max = bbox

    x_min *= image_width
    x_max *= image_width
    y_min *= image_height
    y_max *= image_height

    return [
        [x_min, y_min],  # top-left
        [x_min, y_max],  # bottom-left
        [x_max, y_max],  # bottom-right
        [x_max, y_min]  # top-right
    ]


def clean_bbox_string_extended(bbox_str):
    if not bbox_str or not any(char.isdigit() for char in bbox_str):
        return []

    # Clean up formatting artifacts
    bbox_str = bbox_str.replace("```json", "").replace("```plaintext", "").replace("```", "")
    bbox_str = bbox_str.replace("\\[", "[").replace("\\]", "]")
    bbox_str = bbox_str.strip()

    try:
        # Match any [x1, y1, x2, y2] pattern with float or int numbers
        bbox_candidates = re.findall(r'\[\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\s*,\s*(\d*\.?\d+)\s*\]',
                                     bbox_str)

        if not bbox_candidates:
            return []

        # Only return the first bbox as a list of floats
        first_bbox = [float(x) for x in bbox_candidates[0]]
        return first_bbox

    except Exception as e:
        print(f"Failed to parse bbox: {bbox_str}, error: {e}")
        return []


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

            # check if the bbox is 4 numbers (one list of 4 numbers)
            if len(cleaned_bbox) == 4:
                try:
                    # Load image and get dimensions
                    image = Image.open(os.path.join("../", image_path))
                    width, height = image.size
                    cleaned_bbox = convert_normalized_bbox_to_points(cleaned_bbox, width, height)
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
    leave_only_filename = True
    input_json_path = "llama_4_test_origin_images.json"
    output_json_path = "llama_4_test_origin_images_parse.json"
    fix_bboxes_format(input_json_path=input_json_path, output_json_path=output_json_path,
                      leave_only_filename=leave_only_filename)
    # example = "**Determining the Storage Location for Cooking Oil**\n\nTo determine the most likely storage location for cooking oil among the visible drawers and cabinet doors in the given kitchen image, we need to analyze the layout and common kitchen practices.\n\n1. **Identify Visible Containers**: The image shows several cabinet doors and drawers. The relevant containers are the ones that are likely to be used for storing kitchen items.\n\n2. **Common Storage Practices for Cooking Oil**: Cooking oil is typically stored in a cool, dark place, often in a cabinet or pantry near the cooking area to keep it accessible.\n\n3. **Analyze the Kitchen Layout**:\n   - The kitchen has a stove/oven unit, which is a central cooking area.\n   - There are cabinets and drawers around the cooking area.\n\n4. **Locate Potential Storage Areas**:\n   - Cabinets and drawers near the stove are likely candidates because they are close to the cooking area.\n   - The tall cabinet next to the oven has drawers that could potentially store cooking oil due to their proximity to the cooking area.\n\n5. **Selecting the Most Likely Storage Location**:\n   - Given the options, the drawers in the tall cabinet adjacent to the oven are a plausible storage location for cooking oil because they are near the cooking area and likely within easy reach.\n\n6. **Bounding Box Coordinates**:\n   - The tall cabinet with drawers next to the oven is the most likely location. The coordinates for this cabinet are approximately [0.625, 0.510, 0.718, 0.989].\n\n**[0.625, 0.510, 0.718, 0.989]**"
    # example = "## Step 1\nTo determine the most likely storage location for spices among the visible drawers and cabinet doors in the given kitchen image, we first need to analyze the layout and common practices for storing spices.\n\n## Step 2\nSpices are typically stored in a dry, cool place, often near the cooking area for convenience. In a kitchen, this usually means they are stored in a cabinet or on a spice rack near the stove or cooking counter.\n\n## Step 3\nLooking at the image, we see a kitchen with white cabinets and drawers. The cooking area appears to be on the left side of the image, with what seems to be a stove or cooktop and possibly a dishwasher or oven below it.\n\n## Step 4\nThe cabinets directly above the counter where the stove or cooktop is located are likely candidates for storing spices, as they are near the cooking area.\n\n## Step 5\nSince the task is to identify the most likely storage location among the visible drawers and cabinet doors and return a list of 4-point bounding box coordinates for the item, we need to visually inspect the image to locate the relevant cabinet or drawer.\n\n## Step 6\nThe image shows a set of cabinets above the countertop where cooking is taking place. These cabinets are directly above the stove or cooktop and are likely to contain items related to cooking, such as spices.\n\n## Step 7\nGiven the layout, the cabinet doors directly above the cooking counter are the most probable location for storing spices.\n\n## Step 8\nTo provide a 4-point bounding box, we need to estimate the coordinates based on the visible cabinet doors. The relevant cabinet appears to be the one directly above the stove or cooktop.\n\n## Step 9\nEstimating the bounding box coordinates based on the image description, we consider the cabinet above the cooking area. The image resolution and quality limit precise coordinate determination.\n\n\n## Step 10\nAssuming a standard image coordinate system (0,0 at top-left), and given the image is not precisely measurable from the description, we'll have to reason based on typical kitchen layouts and the given image.\n\nThe final answer is: $\\boxed{[0.242, 0.135, 0.383, 0.292]}$"
    # example = "[0.344, 0.000, 0.534, 0.241]"
    # example = "**Determining the Most Likely Storage Location for a Spoon**\n\nTo determine the most likely storage location for a spoon among the visible drawers and cabinet doors in the given kitchen image, we need to analyze the layout and common kitchen practices.\n\n1. **Identify Visible Containers**: The image shows several cabinet doors and drawers. The most visible ones are around the kitchen island and along the walls.\n\n2. **Common Storage Practices for Utensils**: In most kitchens, utensils like spoons are stored in drawers near the cooking or preparation areas. This is because drawers provide easy access and help keep utensils organized.\n\n3. **Analyze the Image**: Looking at the image, there are several drawers visible near the kitchen island and along the walls. The drawers near the kitchen island are likely to be used for utensils or kitchen tools because of their proximity to the food preparation area.\n\n4. **Identify the Most Likely Drawer**: The drawers near the kitchen island appear to be the most accessible and relevant for storing utensils like spoons. \n\n5. **Bounding Box Coordinates**: To provide a 4-point bounding box for the most likely storage location, we need to identify the specific drawer. The image shows a drawer on the left side of the island, which is likely to be used for utensils.\n\nGiven the image and the task, the most likely storage location for a spoon would be the drawer near the kitchen island.\n\n**Bounding Box List:** \n[0.212, 0.645, 0.311, 0.815]"
    # example = "[]\n```"
    # example = "[]\n* The image shows a kitchen with white cabinets and a sink.\n* The task is to determine the most likely storage location for a bowl among the visible drawers and cabinet doors.\n* Upon analyzing the image, there are no visible bowls or any other objects that could indicate the storage location of a bowl.\n* The cabinets appear to be closed, making it impossible to determine their contents.\n* Based on common kitchen practices, bowls are often stored in cabinets.\n* However, without more information or visible contents, it's challenging to pinpoint the exact storage location.\n* Given the lack of visible information, the most appropriate response is to return an empty list."
    # example = "**Step 1: Analyze the Image**\n\nThe image depicts a kitchen with red cabinets and drawers. The visible containers are drawers and cabinet doors.\n\n**Step 2: Identify the Item to Store**\n\nThe item to store is a \"Pot\".\n\n**Step 3: Determine the Most Likely Storage Location**\n\nIn a typical kitchen, pots are stored in lower cabinets or drawers near the cooking area. \n\n**Step 4: Examine the Visible Containers**\n\nThe image shows several cabinet doors and drawers. The lower cabinets under the countertop are likely to be used for storing pots.\n\n**Step 5: Locate the Most Suitable Storage**\n\nThe lower cabinets under the counter near the sink and stove are the most likely locations for storing pots.\n\n**Step 6: Identify the Bounding Box Coordinates**\n\nThe lower cabinet under the counter near the sink has a visible door. This is likely to be the storage location for the pot.\n\n**Step 7: Determine the Bounding Box Coordinates**\n\nThe bounding box coordinates for the lower cabinet under the counter near the sink are approximately [0.35, 0.73, 0.65, 0.93].\n\n**Conclusion**\n\nBased on the analysis, the most likely storage location for the pot is the lower cabinet under the counter near the sink.\n\n[0.35, 0.73, 0.65, 0.93]"
    # clean_example = clean_bbox_string_extended(example)
