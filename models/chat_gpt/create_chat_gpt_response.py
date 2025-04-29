import pandas as pd
import json
import random
import re
from typing import Optional

def parse_best_container_line(line):
    """Extracts the best container IDs from a line like 'Best container: 5 or 6' or 'None'"""
    match = re.search(r'Best container:\s*(.*)', line)
    if not match:
        return None
    container_str = match.group(1).strip()
    if container_str.lower() == "none":
        return []
    ids = re.findall(r'\d+', container_str)
    return [int(i) for i in ids] if ids else []


def extract_container_id(response: str, mode: str = "first") -> Optional[int]:
    """
    Extracts the container ID from a free-form response string.

    Args:
        response (str): The string containing the model's response.
        mode (str): "first" to return the first match, "random" to pick randomly from all matches.

    Returns:
        int or None: The extracted container ID, or None if no match found.
    """
    # Find all matches of "container id" or "Container id" followed by a number
    matches = re.findall(r"[Cc]ontainer id\s+(\d+)", response)

    if not matches:
        return None

    container_ids = [int(match) for match in matches]

    if mode == "random":
        return random.choice(container_ids)
    return container_ids[0]

def create_json_from_csvs(info_csv_path, response_csv_path, output_json_path, columns_in_description, story_prompt=False):
    # Load the CSVs
    info_df = pd.read_csv(info_csv_path)
    response_df = pd.read_csv(response_csv_path)

    # Normalize image paths to match across files
    info_df["image_path"] = info_df["image_path_html"].apply(lambda x: x.strip())
    response_df["image_path"] = response_df["image_path"].apply(lambda x: x.strip())

    results = []

    for _, row in response_df.iterrows():
        image_path = row["image_path"]
        full_image_url = f"https://michaelalr.github.io/thesis/{image_path}"
        response_text = row["response"]

        if not story_prompt:
            # items = eval(row["item"]) if isinstance(row["item"], str) else row["item"]
            items = [row["item"]]
            # Split the response by items
            response_sections = response_text.split("Item:")
            response_data = {}
            for section in response_sections[1:]:  # skip the first empty split
                lines = section.strip().splitlines()
                item_name = lines[0].strip()
                best_container_ids = []
                for line in lines:
                    if line.startswith("Best container:"):
                        best_container_ids = parse_best_container_line(line)
                        break
                response_data[item_name] = best_container_ids

            for item in items:
                container_ids = response_data.get(item, [])
                if not container_ids:
                    chosen_polygon = "[]"
                    info_columns = {}
                else:
                    # chosen_id = random.choice(container_ids)
                    chosen_id = container_ids[0]
                    # Find corresponding row in info_df
                    matched_row = info_df[(info_df["image_path"] == image_path) & (info_df["short_id"] == chosen_id)]
                    if not matched_row.empty:
                        chosen_polygon = matched_row.iloc[0]["polygon"]
                        info_columns = {
                            "label": matched_row.iloc[0]["label"],
                            "above_or_below_countertop": matched_row.iloc[0]["above_or_below_countertop"],
                            "height_width_ratio": matched_row.iloc[0]["height_width_ratio"]
                        }
                    else:
                        chosen_polygon = "[]"
                        info_columns = {}

                result = {
                    "image_path": full_image_url,
                    "chosen_item": item,
                    "chosen_polygon": chosen_polygon if isinstance(chosen_polygon, str) else json.dumps(chosen_polygon),
                    "info_columns": columns_in_description,
                    "room_type": "kitchen"
                }
                results.append(result)
        else:
            item = row["item"]
            chosen_id = extract_container_id(response=response_text)
            if not chosen_id:
                chosen_polygon = "[]"
            else:
                # Find corresponding row in info_df
                matched_row = info_df[(info_df["image_path"] == image_path) & (info_df["short_id"] == chosen_id)]
                if not matched_row.empty:
                    chosen_polygon = matched_row.iloc[0]["polygon"]
                else:
                    chosen_polygon = "[]"
            result = {
                "image_path": full_image_url,
                "chosen_item": item,
                "chosen_polygon": chosen_polygon if isinstance(chosen_polygon, str) else json.dumps(chosen_polygon),
                "info_columns": columns_in_description,
                "room_type": "kitchen"
            }
            results.append(result)

    # Save to JSON
    with open(output_json_path, "w") as f:
        json.dump(results, f, indent=4)

    print(f"Saved {len(results)} entries to {output_json_path}")

if __name__ == '__main__':
    info_csv_path = "../../short_id_pos_lab_anchors_with_description.csv"
    response_csv_path = "chatgpt_results_short_id_pos_lab_anchors.csv"
    output_json_path = "./chatgpt_train_short_id_pos_lab_anchors_sys_prmpt.json"
    columns_in_description_1 = ["label", "above_or_below_countertop", "height_width_ratio"]
    columns_in_description_2 = ["label", "score", "above_or_below_countertop", "height_width_ratio", "neighbors", "anchor_neighbors"]
    columns_in_description_3 = ["label", "above_or_below_countertop", "height_width_ratio", "neighbors", "anchor_neighbors"]
    columns_in_description_4 = ["id"]
    columns_in_description_5 = ["id", "label"]
    columns_in_description_6 = ["id", "above_or_below_countertop"]
    columns_in_description_7 = ["id", "above_or_below_countertop", "label"]
    columns_in_description_8 = ["id", "height_width_ratio"]
    columns_in_description_9 = ["id", "above_or_below_countertop", "label", "height_width_ratio"]
    columns_in_description_10 = ["id", "neighbors"]
    columns_in_description_11 = ["id", "anchor_neighbors"]
    columns_in_description_12 = ["id", "above_or_below_countertop", "label", "anchor_neighbors"]
    columns_in_description_13 = ["id", "above_or_below_countertop", "label", "neighbors"]
    columns_in_description_14 = ["id", "above_or_below_countertop", "label", "anchor_neighbors", "neighbors"]
    columns_in_description_15 = ["short_id", "above_or_below_countertop", "label", "anchor_neighbors"]

    create_json_from_csvs(
        info_csv_path=info_csv_path,
        response_csv_path=response_csv_path,
        output_json_path=output_json_path,
        columns_in_description=columns_in_description_15,
        # story_prompt=True
    )