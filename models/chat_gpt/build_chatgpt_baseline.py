import json
import os
import time

from openai import OpenAI

# Set your API key using the new client
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def build_chatgpt_baseline(json_path, chatgpt_output):
    # Load the JSON file
    with open(json_path, 'r') as f:
        image_items_dict = json.load(f)

    # Store the results
    results = {}

    # Loop through images
    for image_url, items in image_items_dict.items():
        # Build the prompt
        prompt = (
                f"You are analyzing a kitchen image from the following URL: {image_url}\n"
                f"The visible containers are drawers and cabinet doors.\n"
                f"The items to store are:\n"
                + "\n".join(f"- {item}" for item in items) +
                "\n\nFor each item, determine the most likely storage location among visible drawers and cabinet doors only."
                "\nReturn 4 bounding box coordinates per item in this format: [[xmin,ymin],[xmin,ymax],[xmax,ymax],[xmax,ymin]]."
                "\nIf you cannot determine a suitable location, output []."
                "\nOnly output the list of bounding boxes in the same order as the input items."
                "\nDo not output anything else."
        )

        try:
            # Send the prompt to the ChatGPT API
            response = client.chat.completions.create(
                model="gpt-4-vision",  # Use GPT-4 with vision capabilities
                messages=[{"role": "user", "content": prompt}],
                temperature=0  # for deterministic output
            )

            reply = response.choices[0].message.content

            # Save the reply mapped to the image URL
            results[image_url] = {
                "items": items,
                "bboxes": json.loads(reply)  # try parsing it as a list
            }

            print(f"Processed {image_url}")

        except Exception as e:
            print(f"Error processing {image_url}: {e}")
            results[image_url] = {
                "items": items,
                "bboxes": None,
                "error": str(e)
            }

        # Optional: slight delay to avoid hitting rate limits
        time.sleep(1)

    # Save results to a new JSON
    with open(chatgpt_output, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Finished processing all images. Results saved to {chatgpt_output}")


if __name__ == '__main__':
    # Load data
    json_path = "../../image_details/image_details_git_check.json"
    chatgpt_output = "./chatgpt_baseline.json"
    build_chatgpt_baseline(json_path=json_path, chatgpt_output=chatgpt_output)
