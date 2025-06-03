import json
import os

import cv2
import matplotlib.pyplot as plt


def plot_bbox_comparisons(ferret_json_path, images_json_path, image_folder, num_images=5):
    with open(ferret_json_path, 'r') as f1, open(images_json_path, 'r') as f2:
        ferret_data = json.load(f1)
        images_data = json.load(f2)

    # Normalize json2 for fast lookup by (image, item)
    images_data_lookup = {
        (entry['image_path'], entry['chosen_item'].strip().lower()): entry
        for entry in images_data
    }

    plotted = 0

    for ferret_entry in ferret_data:
        image_name = ferret_entry['image']
        conversations = ferret_entry.get('conversations', [])
        box_sets = ferret_entry.get('box_x1y1x2y2', [])

        # Get item name from human prompt
        item = ''
        for conv in conversations:
            if conv['from'] == 'human':
                if 'value' in conv and ' is a ' in conv['value']:
                    item = conv['value'].split(' is a ')[-1].split(' stored?')[0].strip().lower()
                    break

        if not item:
            continue

        key = (image_name, item)
        if key not in images_data_lookup:
            continue

        images_entry = images_data_lookup[key]

        # Load image
        image_path = os.path.join(image_folder, image_name)
        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            continue
        img = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)

        # Plot
        plt.figure(figsize=(10, 8))
        plt.imshow(img)
        ax = plt.gca()

        # Plot box_x1y1x2y2 in RED
        for box in box_sets[0]:  # Using the first answer set
            x1, y1, x2, y2 = box
            width, height = x2 - x1, y2 - y1
            ax.add_patch(
                plt.Rectangle((x1, y1), width, height, edgecolor='red', linewidth=2, fill=False, label='box_x1y1x2y2'))

        # Plot chosen_polygon in BLUE
        try:
            polygon = json.loads(images_entry['chosen_polygon'])  # e.g., [[x1,y1],[x2,y2],...]
            polygon.append(polygon[0])  # close the loop
            xs, ys = zip(*polygon)
            plt.plot(xs, ys, 'b-', linewidth=2, label='chosen_polygon')
        except Exception as e:
            print(f"Error parsing polygon for {image_name}: {e}")

        plt.title(f"{image_name} — Item: {item}")
        plt.legend()
        plt.axis('off')
        plt.tight_layout()
        plt.show()

        plotted += 1
        if plotted >= num_images:
            break


if __name__ == '__main__':
    ferret_json_path = "ferret_finetune_test_data.json"
    images_json_path = "../../data/test_data/test_data_kitchen_origin_filenames.json"
    image_folder = "../../images/test_kitchen_images_original"
    num_images = 5
    plot_bbox_comparisons(ferret_json_path=ferret_json_path, images_json_path=images_json_path,
                          image_folder=image_folder, num_images=num_images)
