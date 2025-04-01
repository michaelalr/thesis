import json

import matplotlib.pyplot as plt
from PIL import Image
from PIL import ImageDraw
from transformers import AutoProcessor, Kosmos2ForConditionalGeneration

from compare_responses import clean_image_path


def plot_image_with_bbox(entities, image):
    # If entities exist, extract the bounding box and draw it
    if entities:
        for entity in entities:
            # Extract the bounding box coordinates (normalized format)
            label, (start_x, start_y), bbox = entity
            print(f"Object: {label}, Bounding Box (normalized): {bbox}")

            # Convert normalized bbox to pixel coordinates
            x_min, y_min, x_max, y_max = bbox[0]
            width, height = image.size
            x_min = int(x_min * width)
            y_min = int(y_min * height)
            x_max = int(x_max * width)
            y_max = int(y_max * height)

            # Draw the bounding box on the image
            draw = ImageDraw.Draw(image)
            draw.rectangle([x_min, y_min, x_max, y_max], outline="red", width=3)

    # Display image with bounding box
    plt.imshow(image)
    plt.axis("off")
    plt.show()


def run_kosmos_on_image(model, processor, image_path, chosen_item):
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

    # plot_image_with_bbox(entities=entities, image=image)

    return caption, entities


def create_random_baseline(model, processor, train_or_test_data_json, train_or_test="train"):
    # Load image details
    with open(train_or_test_data_json, "r") as f:
        image_details = json.load(f)

    kosmos_2_responses = []

    # Iterate over image details
    for entry in image_details:
        cleaned_path = clean_image_path(entry["image_path"])
        chosen_item = entry["chosen_item"]
        caption, entities = run_kosmos_on_image(model=model, processor=processor, image_path=cleaned_path,
                                                chosen_item=chosen_item)

        # Create response entry
        if train_or_test == "train":
            response_entry = {
                "image_path": entry["image_path"],
                "containers_polygons": entry["containers_polygons"],
                "caption": str(caption),
                "entities": str(entities),
                "chosen_item": entry["chosen_item"],
                "room_type": entry["room_type"]
            }
        else:
            response_entry = {
                "image_path": entry["image_path"],
                "containers_polygons": entry["containers_polygons"],
                "caption": str(caption),
                "entities": str(entities),
                "chosen_item": entry["chosen_item"]
            }
        kosmos_2_responses.append(response_entry)

    # Save to JSON file
    file_name = "kosmos_2_" + train_or_test + "_responses.json"
    with open(file_name, "w") as f:
        json.dump(kosmos_2_responses, f, indent=4)

    print("Kosmos-2 " + train_or_test + " responses JSON generated successfully!")


def main():
    # Load model and processor
    model = Kosmos2ForConditionalGeneration.from_pretrained("microsoft/kosmos-2-patch14-224")
    processor = AutoProcessor.from_pretrained("microsoft/kosmos-2-patch14-224")

    train_or_test_data_json = "train_data.json"
    train_or_test = "train"

    create_random_baseline(model=model, processor=processor, train_or_test_data_json=train_or_test_data_json,
                           train_or_test=train_or_test)


if __name__ == '__main__':
    main()
