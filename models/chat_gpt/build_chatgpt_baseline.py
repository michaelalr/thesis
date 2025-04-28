import json
import os
import time
import base64
from openai import OpenAI

# Set your API key using the new client
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def parse_response(result):
    items_and_containers = []

    # Clean the response
    clean_response = result.replace('```', '').strip()

    for line in clean_response.split("\n"):
        line = line.strip()
        if not line or line == "[]" or line == "[ ]":  # skip garbage lines
            continue
        try:
            if ":" in line:
                item_part, polygon_part = line.split(":", 1)  # safer split
                item_name = item_part.strip().lstrip("-").strip()
                polygon_str = polygon_part.strip()
                items_and_containers.append({item_name: polygon_str})
            else:
                print(f"Skipped line (no colon): {line}")
        except Exception as e:
            print(f"Failed to parse line: {line}, error: {e}")

    return items_and_containers

def build_chatgpt_baseline(json_path, chatgpt_output):
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

        # Build the prompt
        prompt = (
                "You are analyzing a kitchen image.\n"
                "The visible containers are drawers and cabinet doors.\n"
                "The items to store are:\n"
                + "\n".join(f"- {item}" for item in items) +
                "\n\nFor each item, determine the most likely storage location among visible drawers and cabinet doors only."
                "\nReturn 4 bounding box coordinates per item in this format: [[117,290],[117,348],[167,348],[168,320]]."
                "\nIf you cannot determine a suitable location for an item, output [] for it."
                "\nOnly output the list of bounding boxes per item."
        )

        try:
            # Send the prompt to the ChatGPT API
            response = client.responses.create(
                model="gpt-4o",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        ],
                    }
                ],
            )

            result = response.output_text

            # Save the reply mapped to the image URL
            items_and_containers = parse_response(result)
            results[image_url] = items_and_containers

            print(f"Processed {image_url}")

        except Exception as e:
            print(f"Error processing {image_url}: {e}")
            results[image_url] = {
                "items": items,
                "bboxes": None,
                "error": str(e)
            }
            # if "Error code: 429" in e:
            #     print("break running...")
            #     break

        # Optional: slight delay to avoid hitting rate limits
        time.sleep(1)

    # Save results to a new JSON
    with open(chatgpt_output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Finished processing all images. Results saved to {chatgpt_output}")


if __name__ == '__main__':
    # Load data
    json_path = "../../image_details/image_details_check.json"
    chatgpt_output = "./chatgpt_baseline.json"
    build_chatgpt_baseline(json_path=json_path, chatgpt_output=chatgpt_output)
