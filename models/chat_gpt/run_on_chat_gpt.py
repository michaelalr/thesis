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
    You are helping locate a household item in a kitchen.
    The item is stored in one of several visible containers (e.g., drawers, cabinets), but I don't know which.
    I’ll provide a list of container descriptions and the item name.
    Your task is to identify the most likely container based on typical kitchen organization. If none are suitable, return "None".

    Response format:
    Item: [Name]  
    Best container: [Container ID or "None"]  
    Reasoning: [Short explanation]

    ### Example 1
    Item: Fork  
    Containers:  
    - Container 1: cabinet door below the countertop, located to the right of the dishwasher.  
    - Container 2: below the countertop, located to the left of the dishwasher.  
    - Container 3: cabinet door above the countertop, located above the coffee machine.  
    - Container 4: drawer below the countertop.  
    - Container 5: cabinet door above the countertop.  
    - Container 6: cabinet door above the countertop.  

    Item: Fork  
    Best container: 4  
    Reasoning: Forks are usually stored in drawers below the countertop for easy access.

    ### Example 2
    Item: Trash Bag  
    Containers:  
    - Container 1: cabinet door above the countertop.  
    - Container 2: drawer below the countertop.  
    - Container 3: cabinet door below the countertop, located below the sink.  

    Item: Trash Bag  
    Best container: 3  
    Reasoning: Trash bags are commonly stored under the sink near the trash can.

    ### Example 3
    Item: Knife  
    Containers:  
    - Container 1: cabinet door.  
    - Container 2: drawer, located below the electronic kettle, above the oven, at the bottom-right of the refrigerator, and at the bottom-left of the dish drying rack.  
    - Container 3: cabinet door, located below the dishwasher.  

    Item: Knife  
    Best container: 2  
    Reasoning: Knives are typically stored in drawers for safety and accessibility.

    ### Example 4
    Item: Baking pan  
    Containers:  
    - Container 1: drawer below the countertop, located at the bottom-right of the oven, and at the top-right of the electronic kettle.  
    - Container 2: cabinet door below the countertop, located to the right of the electronic kettle, and at the bottom-right of the oven.  
    - Container 3: cabinet door below the countertop, located below the stove.  
    - Container 4: below the countertop.  
    - Container 5: cabinet door below the countertop, located to the left of the electronic kettle, and at the bottom-left of the oven.  

    Item: Baking pan  
    Best container: 5  
    Reasoning: Baking pans are stored in cabinets below the countertop near the oven.

    Now respond to the following:
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
                # if "Error code: 429" in e:
                #     print("break running...")
                #     break

    # Save results to a file
    output_df = pd.DataFrame(results)
    output_df.to_csv(chatgpt_output, index=False)
    print(f"Done! Results saved to {chatgpt_output}")


if __name__ == '__main__':
    # Load data
    csv_path = "../../short_id_pos_lab_anchrs_ratio_most_with_description.csv"
    json_path = "../../image_details/image_to_items_dict.json"
    chatgpt_output = "./chatgpt_results_short_id_pos_lab_anchrs_ratio_most.csv"
    run_queries_in_chat_gpt(csv_path=csv_path, json_path=json_path, chatgpt_output=chatgpt_output)
