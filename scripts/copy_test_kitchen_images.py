import json
import os
import shutil
from urllib.parse import urlparse
import csv

def copy_test_kitchen_images(json_file_path, images_folder, output_folder):



    # === STEP 1: LOAD FILENAMES FROM JSON ===
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    json_filenames = set()
    for item in data:
        url = item.get("image_path", "")
        if url:
            filename = os.path.basename(urlparse(url).path)  # Extract just the filename
            json_filenames.add(filename)

    # === STEP 2: COPY MATCHING FILES ===
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    copied = 0
    for filename in json_filenames:
        source_path = os.path.join(images_folder, filename)
        dest_path = os.path.join(output_folder, filename)
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            copied += 1
        else:
            print(f"Warning: {filename} not found in image folder.")

    print(f"✅ Done. Copied {copied} images to: {output_folder}")


def create_test_kitchen_images_csv(json_file_path, output_csv_path):
    # === STEP 1: LOAD AND FILTER JSON ===
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    filtered_rows = []
    for item in data:
        if item.get("chosen_item") == "Bottle opener":
            image_path = item.get("image_path")
            filtered_rows.append([image_path, '["Bottle opener"]'])

    # === STEP 2: WRITE TO CSV ===
    with open(output_csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["image_path", "chosen_item"])
        writer.writerows(filtered_rows)

    print(f"✅ CSV created with {len(filtered_rows)} rows: {output_csv_path}")

if __name__ == '__main__':
    # === CONFIGURATION ===
    json_file_path = "../data/test_data/test_data_kitchen.json"     # Path to your JSON file
    images_folder = "../images/validation/"                         # Folder with all images
    output_folder = "../images/test_kitchen/"                       # Destination folder for matched images

    # copy_test_kitchen_images(json_file_path, images_folder, output_folder)

    output_csv_path = "../data/test_data/test_kitchen_images_table.csv"  # Output CSV file path
    create_test_kitchen_images_csv(json_file_path, output_csv_path)