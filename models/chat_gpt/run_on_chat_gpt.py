import json
from collections import defaultdict

import openai
import pandas as pd
import os
from openai import OpenAI

# Set your API key using the new client
client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Prepare and call ChatGPT API
def ask_chatgpt(image_path, containers, items):
    prompt = f"""You are a service robot in a domestic environment. You are now looking at a kitchen scene.

The containers (drawers, cabinet doors etc.) detected in the image are:
{chr(10).join(f"- {desc}" for desc in containers)}

For each of the following items:
{', '.join(items)}

Please determine in which container each item is most likely to be stored. If no container is suitable, say so. Provide reasoning for each item.

Format:
Item: [Name]
Best container: [just container id or "None"]
Reasoning: [Your explanation]
"""

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-4-turbo"
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content


def run_queries_in_chat_gpt(csv_path, json_path, chatgpt_output):
    df = pd.read_csv(csv_path)

    with open(json_path, 'r') as f:
        items_dict = json.load(f)

    # Normalize paths for comparison
    def normalize_path(path):
        return path.replace("../", "")

    # Reverse items_dict to map to CSV-style paths
    normalized_items_dict = {
        normalize_path(k): v for k, v in items_dict.items()
    }

    # Group containers by image
    containers_by_image = defaultdict(list)
    for _, row in df.iterrows():
        containers_by_image[row['image_path_html']].append(row['description'])

    # Loop through each image and ask
    results = []
    for image_path, containers in containers_by_image.items():
        items = normalized_items_dict.get(image_path, [])
        if not items:
            continue  # Skip if no items mapped

        print(f"Processing {image_path}...")

        try:
            result = ask_chatgpt(image_path, containers, items)
            results.append({
                "image_path": image_path,
                "items": items,
                "response": result
            })
        except Exception as e:
            print(f"Error for {image_path}: {e}")
            if "Error code: 429" in e:
                print("break running...")
                break

    # Save results to a file
    output_df = pd.DataFrame(results)
    output_df.to_csv(chatgpt_output, index=False)
    print(f"Done! Results saved to {chatgpt_output}")


if __name__ == '__main__':
    # Load data
    csv_path = "../../labeled_containers_with_description.csv"
    json_path = "../../image_details/image_to_items_dict.json"
    chatgpt_output = "./chatgpt_reasoning_results_2.csv"
    run_queries_in_chat_gpt(csv_path=csv_path, json_path=json_path, chatgpt_output=chatgpt_output)
