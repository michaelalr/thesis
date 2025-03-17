import json
import os
import random
import re
from collections import Counter
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from PIL import Image, ImageDraw


def remove_ips(data):
    # Define the IPs to remove
    unwanted_ips = {"46.120.86.255"}  # Set of IPs to remove
    # Filter out entries with these IPs
    filtered_ips_responses = [entry for entry in data if entry["ip_address"] not in unwanted_ips]
    return filtered_ips_responses


def find_duplicates(data):
    # Convert JSON data to a DataFrame
    df = pd.DataFrame(data)
    # Define the fields to check for duplicates
    duplicate_fields = ["image_path", "chosen_polygon", "user_id", "chosen_item", "room_type", "batch_number"]
    # Find duplicate rows based on the specified fields
    df_no_duplicates = df.drop_duplicates(subset=duplicate_fields, keep='first')
    return df_no_duplicates


def find_different_answers_per_user_keep_first(df):
    # Convert date and time columns to datetime objects
    df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"])

    # Group by key fields
    polygon_groups = df.groupby(["user_id", "image_path", "chosen_item", "room_type", "batch_number"])

    # Identify duplicate groups with different polygons
    duplicate_indices_to_drop = []

    # Iterate over the groups
    for (user_id, image_path, item, room, batch), group in polygon_groups:
        if len(group["chosen_polygon"].unique()) > 1:  # Check if there are different polygons for the same parameters
            # Sort by datetime (oldest first)
            group_sorted = group.sort_values(by="datetime", ascending=True)
            # Keep the oldest (first row), drop the rest
            indices_to_drop = group_sorted.iloc[1:].index.tolist()
            duplicate_indices_to_drop.extend(indices_to_drop)

    # Remove the newer duplicates from the original DataFrame
    keep_first_response_df = df.drop(duplicate_indices_to_drop)
    return keep_first_response_df


def display_different_answers_per_user(df):
    # Ensure the directory exists
    output_dir = "images_with_diff_polygons"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Group by key fields and filter groups with multiple distinct polygons
    polygon_groups = df.groupby(["user_id", "image_path", "chosen_item", "room_type", "batch_number"])
    filtered_groups = polygon_groups.filter(lambda x: x['chosen_polygon'].nunique() > 1)

    # Iterate over the filtered groups and display the polygons
    for (user_id, image_path, item, room, batch), group in filtered_groups.groupby(
            ["user_id", "image_path", "chosen_item", "room_type", "batch_number"]):
        try:
            # Load and prepare the image
            response = requests.get(image_path)
            img = Image.open(BytesIO(response.content)).convert("RGB")
            draw = ImageDraw.Draw(img)

            # Draw each polygon with a different color
            colors = ["red", "green", "blue", "purple", "orange"]
            for idx, (_, row) in enumerate(group.iterrows()):
                polygon = json.loads(row['chosen_polygon'])
                polygon_tuples = [tuple(coord) for coord in polygon]
                draw.polygon(polygon_tuples, outline=colors[idx % len(colors)], width=3)
                draw.text(polygon_tuples[0], f"Polygon {idx + 1}", fill=colors[idx % len(colors)])

            # Save the image with polygons
            image_name = Path(image_path).stem
            file_name = f"{image_name}_{user_id}_{item}_{batch}.jpg"  # You can change the format as needed
            save_path = os.path.join(output_dir, file_name)
            img.save(save_path)

            print(f"Image saved: {save_path}")

        except Exception as e:
            print(f"Failed to process {image_path}: {e}")

    print("draw all")


def separate_test_and_all_other_data(df):
    # Filter "validation" responses
    test_df = df[(df['room_type'] == 'validation')]

    # Filter all other responses
    all_other_df = df.drop(test_df.index)

    # Save to JSON files
    test_df.to_json('test_responses.json', orient='records', indent=4)
    all_other_df.to_json('all_other_responses.json', orient='records', indent=4)

    return test_df, all_other_df


def remove_extra_rows(df, batch_folders, clean_df_name, is_test=False):
    # Collect all valid batch entries
    batch_entries = set()

    for folder in batch_folders:
        for file_name in os.listdir(folder):
            if file_name.endswith('.json') and ("_Val_" in file_name) == is_test:
                with open(os.path.join(folder, file_name), 'r') as f:
                    batch_number_match = re.search(r"_batch_(\d+)", file_name)
                    if batch_number_match:
                        batch_number = int(batch_number_match.group(1))
                    else:
                        batch_number = None  # or handle if missing
                    batch_data = json.load(f)
                    for entry in batch_data:
                        batch_entries.add((
                            entry['user_id'],
                            entry['image_path_html'],
                            entry['chosen_item'],
                            entry['room_type'],
                            batch_number
                        ))

    # Now check each row in the DataFrame
    def is_in_batches(row):
        image_path_html = "/".join(row['image_path'].split('/')[-3:])
        return (
            row['user_id'], image_path_html, row['chosen_item'], row['room_type'], row['batch_number']) in batch_entries

    # Apply the check
    df['exists_in_batches'] = df.apply(is_in_batches, axis=1)
    # Drop extra rows from the DataFrame
    df_cleaned = df[df['exists_in_batches']].drop(columns=['exists_in_batches'])
    # Save the cleaned DataFrame
    df_cleaned.to_csv(clean_df_name + '.csv', index=False)

    # Convert datetime columns to string
    df_cleaned["datetime"] = df_cleaned["datetime"].astype(str)
    # Convert DataFrame to a list of dictionaries
    cleaned_data = df_cleaned.to_dict(orient="records")
    # Save the JSON file with proper formatting
    with open(clean_df_name + ".json", "w") as f:
        json.dump(cleaned_data, f, indent=4)

    return df_cleaned


def clean_data(all_responses):
    filtered_ips_responses = remove_ips(data=all_responses)
    df_no_duplicates = find_duplicates(data=filtered_ips_responses)
    keep_first_response_df = find_different_answers_per_user_keep_first(df=df_no_duplicates)
    test_df, all_other_df = separate_test_and_all_other_data(df=keep_first_response_df)

    batch_folders = ['output_batches/user_1', 'output_batches/user_2', 'output_batches/user_3']

    clean_df_name = "cleaned_responses"
    is_test = False
    df_cleaned = remove_extra_rows(df=all_other_df, batch_folders=batch_folders, clean_df_name=clean_df_name,
                                   is_test=is_test)

    clean_df_name = "test_cleaned_responses"
    is_test = True
    test_df['image_path'] = test_df['image_path'].str.replace('%20', ' ', regex=False)
    test_df_cleaned = remove_extra_rows(df=test_df, batch_folders=batch_folders, clean_df_name=clean_df_name,
                                        is_test=is_test)
    return df_cleaned, test_df_cleaned


def create_final_train_df(cleaned_df, image_details_json_path):
    # Load the image details JSON
    with open(image_details_json_path, 'r') as f:
        image_details = json.load(f)

    # Build a quick lookup for image_path_html -> containers_polygons
    image_details_lookup = {
        detail["image_path_html"]: detail["containers_mask_polygon"]
        for detail in image_details
    }

    # Prepare list to store rows for the new DataFrame
    train_rows = []

    # Group the cleaned DataFrame
    grouped = cleaned_df.groupby(["image_path", "chosen_item", "room_type", "batch_number"])

    for (image_path, chosen_item, room_type, batch_number), group in grouped:
        # If only one response, use it directly
        if len(group) == 1:
            chosen_polygon = group.iloc[0]["chosen_polygon"]
        else:
            # Count the polygons to find majority
            polygons = group["chosen_polygon"].tolist()
            polygon_counts = Counter(polygons)
            most_common = polygon_counts.most_common()

            if most_common[0][1] >= 2:
                # Take the majority polygon
                chosen_polygon = most_common[0][0]
            else:
                # No majority, pick one randomly
                chosen_polygon = random.choice(polygons)

        # Extract the relative image_path_html from the full image_path
        relative_path = '/'.join(image_path.split('/')[-3:])  # Example: images/kitchen/9_segmented_sun_...

        # Get the containers_polygons from the lookup
        containers_polygons = image_details_lookup.get(relative_path, [])

        # Add the row to the final list
        train_rows.append({
            "image_path": image_path,
            "containers_polygons": containers_polygons,
            "chosen_polygon": chosen_polygon,
            "chosen_item": chosen_item,
            "room_type": room_type
        })

    # Create the new DataFrame
    train_df = pd.DataFrame(train_rows)

    # Optional: save to CSV or JSON
    train_df.to_csv("train_data.csv", index=False)

    # Convert DataFrame to a list of dictionaries
    trained_data = train_df.to_dict(orient="records")
    # Save the JSON file with proper formatting
    with open("train_data.json", "w") as f:
        json.dump(trained_data, f, indent=4)

    print(f"Final DataFrame created with {len(train_df)} rows.")

    return train_df


def create_test_gt(image_details_json_path):
    # List your JSON files
    json_files = [
        "output_jsons/response_output_batches_build_test_set_usr_4_Val_Bottle_opener_batch_4.json",
        "output_jsons/response_output_batches_build_test_set_usr_4_Val_Iron_Tupperware_containers_batch_3.json",
        "output_jsons/response_output_batches_build_test_set_usr_4_Val_Random_Ear_toothpick_batch_2.json",
        "output_jsons/response_output_batches_build_test_set_usr_4_Val_Screwdriver_Painkiller_batch_1.json"
    ]

    # Read and merge all JSON files into a single DataFrame
    dfs = [pd.read_json(file) for file in json_files]
    gt_test_df = pd.concat(dfs, ignore_index=True)

    gt_test_df['image_path'] = gt_test_df['image_path'].str.replace('%20', ' ', regex=False)

    # Load the image details JSON file
    with open(image_details_json_path, "r") as f:
        image_details = json.load(f)

    # Build a lookup dictionary for image_path_html -> containers_polygons
    image_details_lookup = {
        detail["image_path_html"]: detail["containers_mask_polygon"]
        for detail in image_details
    }

    # Prepare the final list of rows
    test_rows = []

    for _, row in gt_test_df.iterrows():
        image_path = row["image_path"]
        chosen_polygon = row["chosen_polygon"]
        chosen_item = row["chosen_item"]

        # Extract relative path
        relative_path = "/".join(image_path.split("/")[-3:])

        # Get the containers_polygons from the lookup
        containers_polygons = image_details_lookup.get(relative_path, [])

        # Add the row to the final list
        test_rows.append({
            "image_path": image_path,
            "containers_polygons": containers_polygons,
            "chosen_polygon": chosen_polygon,
            "chosen_item": chosen_item
        })

    # Convert to DataFrame
    final_test_df = pd.DataFrame(test_rows)

    # Save to JSON if needed
    final_test_df.to_json("test_data.json", orient="records", indent=4)


if __name__ == "__main__":
    json_filename = 'upwork_responses_rotate.json'
    # Load the JSON file
    with open(json_filename, 'r') as f:
        all_responses = json.load(f)

    df_cleaned, test_df_cleaned = clean_data(all_responses)
    train_df = create_final_train_df(cleaned_df=df_cleaned, image_details_json_path="image_details.json")

    create_test_gt(image_details_json_path="image_details_validation_new.json")
