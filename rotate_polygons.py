import json

from PIL import Image


def rotate_polygon(polygon, image_width, image_height, rotation_degree):
    if rotation_degree == 90:
        return [[image_height - y, x] for x, y in polygon]
    elif rotation_degree == 180:
        return [[image_width - x, image_height - y] for x, y in polygon]
    else:
        raise ValueError("Unsupported rotation degree. Only 90 and 180 degrees are supported.")


def adjust_polygons(polygons_str, image_width, image_height, rotation_degree):
    polygons = json.loads(polygons_str)
    rotated_polygons = [rotate_polygon(polygon, image_width, image_height, rotation_degree) for polygon in polygons]
    return json.dumps(rotated_polygons)


def process_images(json_file_path, image_path_field, polygon_field_to_rotate, update_json_path, image_paths_90,
                   image_paths_180):
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    image_info_dict = {item[image_path_field]: item for item in data}

    for image_path in image_paths_90:
        if image_path in image_info_dict:
            save_adjusted_polygons(image_info_dict, image_path, polygon_field_to_rotate, 90)

    for image_path in image_paths_180:
        if image_path in image_info_dict:
            save_adjusted_polygons(image_info_dict, image_path, polygon_field_to_rotate, 180)

    save_updated_json(data, update_json_path)


def save_adjusted_polygons(image_info_dict, image_path, polygon_field_to_rotate, rotation_degree):
    image_info = image_info_dict[image_path]
    image = Image.open(image_path)
    width, height = image.size
    adjusted_polygons = adjust_polygons(image_info[polygon_field_to_rotate], width, height, rotation_degree)
    image_info[polygon_field_to_rotate] = adjusted_polygons
    print(f"Adjusted polygons for {image_path}: {adjusted_polygons}")


def save_updated_json(updated_data, update_json_path):
    json_path = update_json_path
    with open(json_path, 'w') as f:
        json.dump(updated_data, f, indent=4)
    print(f"Updated JSON file saved at {json_path}")


def main(is_check_responses):
    image_paths_90 = ["images/validation/1_segmented_Ear_toothpick_15_a.jpg",
                      "images/validation/1_segmented_Ear_toothpick_25_a.jpg",
                      "images/validation/1_segmented_Painkiller_21_a.jpg",
                      "images/validation/1_segmented_Painkiller_26_a.jpg",
                      "images/validation/2_segmented_Ear_toothpick_19_a.jpg",
                      "images/validation/2_segmented_Random_6 - Toothpaste_a.jpg",
                      "images/validation/3_segmented_Random_23 - Deodorant_a.jpg",
                      "images/validation/3_segmented_Screwdriver_5_a.jpg",
                      "images/validation/3_segmented_Screwdriver_8_a.jpg",
                      "images/validation/4_segmented_Random_3 - Plates_a.jpeg",
                      "images/validation/5_segmented_Painkiller_24_a.jpg",
                      "images/validation/5_segmented_Random_4 - Air freshener _a.jpeg",
                      "images/validation/5_segmented_Random_16 - Bathrobe_a.jpg",
                      "images/validation/6_segmented_Bottle_opener_46_a.jpg",
                      "images/validation/6_segmented_Ear_toothpick_24_a.jpg",
                      "images/validation/6_segmented_Food_containers__38_a.jpg",
                      "images/validation/6_segmented_Painkiller_27_a.jpg",
                      "images/validation/6_segmented_Random_10 - Fork_a.jpg",
                      "images/validation/6_segmented_Screwdriver_17_a.jpg",
                      "images/validation/7_segmented_Bottle_opener_36_a.jpg",
                      "images/validation/7_segmented_Random_11 - Lemon glass_a.jpg",
                      "images/validation/7_segmented_Screwdriver_12_a.jpg",
                      "images/validation/10_segmented_Food_containers__26_a.jpeg",
                      "images/validation/19_segmented_Food_containers__32_a.jpg"]
    image_paths_180 = ["images/validation/2_segmented_Random_8 - Camera_a.jpg",
                       "images/validation/12_segmented_Food_containers__27_a.jpg",
                       "images/validation/15_segmented_Painkiller_22_a.jpg",
                       "images/validation/16_segmented_Screwdriver_7_a.jpg"]

    if is_check_responses:
        json_file_path = "upwork_responses.json"
        image_path_field = "image_path"
        polygon_field_to_rotate = "chosen_polygon"
        update_json_path = "upwork_responses_rotate.json"
    else:
        json_file_path = "image_details_validation.json"
        image_path_field = 'image_path_html'
        polygon_field_to_rotate = 'containers_mask_polygon'
        update_json_path = "image_details_validation_new.json"

    process_images(json_file_path, image_path_field, polygon_field_to_rotate, update_json_path, image_paths_90,
                   image_paths_180)


if __name__ == '__main__':
    is_check_responses = True
    main(is_check_responses=is_check_responses)
