import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from ast import literal_eval
from urllib.request import urlopen
from PIL import Image
import io

def show_polygon_for_image(json_path, image_filename, item, check_model_answer_polygon):
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

    answer_polygon = literal_eval(check_model_answer_polygon)
    answer_polygon = [(x, y) for x, y in answer_polygon]
    answer_patch = patches.Polygon(answer_polygon, closed=True, edgecolor='blue', fill=False, linewidth=2)
    ax.add_patch(answer_patch)

    # If polygon is not empty, draw it
    if chosen_polygon:
        polygon = [(x, y) for x, y in chosen_polygon]
        patch = patches.Polygon(polygon, closed=True, edgecolor='red', fill=False, linewidth=1)
        ax.add_patch(patch)
        subtitle = ""
    else:
        subtitle = "\nNot in any container"

    plt.title(f"{item} - {image_filename}{subtitle}")
    plt.axis('off')
    plt.show()



if __name__ == '__main__':
    # Example usage:
    json_path = "../data/train_data/train_data.json"
    image_filename = "15_segmented_sun_afxjcqelwocpxiyf.jpg"
    item = "Pan"
    check_model_answer_polygon = "[[429, 408], [392, 420], [394, 562], [431, 529]]"
    show_polygon_for_image(json_path=json_path, image_filename=image_filename, item=item, check_model_answer_polygon=check_model_answer_polygon)