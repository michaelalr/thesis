import ast
import json
import os

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from shapely.geometry import Polygon, LineString, Point


def classify_containers(image_details_json, image_details_with_labels_json, csv_filename):
    # Load JSON files
    with open(image_details_json) as f1:
        json1 = json.load(f1)

    with open(image_details_with_labels_json) as f2:
        json2 = json.load(f2)

    # Index both by image_path_html
    dict1 = {entry["image_path_html"]: entry for entry in json1}
    dict2 = {entry["image_path_html"]: entry for entry in json2}

    common_keys = set(dict1.keys()) & set(dict2.keys())
    only_in_1 = set(dict1.keys()) - set(dict2.keys())
    only_in_2 = set(dict2.keys()) - set(dict1.keys())

    mismatched_polygons = []
    rows = []

    for key in common_keys:
        poly1_str = dict1[key]["containers_mask_polygon"]
        poly2_str = dict2[key]["containers_mask_polygon"]

        try:
            poly1 = ast.literal_eval(poly1_str)
            poly2 = ast.literal_eval(poly2_str)
        except Exception as e:
            print(f"Error parsing polygon for {key}: {e}")
            continue

        if poly1 != poly2:
            mismatched_polygons.append(key)
            continue

        # If matching, extract labeled polygons
        labeled_str = dict2[key].get("containers_mask_polygon_with_labels", "[]")
        try:
            labeled = ast.literal_eval(labeled_str)
            for label, polygon in labeled:
                rows.append({
                    "image_path_html": key,
                    "polygon": polygon,
                    "label": label
                })
        except Exception as e:
            print(f"Error parsing labeled polygons for {key}: {e}")

    # Create the dataframe
    df = pd.DataFrame(rows)

    # Save report
    df.to_csv(csv_filename, index=False)

    # Save mismatched and unmatched files
    # with open("mismatched_polygons.txt", "w") as f:
    #     for item in mismatched_polygons:
    #         f.write(f"{item}\n")
    #
    # with open("only_in_json1.txt", "w") as f:
    #     for item in sorted(only_in_1):
    #         f.write(f"{item}\n")
    #
    # with open("only_in_json2.txt", "w") as f:
    #     for item in sorted(only_in_2):
    #         f.write(f"{item}\n")

    print(f"✅ Done. Total entries: {len(df)}")
    print(
        f"🔍 Mismatched: {len(mismatched_polygons)} | Only in JSON1: {len(only_in_1)} | Only in JSON2: {len(only_in_2)}")

    return df


def get_image_id(image_path_html):
    """Extracts the unique part of the filename after 'segmented_'."""
    filename = os.path.basename(image_path_html)
    return filename.split("segmented_")[-1]


def get_diff_between_jsons_image_path(countertop_data, details_data):
    # Get sets of image IDs from both datasets
    countertop_ids = set(get_image_id(entry["image_path_html"]) for entry in countertop_data)
    details_ids = set(get_image_id(entry["image_path_html"]) for entry in details_data)

    # Find differences
    in_countertop_not_in_details = countertop_ids - details_ids
    in_details_not_in_countertop = details_ids - countertop_ids

    print("Images in countertop_data but not in details_data:")
    for img_id in sorted(in_countertop_not_in_details):
        print(img_id)

    print("\nImages in details_data but not in countertop_data:")
    for img_id in sorted(in_details_not_in_countertop):
        print(img_id)

    print(f"\nSummary:")
    print(f"- Countertop entries: {len(countertop_ids)}")
    print(f"- Details entries: {len(details_ids)}")
    print(f"- Unmatched in countertop: {len(in_countertop_not_in_details)}")
    print(f"- Unmatched in details: {len(in_details_not_in_countertop)}")


def add_image_path_html_match(image_details_countertop, image_details_json_path, output_path=None):
    # Load the data
    with open(image_details_countertop, 'r') as f:
        countertop_data = json.load(f)
    with open(image_details_json_path, 'r') as f:
        details_data = json.load(f)

    # get_diff_between_jsons_image_path(countertop_data=countertop_data, details_data=details_data)

    if not isinstance(countertop_data, list):
        countertop_data = [countertop_data]
    if not isinstance(details_data, list):
        details_data = [details_data]

    # Build a mapping from unique name to full path in image_details_json
    details_map = {}
    for entry in details_data:
        filename = os.path.basename(entry["image_path_html"])
        key = filename.split("segmented_")[-1]
        details_map[key] = entry["image_path_html"]

    # Match and add image_path_html_match
    for entry in countertop_data:
        filename = os.path.basename(entry["image_path_html"])
        key = filename.split("segmented_")[-1]
        matched_path = details_map.get(key, json.dumps([]))
        entry["image_path_html_match"] = matched_path

    # Save the updated countertop data
    output_path = output_path or image_details_countertop
    with open(output_path, 'w') as f:
        json.dump(countertop_data, f, indent=4)

    print(f"Updated countertop JSON saved to: {output_path}")
    return countertop_data


def plot_min_y_polygons(data, max_images=30):
    plotted = 0

    for entry in data:
        image_path_match = entry.get("image_path_html_match")
        min_y_polygon_str = entry.get("min_y_polygon")

        if not image_path_match or not min_y_polygon_str:
            continue

        try:
            min_y_polygon = json.loads(min_y_polygon_str)
            if not min_y_polygon:
                continue
        except json.JSONDecodeError:
            continue

        image_path = os.path.normpath(os.path.join("..", image_path_match))
        try:
            img = Image.open(image_path)
        except Exception as e:
            print(f"Could not open image {image_path}: {e}")
            continue

        # Plot image
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(img)

        # Draw min_y polygon
        polygon = patches.Polygon(min_y_polygon, closed=True, edgecolor='red', facecolor='red', alpha=0.3)
        ax.add_patch(polygon)
        ax.set_title(f"Image: {image_path_match}", fontsize=10)
        plt.axis("off")
        plt.show()

        plotted += 1
        if plotted >= max_images:
            break


def add_countertop_min_y_fields(json_path, output_path=None):
    # Load JSON data
    with open(json_path, 'r') as f:
        data = json.load(f)

    if not isinstance(data, list):
        data = [data]

    for entry in data:
        # Parse polygon list
        polygons = ast.literal_eval(entry["containers_mask_polygon"])
        min_y = min(point[1] for polygon in polygons for point in polygon)
        entry["min_y"] = json.dumps(min_y)

        # Handle image dimension safely
        image_path_match = entry.get("image_path_html_match")
        if image_path_match == json.dumps([]):
            print(f"Missing or None image_path_html_match for entry: {entry['image_path_html']}")
            entry["min_y_polygon"] = json.dumps([])
            entry["min_y_polygon"] = json.dumps([])
            continue

        # Get image dimensions
        image_path = os.path.normpath(os.path.join("..", image_path_match))
        try:
            with Image.open(image_path) as img:
                image_width, image_height = img.size
        except Exception as e:
            print(f"Warning: Could not open {image_path}: {e}")
            entry["min_y_polygon"] = json.dumps([])
            continue

        # Create rectangle from min_y to image bottom
        min_y_polygon = [
            [0, min_y],
            [image_width, min_y],
            [image_width, image_height],
            [0, image_height]
        ]
        entry["min_y_polygon"] = json.dumps(min_y_polygon)

    # Save updated data
    output_path = output_path or json_path
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Updated JSON saved to: {output_path}")

    # plot_min_y_polygons(data)

    return data


def to_geometry(coords):
    if len(coords) == 1:
        return Point(coords[0])
    elif len(coords) == 2:
        return LineString(coords)
    else:
        return Polygon(coords)


def add_above_or_below_countertop(csv_path, countertop_json_path, output_csv_path):
    # Load countertop JSON
    with open(countertop_json_path, 'r') as f:
        countertop_data = json.load(f)

    # Create a mapping from image_path_html to min_y_polygon
    image_to_countertop = {
        entry["image_path_html_match"]: ast.literal_eval(entry["min_y_polygon"])
        for entry in countertop_data
        if
        entry.get("image_path_html_match") and entry.get("min_y_polygon") and entry["min_y_polygon"] != json.dumps([])
    }

    # Load labeled containers CSV
    df = pd.read_csv(csv_path)

    # Initialize the new column
    df["countertop_polygon"] = ""
    df["above_or_below_countertop"] = ""

    # Group by image_path_html
    for image_path_html, group in df.groupby("image_path_html"):
        if image_path_html not in image_to_countertop:
            continue  # Skip if no countertop info

        try:
            countertop_geom = to_geometry(image_to_countertop[image_path_html])
        except Exception as e:
            print(f"Error parsing countertop polygon for {image_path_html}: {e}")
            continue

        # Go over each container row
        for idx, row in group.iterrows():
            try:
                coords = ast.literal_eval(row["polygon"])  # should be a single polygon
                container_geom = to_geometry(coords)

                intersects = container_geom.intersects(countertop_geom)
                df.at[idx, "above_or_below_countertop"] = "below" if intersects else "above"
                df.at[idx, "countertop_polygon"] = json.dumps(image_to_countertop[image_path_html])
            except Exception as e:
                print(f"Error processing container in {image_path_html}: {e}")
                continue

    # Save to CSV
    df.to_csv(output_csv_path, index=False)
    print(f"Updated CSV with 'above_or_below_countertop' saved to: {output_csv_path}")

    return df

def plot_above_below_polygons(csv_path, image_base_dir, num_images=30):
    df = pd.read_csv(csv_path)
    shown_images = 0

    # Color map: (label, position) → color
    color_map = {
        ("drawer", "above"): "blue",
        ("drawer", "below"): "cyan",
        ("drawer door", "above"): "blue",
        ("drawer door", "below"): "cyan",
        ("cabinet door", "above"): "pink",
        ("cabinet door", "below"): "magenta",
        ("drawer cabinet", "above"): "green",
        ("drawer cabinet", "below"): "green",
        ("drawer cabinet door", "above"): "yellow",
        ("drawer cabinet door", "below"): "yellow",
    }

    for image_path_html in df["image_path_html"].unique():
        if shown_images >= num_images:
            break

        full_image_path = os.path.normpath(os.path.join(image_base_dir, image_path_html))
        if not os.path.exists(full_image_path):
            print(f"Image not found: {full_image_path}")
            continue

        try:
            img = Image.open(full_image_path)
        except Exception as e:
            print(f"Failed to open image: {full_image_path} – {e}")
            continue

        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(img)
        ax.set_title(f"{image_path_html}")

        # Plot all containers for this image
        containers = df[df["image_path_html"] == image_path_html]

        # Plot countertop polygon once (if available)
        if "countertop_polygon" in containers.columns:
            countertop_str = containers["countertop_polygon"].iloc[0]
            if countertop_str and countertop_str != "[]":
                try:
                    countertop_coords = ast.literal_eval(countertop_str)
                    if len(countertop_coords) == 1:
                        ax.plot(countertop_coords[0][0], countertop_coords[0][1], "o", color="red")
                    elif len(countertop_coords) == 2:
                        xs, ys = zip(*countertop_coords)
                        ax.plot(xs, ys, "-", color="red")
                    else:
                        polygon = patches.Polygon(countertop_coords, closed=True, fill=True,
                                                  edgecolor='black', facecolor="red", alpha=0.5)
                        ax.add_patch(polygon)
                except Exception as e:
                    print(f"Failed to draw countertop for {image_path_html}: {e}")

        for _, row in containers.iterrows():
            try:
                coords = ast.literal_eval(row["polygon"])
                label = row["label"]
                position = row["above_or_below_countertop"]
                color = color_map.get((label, position), "gray")

                if len(coords) == 1:  # Single point
                    ax.plot(coords[0][0], coords[0][1], "o", color=color)
                elif len(coords) == 2:  # Line
                    xs, ys = zip(*coords)
                    ax.plot(xs, ys, "-", color=color)
                else:  # Polygon
                    polygon = patches.Polygon(coords, closed=True, fill=True, edgecolor='black', facecolor=color, alpha=0.8)
                    ax.add_patch(polygon)

            except Exception as e:
                print(f"Error drawing polygon for {image_path_html}: {e}")
                continue

        plt.axis('off')
        plt.tight_layout()
        plt.show()
        shown_images += 1

if __name__ == '__main__':
    image_details_json_path = "../image_details/image_details.json"
    image_details_with_labels = "../image_details/image_details_with_labels.json"
    csv_filename = "../labeled_containers.csv"

    # df = classify_containers(image_details_json=image_details_json_path,
    #                          image_details_with_labels_json=image_details_with_labels,
    #                          csv_filename=csv_filename)

    image_details_countertop = "../image_details/image_details_countertop.json"
    image_details_countertop_output = "../image_details/image_details_countertop_output.json"
    # countertop_data = add_image_path_html_match(image_details_countertop=image_details_countertop,
    #                                             image_details_json_path=image_details_json_path,
    #                                             output_path=image_details_countertop_output)

    # data = add_countertop_min_y_fields(json_path=image_details_countertop_output)

    csv_with_countertop = "../labeled_containers_with_countertop.csv"
    # add_above_or_below_countertop(csv_path=csv_filename, countertop_json_path=image_details_countertop_output,
    #                               output_csv_path=csv_with_countertop)
    plot_above_below_polygons(csv_with_countertop, "../")