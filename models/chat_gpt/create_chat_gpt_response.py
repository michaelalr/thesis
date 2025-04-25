import pandas as pd
import json
import random
import re

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

def create_json_from_csvs(info_csv_path, response_csv_path, output_json_path):
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
        items = eval(row["items"]) if isinstance(row["items"], str) else row["items"]
        response_text = row["response"]

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
                chosen_id = random.choice(container_ids)
                # Find corresponding row in info_df
                matched_row = info_df[(info_df["image_path"] == image_path) & (info_df["id"] == chosen_id)]
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
                "info_columns": ["label", "above_or_below_countertop", "height_width_ratio"],
                "room_type": "kitchen"
            }
            results.append(result)

    # Save to JSON
    with open(output_json_path, "w") as f:
        json.dump(results, f, indent=4)

    print(f"Saved {len(results)} entries to {output_json_path}")

if __name__ == '__main__':
    info_csv_path = "../../labeled_containers_with_description.csv"
    response_csv_path = "chatgpt_reasoning_results_2.csv"
    output_json_path = "./chatgpt_train_responses_2.json"
    create_json_from_csvs(
        info_csv_path=info_csv_path,
        response_csv_path=response_csv_path,
        output_json_path=output_json_path
    )