import json
import os
import re

import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from PIL import ImageDraw
from transformers import AutoProcessor, Kosmos2ForConditionalGeneration

from compare_responses import clean_image_path


def plot_image_with_bbox(entities, image, image_path, chosen_item, output_folder):
    # Make a copy so we don't modify the original
    image = image.copy()

    # Draw bounding boxes if entities exist
    if entities:
        draw = ImageDraw.Draw(image)
        for entity in entities:
            label, (start_x, start_y), bbox = entity
            print(f"Object: {label}, Bounding Box (normalized): {bbox}")

            # Convert normalized bbox to pixel coordinates
            x_min, y_min, x_max, y_max = bbox[0]
            width, height = image.size
            x_min = int(x_min * width)
            y_min = int(y_min * height)
            x_max = int(x_max * width)
            y_max = int(y_max * height)

            # Ensure proper ordering for drawing
            x_min, x_max = sorted([x_min, x_max])
            y_min, y_max = sorted([y_min, y_max])

            draw.rectangle([x_min, y_min, x_max, y_max], outline="red", width=3)

    # Extract filename and add prefix
    original_filename = os.path.basename(image_path)
    output_filename = f"kosmos_{chosen_item}_{original_filename}"

    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    save_path = os.path.join(output_folder, output_filename)

    # Save image
    image.save(save_path)
    print(f"Saved image with bounding boxes to: {save_path}")

    # Optionally display image
    plt.imshow(image)
    plt.axis("off")
    plt.show()


def run_kosmos_on_image(model, processor, image_path, chosen_item, output_folder):
    image = Image.open(image_path)
    prompt = f"<grounding> In which<phrase> drawer</phrase> or<phrase> cabinet door</phrase> is<phrase> a {chosen_item}</phrase> stored?"

    inputs = processor(text=prompt, images=image, return_tensors="pt")

    generated_ids = model.generate(
        pixel_values=inputs["pixel_values"],
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        image_embeds=None,
        image_embeds_position_mask=inputs["image_embeds_position_mask"],
        use_cache=True,
        max_new_tokens=128,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

    # Specify `cleanup_and_extract=False` in order to see the raw model generation.
    processed_text = processor.post_process_generation(generated_text, cleanup_and_extract=False)

    # By default, the generated  text is cleanup and the entities are extracted.
    caption, entities = processor.post_process_generation(generated_text)

    plot_image_with_bbox(entities=entities, image=image, image_path=image_path, chosen_item=chosen_item,
                         output_folder=output_folder)

    print(caption)

    return caption, entities


def change_image_path(image_path, train_or_test):
    img_folder_path = '/dsi/scratch/home/dsi/glikmao/SUN397/k/kitchen/' if train_or_test == "train" else "/dsi/dsai-lab/michaela.lr/thesis/organized_images/a/"

    filename = os.path.basename(image_path)  # Get only the filename
    filename = re.sub(r"^\d+_", "", filename)  # Remove leading numbers + underscore
    filename = re.sub(r"^segmented_", "", filename)  # Remove "segmented_" if present

    new_image_path = os.path.join(img_folder_path, filename)
    print(new_image_path)
    return new_image_path


def create_kosmos_2_responses(model, processor, train_or_test_data_json, output_folder, train_or_test="train",
                              is_linux=False):
    # Load image details
    with open(train_or_test_data_json, "r") as f:
        image_details = json.load(f)

    kosmos_2_responses = []

    print("start images")

    # Iterate over image details
    for entry in image_details:
        new_image_path = change_image_path(entry["image_path"], train_or_test) if is_linux else clean_image_path(
            entry["image_path"])
        chosen_item = entry["chosen_item"]
        caption, entities = run_kosmos_on_image(model=model, processor=processor, image_path=new_image_path,
                                                chosen_item=chosen_item, output_folder=output_folder)

        # Create response entry
        if train_or_test == "train":
            response_entry = {
                "image_path": entry["image_path"],
                "new_image_path": new_image_path,
                "containers_polygons": entry["containers_polygons"],
                "caption": str(caption),
                "entities": str(entities),
                "chosen_item": entry["chosen_item"],
                "room_type": entry["room_type"]
            }
        else:
            response_entry = {
                "image_path": entry["image_path"],
                "new_image_path": new_image_path,
                "containers_polygons": entry["containers_polygons"],
                "caption": str(caption),
                "entities": str(entities),
                "chosen_item": entry["chosen_item"]
            }
        kosmos_2_responses.append(response_entry)

    print("done images")

    # Create the new DataFrame
    kosmos_df = pd.DataFrame(kosmos_2_responses)
    file_name = "kosmos_2_" + train_or_test + "_responses"

    # Save to CSV file
    kosmos_df.to_csv(file_name + ".csv", index=False)

    # Save to JSON file
    with open(file_name + ".json", "w") as f:
        json.dump(kosmos_2_responses, f, indent=4)

    print("Kosmos-2 " + train_or_test + " responses CSV and JSON generated successfully!")


def main():
    # Load model and processor
    model = Kosmos2ForConditionalGeneration.from_pretrained("microsoft/kosmos-2-patch14-224")
    processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")

    print("model and processor loaded")
    output_folder = "/dsi/dsai-lab/michaela.lr/kosmos2/kosmos_test_output/"
    train_or_test_data_json = "test_data.json"
    train_or_test = "test"

    is_linux = False

    create_kosmos_2_responses(model=model, processor=processor, train_or_test_data_json=train_or_test_data_json,
                              output_folder=output_folder, train_or_test=train_or_test, is_linux=is_linux)


if __name__ == '__main__':
    main()
