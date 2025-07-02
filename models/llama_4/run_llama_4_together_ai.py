import base64
import json
import os

from together import Together

# Set your API key using the new client
client = Together()


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def build_llama_4_response(json_path, chatgpt_output):
    # Load the JSON file
    with open(json_path, 'r') as f:
        image_items_dict = json.load(f)

    # Store the results
    results = {}

    # Loop through images
    for image_url, items in image_items_dict.items():
        image_path = os.path.normpath(os.path.join("..", image_url))

        # Getting the Base64 string
        base64_image = encode_image(image_path)

        # Initialize the dict for this image
        results[image_url] = []

        for item in items:
            # Build the prompt per item
            prompt = (
                "You are analyzing a kitchen image.\n"
                "The visible containers are drawers and cabinet doors.\n"
                f"The item to store is:\n- {item}\n\n"
                "Determine the most likely storage location among visible drawers and cabinet doors only.\n"
                "Return a list of 4-point bounding box coordinates for the item.\n"
                "If a suitable location cannot be determined, return an empty list [].\n"
                "Only return the bounding box list, nothing else."
            )

            try:
                # Query image with Llama 4 Maverick model
                response = client.chat.completions.create(
                    # model="meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
                    model="Qwen/Qwen2.5-VL-72B-Instruct",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url",
                             "image_url": {
                                 "url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }]
                )

                result = response.choices[0].message.content

                # Append the item and its bbox result
                results[image_url].append({
                    "item": item,
                    "bbox": result
                })

                print(f"Processed {image_url} - {item}")

            except Exception as e:
                print(f"Error processing {image_url} - {item}: {e}")
                results[image_url].append({
                    "item": item,
                    "bbox": None,
                    "error": str(e)
                })

    # Save results to a new JSON
    with open(chatgpt_output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Finished processing all images. Results saved to {chatgpt_output}")


if __name__ == '__main__':
    # Load data
    json_path = "../../image_details/image_to_items_dict_test_kitchen_origin_images.json"
    llama_output = "./qwen_2.5_test_origin_images.json"
    build_llama_4_response(json_path=json_path, chatgpt_output=llama_output)
