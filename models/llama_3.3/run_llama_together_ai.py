from together import Together

import json
from collections import defaultdict
from openai import OpenAI
import pandas as pd
import os
import re


# Prepare and call Together API
def ask_together(containers, item):
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
        model=model_to_run,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content


def run_queries_in_together(csv_path, json_path, together_output):
    df = pd.read_csv(csv_path)

    with open(json_path, 'r') as f:
        items_dict = json.load(f)

    # Normalize paths for comparison
    def normalize_filename(path):
        # filename = os.path.basename(path)
        # # Remove "X_segmented_" prefix using regex
        # filename = re.sub(r'^\d+_segmented_', '', filename)
        # # Replace double underscores with single underscores for matching
        # filename = filename.replace('__', '_')
        # return filename
        return path.replace("../", "")

    # Reverse items_dict to map to CSV-style paths
    normalized_items_dict = {
        normalize_filename(k): v for k, v in items_dict.items()
    }

    # Group containers by image
    containers_by_image = defaultdict(list)
    for _, row in df.iterrows():
        norm_filename = normalize_filename(row['image_path_html'])
        containers_by_image[norm_filename].append(row['description'])

    # Loop through each image and ask
    results = []
    for image_path, containers in containers_by_image.items():
        items = normalized_items_dict.get(image_path, [])
        if not items:
            continue  # Skip if no items mapped
        for item in items:
            print(f"Processing {image_path} - {item}")
            try:
                result = ask_together(containers, item)
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
    output_df.to_csv(together_output, index=False)
    print(f"Done! Results saved to {together_output}")


if __name__ == '__main__':
    model = "llama"

    if model == "llama":
        client = Together()
        model_to_run = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
    else:  # model == "gpt":
        client = OpenAI(
            # This is the default and can be omitted
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
        model_to_run = "gpt-4"

    # Load data
    csv_path = "../../containers_info_table/train_info_table_versions/short_id_pos_lab_anchrs_ratio_with_description.csv"
    json_path = "../../image_details/image_to_items_dict_missing_llama.json"
    together_output = f"./{model}_results_missing_llama.csv"
    run_queries_in_together(csv_path=csv_path, json_path=json_path, together_output=together_output)
