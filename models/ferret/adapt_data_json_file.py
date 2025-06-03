import json
import ast
from pathlib import Path
from PIL import Image

def convert_to_finetune_json(
    input_json_path: str,
    image_repo_dir: str,
    output_json_path: str
):
    # Load the source data
    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    finetune = []
    for idx, record in enumerate(data):
        image_name = record['image_path']
        chosen_item = record['chosen_item']
        poly_str = record['chosen_polygon']

        # 1) Load image to get size
        image_path = Path(image_repo_dir) / image_name
        with Image.open(image_path) as img:
            w, h = img.size

        # 2) Parse the polygon string
        try:
            poly = ast.literal_eval(poly_str)
        except Exception:
            poly = []

        # 3) Compute bbox [x1,y1,x2,y2]
        if poly and isinstance(poly, list) and all(isinstance(pt, (list,tuple)) for pt in poly):
            # xs = [pt[0] for pt in poly]
            # ys = [pt[1] for pt in poly]
            # bbox = [min(xs), min(ys), max(xs), max(ys)]
            # box_field = [[bbox], []]
            box_field = [poly, []]  # leave bbox as the original polygon
        else:
            # no polygon → both lists empty
            box_field = [[], []]

        # 4) Build the conversation
        human_prompt = (
            "<image>\n"
            f"In which drawer or cabinet door is a {chosen_item} stored?"
        )
        gpt_resp = "<bbox_location0>"

        entry = {
            "id": idx,
            "image": image_name,
            "image_h": h,
            "image_w": w,
            "conversations": [
                {"from": "human", "value": human_prompt},
                {"from": "gpt",   "value": gpt_resp}
            ],
            "box_x1y1x2y2": box_field
        }
        finetune.append(entry)

    # 5) Write out the fine-tuning JSON
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(finetune, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Example usage:
    convert_to_finetune_json(
        input_json_path   = "../../data/train_data/train_data_origin_filenames.json",
        image_repo_dir    = "../../images/sun_kitchen_images_original",
        output_json_path  = "ferret_finetune_train_data.json"
    )
