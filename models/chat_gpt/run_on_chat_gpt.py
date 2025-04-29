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
def ask_chatgpt(containers, item):
    system_prompt = """
    You are a helpful assistant that determines the most likely storage container for household items in a kitchen.
    Containers are described in natural language. Given a specific item, select the most appropriate container, or say that none are suitable.
    
    Format:
    Item: [Name]
    Best container: [just container id or "None"]
    Reasoning: [short explanation]
    
    ### Example 1
    Item: Knife  
    Containers:
    - Container id 1, is a "cabinet door" below the countertop.  
    - Container id 2, is a "drawer" below the countertop.  
    - Container id 3, is a "cabinet door" above the countertop.
    
    Item: Knife
    Best container: 2  
    Reasoning: Knives are typically stored in drawers for safety and accessibility.
    
    ### Example 2
    Item: Trash Bag  
    Containers:
    - Container id 1, is a "cabinet door" under the sink.  
    - Container id 2, is a "cabinet door" above the stove.
    
    Item: Trash Bag
    Best container: 1  
    Reasoning: Trash bags are commonly stored under the sink where the trash can is.
    
    ### Example 3  
    Item: Winter Coat  
    Containers:
    - Container id 1, is a "drawer" below the countertop.  
    - Container id 2, is a "cabinet door" below the sink.
    
    Item: Winter Coat
    Best container: None  
    Reasoning: A winter coat would not be stored in kitchen storage like drawers or cabinets.

    Now do the same for the following item and containers.
    """.strip()

    user_prompt = f"Item: {item}\nContainers:\n" + "\n".join(f"- {desc}" for desc in containers)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
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
        for item in items:
            print(f"Processing {image_path} - {item}")
            try:
                result = ask_chatgpt(containers, item)
                results.append({
                    "image_path": image_path,
                    "item": item,
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
    csv_path = "../../short_id_pos_lab_anchors_with_description.csv"
    json_path = "../../image_details/image_to_items_dict.json"
    chatgpt_output = "./chatgpt_results_short_id_pos_lab_anchors.csv"
    run_queries_in_chat_gpt(csv_path=csv_path, json_path=json_path, chatgpt_output=chatgpt_output)
