import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from ast import literal_eval
from urllib.request import urlopen
from PIL import Image
import io

def show_polygon_for_image(json_path, image_filename, item):
    # Load the data
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Find matching entry
    for entry in data:
        if image_filename in entry['image_path'] and entry['chosen_item'].lower() == item.lower():
            image_url = entry['image_path']
            chosen_polygon_raw = entry.get('chosen_polygon', '[]')
            chosen_polygon = literal_eval(chosen_polygon_raw)
            break
    else:
        print("No matching entry found.")
        return

    # Load image from URL
    image_data = urlopen(image_url).read()
    image = Image.open(io.BytesIO(image_data))

    # Plot image
    fig, ax = plt.subplots()
    ax.imshow(image)

    # If polygon is not empty, draw it
    if chosen_polygon:
        polygon = [(x, y) for x, y in chosen_polygon]
        patch = patches.Polygon(polygon, closed=True, edgecolor='red', fill=False, linewidth=2)
        ax.add_patch(patch)
        subtitle = ""
    else:
        subtitle = "\nNot in any container"

    plt.title(f"{item} - {image_filename}{subtitle}")
    plt.axis('off')
    plt.show()



if __name__ == '__main__':
    # Example usage:
    show_polygon_for_image("../data/train_data/train_data.json", "8_segmented_sun_aczownhxhsefytxm.jpg", "Plate")