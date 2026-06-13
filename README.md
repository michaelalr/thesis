# Break Out the Silverware: Semantic Understanding of Stored Household Items

Official repository for the paper **"Break Out the Silverware: Semantic Understanding of Stored Household Items"**.

This project introduces the **Stored Household Item Challenge**, a benchmark for evaluating commonsense reasoning about the likely storage location of household items that are not visible (e.g., inside drawers or cabinets), and presents **NOAM (Non-visible Object Allocation Model)** — a structured vision-language pipeline for solving this task.

## Project Overview

Given:

* a kitchen scene image
* a queried household item

The goal is to predict the most likely storage container (drawer, cabinet, closet, etc.) where the item would be stored.

The repository includes:

1. **Data collection pipeline**
2. **Detection and feature extraction pipeline**
3. **NOAM semantic reasoning pipeline**
4. **Baseline model evaluations**
5. **Evaluation scripts**

---

## Repository Structure

### Dataset

Located under:

`/data`

Contains:

* **Development set (train)**
  Crowdsourced annotations based on SUN kitchen images (~6,500 item-image pairs).

* **Evaluation set (test)**
  Real-world kitchen images collected from participants (~100 item-image pairs).

---

### Images

Located under:

`/images`

Contains all kitchen scene images used throughout the project.

---

### Detection Pipeline

Located under:

`/detection`

This stage uses:

* Grounding-DINO
* SAM (Segment Anything)

to detect:

* drawers
* cabinet doors
* countertops
* anchor objects (sink, oven, dishwasher, etc.)

The output of this stage includes JSON files describing detected objects and their polygons.

⚠ **GPU required** for this stage.

---

### Feature Engineering

Located under:

`/containers_info_table`

This module contains the feature extraction process and multiple experimental iterations used to build the final structured container representation.

Features include:

* container type
* confidence score
* aspect ratio
* spatial relation to countertops
* neighboring containers
* neighboring anchor objects
* closest anchor relationships

The final output is the **containers_info_table**, which serves as input for all reasoning models.

---

### Models

Located under:

`/models`

Contains all model implementations evaluated in the paper.

#### NOAM (our method)

Located under:

`/models/chat-gpt`

NOAM converts structured container features into natural language descriptions and prompts LLMs to reason about likely storage locations.

Supported in the paper with:

* GPT-4
* LLaMA-3.3

---

#### Baseline Models

Other folders under `/models` contain baseline implementations used for comparison, including:

* Grounding-DINO
* Kosmos-2
* Gemini
* GPT-4o
* LLaMA-4
* Qwen-2.5

Each model’s output is parsed into a unified format for evaluation.

---

### Evaluation Scripts

Located under:

`/scripts`

Contains all scripts used for:

* parsing model outputs
* computing IoU
* calculating accuracy
* comparing model performance

Main evaluation script used for the paper:

`compare_responses.py`

This script generates the final benchmark results reported in the paper.

---

## Pipeline Flow

The full NOAM pipeline:

1. Input kitchen image
2. Detect visible containers and anchors
3. Extract structured spatial and semantic features
4. Convert features into natural language descriptions
5. Generate prompts for the LLM
6. Predict the most likely hidden storage location
7. Map predictions back to container polygons
8. Evaluate against ground truth using IoU and accuracy

---

## Requirements

Some parts of the project require:

* Python 3.10+
* OpenAI API key
* Together AI API key
* Google Gemini API key
* CUDA-enabled GPU (for detection)

---

## Citation

If you use this repository, please cite:

```bibtex
@inproceedings{levi_richter2026breakout,
  title={Break Out the Silverware: Semantic Understanding of Stored Household Items},
  author={Levi Richter, Michaela and Mirsky, Reuth and Glickman, Oren},
  booktitle={ICPR},
  year={2026}
}
```
