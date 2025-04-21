import json
import os

import matplotlib.pyplot as plt

import numpy as np
from PIL import Image
from matplotlib.patches import Polygon
from shapely.geometry import Polygon
import matplotlib.patches as patches


def create_counter_lines(data):
    """
    Processes a list of kitchen data to identify and filter counter polygons,
    adding a 'counter_line_polygon' field to each entry. Handles small polygons
    by averaging, ensures integer coordinates in output, avoids extra list nesting,
    and filters out invalid polygons with fewer than 3 unique vertices.

    Args:
        data (list): A list of dictionaries, where each dictionary contains
                     image information and 'containers_mask_polygon' (a string
                     representation of a list of counter polygons).

    Returns:
        list: The input list of dictionaries with an added
              'counter_line_polygon' field (a string representation of a list
              of lists of integer coordinate pairs).
    """
    processed_data = []
    for item in data:
        image_path = item['image_path_html']
        counter_polygons_str = item['containers_mask_polygon']
        counter_polygons_list = json.loads(counter_polygons_str)
        valid_counters_coords = []
        shapely_polygons = []

        if counter_polygons_list:
            for poly_coords_container in counter_polygons_list:
                raw_coords = None
                if isinstance(poly_coords_container, list) and all(isinstance(coord, list) and len(coord) == 2 and all(
                        isinstance(val, (int, float)) for val in coord) for coord in poly_coords_container):
                    raw_coords = poly_coords_container
                elif isinstance(poly_coords_container, list) and len(poly_coords_container) > 0 and isinstance(
                        poly_coords_container[0], list) and all(isinstance(coord, list) and len(coord) == 2 and all(
                    isinstance(val, (int, float)) for val in coord) for coord in poly_coords_container[0]):
                    raw_coords = poly_coords_container[0]

                if raw_coords and len(
                        set(tuple(coord) for coord in raw_coords)) >= 3:  # Check for at least 3 unique vertices
                    try:
                        polygon = Polygon(raw_coords)
                        shapely_polygons.append(polygon)
                    except Exception as e:
                        print(f"Error creating polygon for image {image_path}: {e}")
                        print(f"Problematic polygon data: {raw_coords}")
                elif raw_coords:
                    print(
                        f"Warning: Skipping invalid polygon with fewer than 3 unique vertices in {image_path}: {raw_coords}")
                else:
                    print(f"Warning: Skipping malformed polygon data in image {image_path}: {poly_coords_container}")

            if not shapely_polygons:
                item['counter_line_polygon'] = json.dumps([])
                processed_data.append(item)
                continue

            if len(shapely_polygons) == 1:
                coords_int = [[int(c) for c in coord] for coord in list(shapely_polygons[0].exterior.coords)]
                valid_counters_coords.append(coords_int)
            else:
                # --- Filtering Logic ---
                min_counter_area_threshold = 5000  # Adjust as needed
                large_area_candidates = [
                    poly for poly in shapely_polygons if poly.area > min_counter_area_threshold
                ]

                if large_area_candidates:
                    def get_aspect_ratio(polygon):
                        min_x, min_y, max_x, max_y = polygon.bounds
                        width = max_x - min_x
                        height = max_y - min_y
                        if height > 0:
                            return width / height
                        return 0

                    min_aspect_ratio_threshold = 1.5  # Adjust as needed
                    wide_candidates = [
                        poly for poly in large_area_candidates
                        if get_aspect_ratio(poly) >= min_aspect_ratio_threshold
                    ]

                    if wide_candidates:
                        if len(wide_candidates) == 1:
                            coords_int = [[int(c) for c in coord] for coord in list(wide_candidates[0].exterior.coords)]
                            valid_counters_coords.append(coords_int)
                        elif len(wide_candidates) > 1:
                            largest_wide = max(wide_candidates, key=lambda p: p.area)
                            coords_int = [[int(c) for c in coord] for coord in list(largest_wide.exterior.coords)]
                            valid_counters_coords.append(coords_int)
                    elif len(large_area_candidates) > 0:
                        largest_area = max(large_area_candidates, key=lambda p: p.area)
                        coords_int = [[int(c) for c in coord] for coord in list(largest_area.exterior.coords)]
                        valid_counters_coords.append(coords_int)
                else:
                    # Handle case where all counter polygons are too small
                    if shapely_polygons:
                        all_min_y = [poly.bounds[1] for poly in shapely_polygons]
                        all_max_y = [poly.bounds[3] for poly in shapely_polygons]
                        avg_min_y = np.mean(all_min_y)
                        avg_max_y = np.mean(all_max_y)

                        min_x_overall = min(
                            min(point[0] for point in poly.exterior.coords) for poly in shapely_polygons)
                        max_x_overall = max(
                            max(point[0] for point in poly.exterior.coords) for poly in shapely_polygons)

                        representative_counter = [
                            [int(min_x_overall), int(avg_min_y)],
                            [int(max_x_overall), int(avg_min_y)],
                            [int(max_x_overall), int(avg_max_y)],
                            [int(min_x_overall), int(avg_max_y)]
                        ]
                        valid_counters_coords.append(representative_counter)

        item['counter_line_polygon'] = json.dumps(valid_counters_coords)
        processed_data.append(item)

    return processed_data


def plot_counter_on_image(json_file, image_dir):
    """
    Reads a JSON file with image paths and counter polygons, loads each image,
    plots the counter polygon on it, and displays the result. Pauses for user
    input before moving to the next image.

    Args:
        json_file (str): Path to the JSON file containing image paths and
                         'counter_line_polygon' data.
        image_dir (str, optional): Directory containing the kitchen images.
                                     Defaults to "images/kitchen/".
    """
    with open(json_file, 'r') as f:
        data = json.load(f)

    for item in data:
        image_path_html = item['image_path_html']
        counter_polygon_str = item.get('counter_line_polygon')

        if counter_polygon_str:
            counter_polygons = json.loads(counter_polygon_str)

            # Extract the base image filename
            base_filename = os.path.basename(image_path_html)
            parts = base_filename.split('_sun_')
            if len(parts) == 2:
                target_suffix = "_sun_" + parts[1]
                image_filename = None
                for filename in os.listdir(image_dir):
                    if target_suffix in filename:
                        image_filename = filename
                        break

                if image_filename:
                    full_image_path = os.path.join(image_dir, image_filename)
                    try:
                        img = Image.open(full_image_path)
                        fig, ax = plt.subplots(1)
                        ax.imshow(img)

                        for polygon_coords_list in counter_polygons:
                            if polygon_coords_list:
                                polygon = [(x, y) for x, y in polygon_coords_list]
                                patch = patches.Polygon(polygon, closed=True, edgecolor='red', fill=False, linewidth=2)
                                ax.add_patch(patch)

                        ax.set_title(f"Image: {os.path.basename(image_filename)}")
                        plt.show(block=False)
                        input("Press Enter to continue to the next image...")
                        plt.close(fig)

                    except FileNotFoundError:
                        print(f"Error: Image not found at {full_image_path}")
                    except Exception as e:
                        print(f"Error plotting image {image_filename}: {e}")
                else:
                    print(f"Warning: Corresponding image not found for {base_filename}")
            else:
                print(f"Warning: Could not parse base filename from {base_filename}")
        else:
            print(f"Warning: 'counter_line_polygon' field not found for {image_path_html}")


def main_choose_counter(output_json_file):
    input_json_file = "../image_details/image_details_counter.json"  # Replace with your file path

    with open(input_json_file, 'r') as f:
        counter_data = json.load(f)

    processed_counter_data = create_counter_lines(counter_data)

    with open(output_json_file, 'w') as f:
        json.dump(processed_counter_data, f, indent=4)

    print(f"Processed counter lines saved to {output_json_file}")


def main_plot_counter(output_json_file):
    image_directory = "../images/kitchen/"  # Ensure this is the correct path to your images

    plot_counter_on_image(output_json_file, image_directory)

    print("Finished processing all images.")


if __name__ == "__main__":
    output_json_file = "../image_details/image_details_choose_counter.json"
    # main_choose_counter(output_json_file=output_json_file)
    main_plot_counter(output_json_file=output_json_file)
