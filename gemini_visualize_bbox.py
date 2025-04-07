import json
import os
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse # To help extract filename from URL
import sys # To exit gracefully

# --- Configuration ---

# 1. Input JSON file (output from the UPDATED process_images.py script)
JSON_INPUT_PATH = "train_data_with_gemini_bboxes_as_strings.json"

# 2. Base directory for local images
LOCAL_IMAGE_BASE_DIR = "./images"

# 3. Drawing settings
RECTANGLE_OUTLINE_COLOR = "red" # For the simple list string "[x,y,x,y]"
POLYGON_OUTLINE_COLOR = "lime" # For the polygon list string "[[x,y],...]"
BOX_WIDTH = 3
LABEL_TEXT_COLOR = "white"
LABEL_BACKGROUND_COLOR = "black"
try:
    LABEL_FONT = ImageFont.truetype("arial.ttf", 18)
except IOError:
    print("Arial font not found, using PIL default font.")
    LABEL_FONT = ImageFont.load_default()

# --- Main Logic ---

def main():
    # 1. Load the JSON data
    try:
        with open(JSON_INPUT_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {len(data)} entries from {JSON_INPUT_PATH}")
    except FileNotFoundError:
        print(f"Error: Input JSON file not found at {JSON_INPUT_PATH}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {JSON_INPUT_PATH}")
        return
    except Exception as e:
        print(f"An unexpected error occurred loading JSON: {e}")
        return

    if not data:
        print("JSON data is empty. Nothing to visualize.")
        return

    total_entries = len(data)
    print(f"\nStarting visualization for {total_entries} entries...")
    print("An image window will open for each entry.")
    print("**** Close each image window to proceed to the next one. ****")

    # 2. Loop through all entries
    for i, entry in enumerate(data):
        print(f"\n--- Processing Entry {i+1}/{total_entries} ---")

        # 3. Construct the local image path
        image_url = entry.get("image_path")
        room_type = entry.get("room_type", "unknown_room")
        chosen_item = entry.get("chosen_item", "Unknown Item")

        if not image_url:
            print("  Skipping: 'image_path' not found.")
            continue

        try:
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                 raise ValueError("Could not extract filename")
            local_image_path = os.path.join(LOCAL_IMAGE_BASE_DIR, room_type, filename)
            print(f"  Image Path: {local_image_path}")
            print(f"  Item: {chosen_item}")
        except Exception as e:
            print(f"  Skipping: Error constructing local image path from URL '{image_url}': {e}")
            continue

        # 4. Load the local image
        try:
            img = Image.open(local_image_path)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            draw = ImageDraw.Draw(img)
            print(f"  Loaded image (Size: {img.size})")
        except FileNotFoundError:
            print(f"  Skipping: Local image file not found at '{local_image_path}'")
            continue
        except Exception as e:
            print(f"  Skipping: Error opening image file '{local_image_path}': {e}")
            continue

        # Flag to track if we drew anything
        drew_something = False

        # 5. Parse and Draw Rectangle (from STRING)
        bbox_list_string = entry.get("gemini_bbox_list_string")
        if bbox_list_string and isinstance(bbox_list_string, str):
            try:
                # Parse the string back into a list
                bbox_list = json.loads(bbox_list_string)
                if isinstance(bbox_list, list) and len(bbox_list) == 4 and bbox_list != [0, 0, 0, 0]:
                    xmin, ymin, xmax, ymax = bbox_list
                    if xmax >= xmin and ymax >= ymin: # Basic validity check
                         draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=RECTANGLE_OUTLINE_COLOR, width=BOX_WIDTH)
                         print(f"  Drew RECTANGLE (Red) from string: {bbox_list_string}")
                         drew_something = True
                    else:
                         print(f"  Skipping rectangle drawing: Invalid coords in parsed list {bbox_list}")
                else:
                    print("  Skipping rectangle drawing: Parsed list invalid or default.")
            except json.JSONDecodeError:
                 print(f"  Skipping rectangle drawing: Could not decode list string: '{bbox_list_string}'")
            except Exception as e:
                 print(f"  Error processing/drawing rectangle from list string {bbox_list_string}: {e}")
        else:
             print("  Skipping rectangle drawing: 'gemini_bbox_list_string' missing or not a string.")


        # 6. Parse and Draw Polygon (from STRING)
        polygon_string = entry.get("gemini_bbox_polygon_string")
        if polygon_string and isinstance(polygon_string, str):
            try:
                # Parse the string back into a list of lists
                polygon_points = json.loads(polygon_string)
                if polygon_points and isinstance(polygon_points, list) and polygon_points != [[0, 0], [0, 0], [0, 0], [0, 0]]:
                     # Check if elements are lists of size 2 (basic check)
                     if all(isinstance(p, list) and len(p) == 2 for p in polygon_points):
                          polygon_tuples = [tuple(point) for point in polygon_points]
                          draw.polygon(polygon_tuples, outline=POLYGON_OUTLINE_COLOR, width=BOX_WIDTH)
                          print(f"  Drew POLYGON (Lime) from string: {polygon_string}")
                          drew_something = True
                     else:
                          print(f"  Skipping polygon drawing: Parsed data not list of points: {polygon_points}")
                else:
                     print("  Skipping polygon drawing: Parsed default/empty polygon.")
            except json.JSONDecodeError:
                print(f"  Skipping polygon drawing: Could not decode polygon string: '{polygon_string}'")
            except Exception as e:
                print(f"  Error processing/drawing polygon from string '{polygon_string}': {e}")
        else:
             print("  Skipping polygon drawing: 'gemini_bbox_polygon_string' missing or not a string.")


        # 7. Add Label (Only if we drew something)
        if drew_something:
             label = f"Item: {chosen_item}"
             try:
                  text_box = draw.textbbox((0,0), label, font=LABEL_FONT)
                  text_width = text_box[2] - text_box[0]
                  text_height = text_box[3] - text_box[1]
                  label_x = 10
                  label_y = 10
                  draw.rectangle([(label_x, label_y), (label_x + text_width + 4, label_y + text_height + 4)], fill=LABEL_BACKGROUND_COLOR)
                  draw.text((label_x + 2, label_y + 2), label, fill=LABEL_TEXT_COLOR, font=LABEL_FONT)
                  print(f"  Added label: '{label}'")
             except Exception as e:
                  print(f"  Could not draw label: {e}")


        # 8. Display the image (blocks until closed)
        try:
            print(f"  Displaying image {i+1}/{total_entries}... CLOSE THE IMAGE WINDOW TO CONTINUE.")
            img.show()
        except Exception as e:
            print(f"  Error displaying image: {e}")
            cont = input("Could not display image. Continue to next (y/n)? ").lower()
            if cont != 'y':
                print("Exiting.")
                sys.exit()

    print("\nFinished visualizing all entries.")

if __name__ == "__main__":
    main()