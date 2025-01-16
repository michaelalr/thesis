import json
from collections import OrderedDict


def create_batches(json_file):
    with open(json_file, 'r') as file:
        data = json.load(file)

    # Initialize lists for each category
    screwdriver_images = []
    painkiller_images = []
    random_images = []
    ear_toothpick_images = []
    iron_images = []
    food_containers_images = []
    bottle_opener_images = []

    # Categorize the items
    for item in data:
        item['user_id'] = 1  # Add user_id field
        if 'screwdriver' in item['image_path_html'].lower():
            screwdriver_images.append(item)
        elif 'painkiller' in item['image_path_html'].lower():
            painkiller_images.append(item)
        elif 'random' in item['image_path_html'].lower():
            random_images.append(item)
        elif 'ear_toothpick' in item['image_path_html'].lower():
            ear_toothpick_images.append(item)
        elif 'iron' in item['image_path_html'].lower():
            iron_images.append(item)
        elif 'food_containers' in item['image_path_html'].lower():
            food_containers_images.append(item)
        elif 'bottle_opener' in item['image_path_html'].lower():
            bottle_opener_images.append(item)

    # Combine lists to form batches
    batch_1 = screwdriver_images + painkiller_images
    batch_2 = random_images + ear_toothpick_images
    batch_3 = iron_images + food_containers_images
    batch_4 = bottle_opener_images

    # Save the batches into separate JSON files
    with open('output_batches/user_1/usr_1_Val_Screwdriver_Painkiller_batch_1.json', 'w') as b1, open(
            'output_batches/user_1/usr_1_Val_Random_Ear_toothpick_batch_2.json', 'w') as b2, open(
        'output_batches/user_1/usr_1_Val_Iron_Tupperware_containers_batch_3.json', 'w') as b3, open(
        'output_batches/user_1/usr_1_Val_Bottle_opener_batch_4.json', 'w') as b4:
        json.dump(batch_1, b1, indent=4)
        json.dump(batch_2, b2, indent=4)
        json.dump(batch_3, b3, indent=4)
        json.dump(batch_4, b4, indent=4)


# Example usage
create_batches('image_details_validation.json')
