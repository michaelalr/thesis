import ast
import json
import math
import os
import numpy as np
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from matplotlib.patheffects import withStroke
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
                    polygon = patches.Polygon(coords, closed=True, fill=True, edgecolor='black', facecolor=color,
                                              alpha=0.8)
                    ax.add_patch(polygon)

            except Exception as e:
                print(f"Error drawing polygon for {image_path_html}: {e}")
                continue

        plt.axis('off')
        plt.tight_layout()
        plt.show()
        shown_images += 1


def add_height_width_ratio(csv_path, output_csv_path):
    df = pd.read_csv(csv_path)
    columns_to_drop = ["height_width_ratio", "description", "neighbors"]
    df = df.drop(columns=columns_to_drop)

    def compute_dimensions(polygon_str):
        try:
            coords = ast.literal_eval(polygon_str)

            if not isinstance(coords, list) or len(coords) < 1:
                return 0.0, 0.0, 0.0

            if len(coords) == 1:
                return 0.0, 0.0, 0.0  # A single point has no height or width

            xs = [pt[0] for pt in coords]
            ys = [pt[1] for pt in coords]

            width = max(xs) - min(xs)
            height = max(ys) - min(ys)

            if width == 0:
                ratio = float('inf') if height > 0 else 0.0
            else:
                ratio = round(height / width, 3)

            return ratio, height, width

        except Exception as e:
            print(f"Failed to compute ratio for polygon: {polygon_str} – {e}")
            return 0.0, 0.0, 0.0

    df[["height_width_ratio", "container_height", "container_width"]] = df["polygon"].apply(
        lambda p: pd.Series(compute_dimensions(p)))
    df.to_csv(output_csv_path, index=False)
    print(f"Saved CSV with height_width_ratio to {output_csv_path}")


def add_ids_to_csv(csv_path, output_path):
    df = pd.read_csv(csv_path)
    df.insert(0, "id", range(1, len(df) + 1))  # ID starts at 1
    df.to_csv(output_path, index=False)
    print(f"Saved CSV with IDs to {output_path}")


def describe_csv_row(row):
    id = row["id"]
    label = row["label"]
    score = row["score"]
    position = row["above_or_below_countertop"]
    ratio = row["height_width_ratio"]
    neighbors = row.get("neighbors", None)
    anchor_neighbors = row.get("anchor_neighbors", None)

    description = (
        f'The container id {id} has a label of "{label}" with confidence of {score} from a detection model, '
        f'it is {position} the countertop, and the ratio between its height and width is {ratio}.'
    )

    direction_map = {
        "above": "above",
        "below": "below",
        "left": "to the left of",
        "right": "to the right of",
        "top_left": "at the top-left of",
        "top_right": "at the top-right of",
        "bottom_left": "at the bottom-left of",
        "bottom_right": "at the bottom-right of",
    }

    # Handle container neighbors if valid
    try:
        if isinstance(neighbors, str):
            neighbors = json.loads(neighbors)

        if isinstance(neighbors, dict):
            phrases = [
                f"{direction_map[d]} it there is the container id {n}"
                for d, n in neighbors.items() if n is not None
            ]

            if phrases:
                description += " " + ", ".join(phrases) + "."

    except Exception as e:
        print(f"Error parsing neighbors: {e}")
        pass  # In case of malformed JSON or any error, skip neighbor info

    # Handle anchor neighbors if valid
    try:
        if isinstance(anchor_neighbors, str):
            anchor_neighbors = json.loads(anchor_neighbors)

        if isinstance(anchor_neighbors, dict):
            anchor_phrases = [
                f"{direction_map[d]} it there is a {anchor}"
                for d, anchor in anchor_neighbors.items() if anchor is not None
            ]
            if anchor_phrases:
                description += " " + ", ".join(anchor_phrases) + "."
    except Exception as e:
        print(f"Error parsing anchor_neighbors: {e}")

    return description


def add_descriptions_to_csv(csv_path, output_path):
    df = pd.read_csv(csv_path)
    df["description"] = df.apply(describe_csv_row, axis=1)
    df.to_csv(output_path, index=False)
    print(f"Saved CSV with descriptions to {output_path}")


def add_score_column_to_csv(csv_path, json_path, output_csv_path):
    # Load the CSV
    df = pd.read_csv(csv_path)

    # Load the JSON
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    # Normalize JSON data into a dict indexed by image_path_html
    json_dict = {entry['image_path_html']: entry for entry in json_data}

    # List to collect scores
    scores = []

    for idx, row in df.iterrows():
        image_path = row['image_path_html']
        csv_polygon = ast.literal_eval(row['polygon'])  # parse polygon list safely
        score_found = None

        json_entry = json_dict.get(image_path)
        if json_entry:
            containers_with_labels = ast.literal_eval(json_entry['containers_mask_polygon_with_labels'])
            for label, score, poly in containers_with_labels:
                if poly == csv_polygon:
                    score_found = score
                    break

        scores.append(score_found)

    # Insert score column after 'label'
    label_index = df.columns.get_loc('label')
    df.insert(label_index + 1, 'score', scores)

    # Save updated CSV
    df.to_csv(output_csv_path, index=False)
    print(f"Updated CSV saved to: {output_csv_path}")


def polygon_center(polygon):
    """Return center (x, y) of a polygon."""
    polygon = np.array(polygon)
    x_coords = polygon[:, 0]
    y_coords = polygon[:, 1]
    return np.mean(x_coords), np.mean(y_coords)


def is_neighbor_within_gap(poly1, poly2, ratio_threshold=0.25):
    # Ensure both polygons are valid (at least 3 unique points)
    if len(poly1) < 3 or len(poly2) < 3:
        return False  # Skip invalid polygons

    try:
        shapely1 = Polygon(poly1)
        shapely2 = Polygon(poly2)
    except ValueError:
        return False  # Skip invalid polygon shapes

    gap = shapely1.distance(shapely2)

    # Compute bounding box sizes
    min_x1 = min(pt[0] for pt in poly1)
    max_x1 = max(pt[0] for pt in poly1)
    min_y1 = min(pt[1] for pt in poly1)
    max_y1 = max(pt[1] for pt in poly1)
    width1 = max_x1 - min_x1
    height1 = max_y1 - min_y1

    min_x2 = min(pt[0] for pt in poly2)
    max_x2 = max(pt[0] for pt in poly2)
    min_y2 = min(pt[1] for pt in poly2)
    max_y2 = max(pt[1] for pt in poly2)
    width2 = max_x2 - min_x2
    height2 = max_y2 - min_y2

    avg_dim = (width1 + width2 + height1 + height2) / 4
    return gap <= avg_dim * ratio_threshold

def parse_polygon_string(polygon_str):
    """Convert string like '[[1,2],[3,4]]' to list of lists."""
    return ast.literal_eval(polygon_str)


def determine_neighbors_for_image(image_df):
    """Given one image's DataFrame, return a dict of container id -> neighbor dict."""
    centers = {}
    polygons = {}
    ids = list(image_df["id"])

    for _, row in image_df.iterrows():
        pid = row["id"]
        poly = row["polygon"]
        polygons[pid] = poly
        centers[pid] = polygon_center(poly)

    dominance_ratio = 1.5
    directions = ["above", "below", "left", "right", "top_left", "top_right", "bottom_left", "bottom_right"]
    relations = {}

    for id1 in ids:
        cx1, cy1 = centers[id1]
        poly1 = polygons[id1]
        width1 = image_df.loc[image_df["id"] == id1, "container_width"].values[0]
        height1 = image_df.loc[image_df["id"] == id1, "container_height"].values[0]

        horizontal_align_threshold = height1 * 0.6
        vertical_align_threshold = width1 * 0.6
        max_neighbor_dist = ((width1 + height1) / 2) * 2.0

        relations[id1] = {dir: None for dir in directions}
        closest_dist = {dir: float("inf") for dir in directions}

        for id2 in ids:
            if id1 == id2:
                continue

            cx2, cy2 = centers[id2]
            poly2 = polygons[id2]
            dx = cx2 - cx1
            dy = cy2 - cy1
            center_dist = (dx ** 2 + dy ** 2) ** 0.5

            # Skip if they’re too far apart
            if not is_neighbor_within_gap(poly1, poly2):
                continue

            # Skip if too far
            if center_dist > max_neighbor_dist:
                continue

            abs_dx = abs(dx)
            abs_dy = abs(dy)

            # Prefer smaller containers if one contains the other
            def is_valid_polygon(poly):
                return isinstance(poly, list) and len(poly) >= 3

            if is_valid_polygon(poly1) and is_valid_polygon(poly2):
                shapely1 = Polygon(poly1)
                shapely2 = Polygon(poly2)
                contains = shapely1.contains(shapely2) or shapely2.contains(shapely1)
                area1 = shapely1.area
                area2 = shapely2.area
            else:
                contains = False
                area1 = area2 = float("inf")  # Set area high so no preference

            def should_replace(direction, dist, id2):
                if contains:
                    # Prefer smaller container
                    return (area2 < area1) and (dist < closest_dist[direction])
                else:
                    return dist < closest_dist[direction]

            # Horizontal dominant
            if abs_dx > abs_dy * dominance_ratio and abs_dy < horizontal_align_threshold:
                if dx > 0 and should_replace("right", center_dist, id2):
                    relations[id1]["right"] = id2
                    closest_dist["right"] = center_dist
                elif dx < 0 and should_replace("left", center_dist, id2):
                    relations[id1]["left"] = id2
                    closest_dist["left"] = center_dist

            # Vertical dominant
            elif abs_dy > abs_dx * dominance_ratio and abs_dx < vertical_align_threshold:
                if dy > 0 and should_replace("below", center_dist, id2):
                    relations[id1]["below"] = id2
                    closest_dist["below"] = center_dist
                elif dy < 0 and should_replace("above", center_dist, id2):
                    relations[id1]["above"] = id2
                    closest_dist["above"] = center_dist

            else:
                # Diagonal directions (no dominant)
                if dx < 0 and dy < 0 and should_replace("top_left", center_dist, id2):
                    relations[id1]["top_left"] = id2
                    closest_dist["top_left"] = center_dist
                elif dx > 0 and dy < 0 and should_replace("top_right", center_dist, id2):
                    relations[id1]["top_right"] = id2
                    closest_dist["top_right"] = center_dist
                elif dx < 0 and dy > 0 and should_replace("bottom_left", center_dist, id2):
                    relations[id1]["bottom_left"] = id2
                    closest_dist["bottom_left"] = center_dist
                elif dx > 0 and dy > 0 and should_replace("bottom_right", center_dist, id2):
                    relations[id1]["bottom_right"] = id2
                    closest_dist["bottom_right"] = center_dist

    return relations


def add_neighbor_column_to_csv(info_csv_path, output_csv_path):
    df = pd.read_csv(info_csv_path)

    # Ensure polygon and id are parsed correctly
    df["polygon"] = df["polygon"].apply(parse_polygon_string)
    df["id"] = df["id"].astype(int)

    df["neighbors"] = ""
    # Define the default neighbor structure (all None) for skipped containers
    # This is needed for the .get() method's default value
    directions = ["above", "below", "left", "right",
                  "top_left", "top_right", "bottom_left", "bottom_right"]
    default_neighbors = {direction: None for direction in directions}

    for image_path, group in df.groupby("image_path_html"):
        relations = determine_neighbors_for_image(group)
        for idx, row in group.iterrows():
            container_id = row["id"]

            # --- FIX: Use dict.get() to avoid KeyError ---
            # If container_id exists in relations, get its value.
            # Otherwise, return the default_neighbors dictionary.
            neighbors_dict = relations.get(container_id, default_neighbors)

            # Convert the resulting dictionary to a JSON string
            neighbors_json = json.dumps(neighbors_dict)

            # Assign the JSON string to the correct row in the main DataFrame
            # using the index 'idx' from the group iteration.
            df.loc[idx, "neighbors"] = neighbors_json

    df.to_csv(output_csv_path, index=False)
    print(f"Updated CSV saved to: {output_csv_path}")

def load_anchor_json(json_path):
    with open(json_path, 'r') as f:
        data = json.load(f)
    anchors_by_filename = {}
    for entry in data:
        img_path = entry['image_path_html']
        fname_key = os.path.basename(img_path).split('_segmented_')[-1]
        anchors = []
        try:
            labeled_polygons = ast.literal_eval(entry['containers_mask_polygon_with_labels'])
            for label, score, poly in labeled_polygons:
                # if len(poly) >= 3:
                # Keep even if poly has < 3 points
                anchors.append({'label': label, 'polygon': poly})
        except:
            continue
        anchors_by_filename[fname_key] = anchors
    return anchors_by_filename

def is_anchor_neighbor_within_gap(poly1, poly2, ratio_threshold=0.5):
    def to_geometry(poly):
        if len(poly) == 1:
            return Point(poly[0])
        elif len(poly) == 2:
            return LineString(poly)
        elif len(poly) >= 3:
            return Polygon(poly)
        return None

    geom1 = to_geometry(poly1)
    geom2 = to_geometry(poly2)

    if geom1 is None or geom2 is None:
        return False

    # Slightly buffer point and line geometries to avoid degenerate cases
    if isinstance(geom1, (Point, LineString)):
        geom1 = geom1.buffer(1)
    if isinstance(geom2, (Point, LineString)):
        geom2 = geom2.buffer(1)

    try:
        gap_centroid = geom1.centroid.distance(geom2.centroid)
        gap_edge = geom1.distance(geom2)
    except Exception:
        return False

    # Use the largest dimension of both bounding boxes as a scale reference
    all_x = [pt[0] for pt in poly1 + poly2]
    all_y = [pt[1] for pt in poly1 + poly2]
    max_dim = max(max(all_x) - min(all_x), max(all_y) - min(all_y))

    # Slightly more lenient on edge distances
    gap_centroid_cond = gap_centroid <= max_dim * ratio_threshold
    gap_edge_cond = gap_edge <= max_dim * ratio_threshold * 0.5

    return gap_centroid_cond or gap_edge_cond

def determine_anchor_neighbors_for_image(image_df, anchors):
    directions = ["above", "below", "left", "right", "top_left", "top_right", "bottom_left", "bottom_right"]
    results = {}

    for _, row in image_df.iterrows():
        cid = row['id']
        poly1 = row['polygon']
        cx1, cy1 = polygon_center(poly1)
        width1 = row['container_width']
        height1 = row['container_height']

        horizontal_align_threshold = height1 * 0.6
        vertical_align_threshold = width1 * 0.6
        max_neighbor_dist = ((width1 + height1) / 2) * 2.0

        closest = {dir: (None, float("inf")) for dir in directions}
        for anchor in anchors:
            poly2 = anchor['polygon']
            cx2, cy2 = polygon_center(poly2)
            dx = cx2 - cx1
            dy = cy2 - cy1
            center_dist = (dx ** 2 + dy ** 2) ** 0.5

            if not is_anchor_neighbor_within_gap(poly1, poly2) or center_dist > max_neighbor_dist:
                continue

            abs_dx = abs(dx)
            abs_dy = abs(dy)
            label = anchor['label']

            def update_dir(direction):
                if center_dist < closest[direction][1]:
                    closest[direction] = (label, center_dist)

            if abs_dx > abs_dy * 1.5 and abs_dy < horizontal_align_threshold:
                if dx > 0:
                    update_dir("right")
                else:
                    update_dir("left")
            elif abs_dy > abs_dx * 1.5 and abs_dx < vertical_align_threshold:
                if dy > 0:
                    update_dir("below")
                else:
                    update_dir("above")
            else:
                if dx < 0 and dy < 0:
                    update_dir("top_left")
                elif dx > 0 and dy < 0:
                    update_dir("top_right")
                elif dx < 0 and dy > 0:
                    update_dir("bottom_left")
                elif dx > 0 and dy > 0:
                    update_dir("bottom_right")

        results[cid] = {dir: closest[dir][0] for dir in directions}
    return results


def add_anchor_neighbors_column_to_csv(info_csv_path, json_path, output_csv_path):
    df = pd.read_csv(info_csv_path)
    df["polygon"] = df["polygon"].apply(parse_polygon_string)
    df["id"] = df["id"].astype(int)

    anchors_by_file = load_anchor_json(json_path)
    df["anchor_neighbors"] = ""

    for image_path, group in df.groupby("image_path_html"):
        key = os.path.basename(image_path).split('_segmented_')[-1]
        anchors = anchors_by_file.get(key, [])
        anchor_neighbors = determine_anchor_neighbors_for_image(group, anchors)
        for idx, row in group.iterrows():
            cid = row['id']
            neighbors = anchor_neighbors.get(cid, {d: None for d in [
                "above", "below", "left", "right",
                "top_left", "top_right", "bottom_left", "bottom_right"
            ]})
            df.loc[idx, "anchor_neighbors"] = json.dumps(neighbors)

    df.to_csv(output_csv_path, index=False)
    print(f"Updated CSV with anchor neighbors saved to: {output_csv_path}")

# --- Visualization Function ---
def plot_image_with_polygons(df, image_folder, n=5):
    sampled_images = df["image_path_html"].drop_duplicates().sample(n)

    for img_path in sampled_images:
        subset = df[df["image_path_html"] == img_path]

        img_full_path = os.path.normpath(os.path.join("..", img_path))
        if not os.path.exists(img_full_path):
            print(f"Image not found: {img_full_path}")
            continue

        img = plt.imread(img_full_path)
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.imshow(img)
        ax.set_title(f"Image: {os.path.basename(img_path)}", fontsize=14)

        for _, row in subset.iterrows():
            # poly = np.array(row["polygon"])
            poly = ast.literal_eval(row["polygon"])
            container_id = row["id"]

            patch = patches.Polygon(poly, closed=True, edgecolor='lime', facecolor='none', linewidth=2)
            ax.add_patch(patch)

            # Label in center
            cx, cy = polygon_center(poly)
            ax.text(cx, cy, str(container_id),
                    fontsize=10, weight='bold', color='white',
                    path_effects=[withStroke(linewidth=2, foreground='black')],
                    ha='center', va='center')

        plt.axis('off')
        plt.show()


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
    # plot_above_below_polygons(csv_with_countertop, "../")

    csv_with_ratio = "../labeled_containers_with_ratio.csv"
    # add_height_width_ratio(csv_path=csv_with_countertop, output_csv_path=csv_with_ratio)

    csv_with_ids = "../labeled_containers_with_ids.csv"
    # add_ids_to_csv(csv_path=csv_with_ratio, output_path=csv_with_ids)

    csv_with_description = "../labeled_containers_with_description.csv"
    # add_descriptions_to_csv(csv_path=csv_with_ids, output_path=csv_with_description)

    image_details_with_labels_score = "../image_details/image_details_with_labels_score.json"
    csv_with_scores = "../labeled_containers_with_scores.csv"
    # add_score_column_to_csv(csv_path=csv_with_description, json_path=image_details_with_labels_score,
    #                         output_csv_path=csv_with_scores)

    csv_with_height_width = "../labeled_containers_with_height_width.csv"
    # add_height_width_ratio(csv_path=csv_with_description, output_csv_path=csv_with_height_width)

    csv_with_neighbors = "../labeled_containers_with_neighbors.csv"
    # add_neighbor_column_to_csv(
    #     info_csv_path=csv_with_height_width,
    #     output_csv_path=csv_with_neighbors
    # )

    # plot_image_with_polygons(
    #     df=pd.read_csv(csv_with_neighbors),
    #     image_folder="..",  # adjust to match your local path
    #     n=5
    # )

    image_details_with_anchors = "../image_details/image_details_with_anchors.json"
    csv_with_anchors = "../labeled_containers_with_anchors.csv"
    # add_anchor_neighbors_column_to_csv(
    #     info_csv_path=csv_with_neighbors,
    #     json_path=image_details_with_anchors,
    #     output_csv_path=csv_with_anchors
    # )

    add_descriptions_to_csv(csv_path=csv_with_anchors, output_path=csv_with_description)