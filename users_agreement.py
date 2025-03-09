import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon


# Function to load JSON files
def load_responses(user_files):
    responses = {}
    for file in user_files:
        with open(file, 'r') as f:
            user_data = json.load(f)
            for entry in user_data:
                user_id = entry.get('user_id')
                if user_id is not None:
                    if user_id not in responses:
                        responses[user_id] = []
                    responses[user_id].append(entry)
    return responses


# Function to compute the IoU (Intersection over Union) for polygons
def compute_iou(polygon1, polygon2):
    poly1 = Polygon(np.array(polygon1))
    poly2 = Polygon(np.array(polygon2))

    if not poly1.is_valid or not poly2.is_valid:
        return 0.0

    if poly1.is_empty and poly2.is_empty:
        return 1

    intersection = poly1.intersection(poly2).area
    union = poly1.union(poly2).area
    return intersection / union


# Function to extract the filename from the image_path
def extract_filename(image_path):
    return os.path.basename(image_path)


# Function to compare users' responses for agreement
def compare_responses(responses):
    user_ids = list(responses.keys())
    results = {}

    for i in range(len(user_ids)):
        for j in range(i + 1, len(user_ids)):
            user1_data = responses[user_ids[i]]
            user2_data = responses[user_ids[j]]

            agreements = 0
            total_comparisons = 0

            # Compare all responses for same image_path and chosen_item
            for response1 in user1_data:
                for response2 in user2_data:
                    filename1 = extract_filename(response1['image_path'])
                    filename2 = extract_filename(response2['image_path'])

                    if filename1 == filename2 and response1['chosen_item'] == response2['chosen_item']:
                        total_comparisons += 1
                        iou = compute_iou(json.loads(response1['chosen_polygon']),
                                          json.loads(response2['chosen_polygon']))
                        if iou > 0.5:  # threshold for considering agreement
                            agreements += 1

            agreement_percentage = (agreements / total_comparisons) * 100 if total_comparisons > 0 else 0
            results[(user_ids[i], user_ids[j])] = agreement_percentage

    return results


# Function to compute the agreement across different items
def agreement_by_item(responses):
    item_agreements = defaultdict(list)

    # Compare responses across all users for the same item and image
    user_ids = list(responses.keys())
    for i in range(len(user_ids)):
        for j in range(i + 1, len(user_ids)):
            user1_data = responses[user_ids[i]]
            user2_data = responses[user_ids[j]]

            for response1 in user1_data:
                for response2 in user2_data:
                    filename1 = extract_filename(response1['image_path'])
                    filename2 = extract_filename(response2['image_path'])
                    item1 = response1['chosen_item']
                    item2 = response2['chosen_item']
                    if item1 == item2 and filename1 == filename2:
                        iou = compute_iou(json.loads(response1['chosen_polygon']),
                                          json.loads(response2['chosen_polygon']))
                        if iou > 0.5:  # threshold for considering agreement
                            item_agreements[item1].append(1)
                        else:
                            item_agreements[item1].append(0)

    # Calculate average agreement for each item
    avg_item_agreements = {item: (sum(agreements) / len(agreements)) * 100 for item, agreements in
                           item_agreements.items()}

    return avg_item_agreements


# Function to visualize the agreement across different items
def visualize_item_agreement(item_agreements):
    sorted_items = sorted(item_agreements.items(), key=lambda x: x[1], reverse=True)
    items = [item[0] for item in sorted_items]
    agreement_percentages = [item[1] for item in sorted_items]

    plt.bar(items, agreement_percentages)
    plt.xlabel('Item')
    plt.ylabel('Average Agreement (%)')
    plt.title('Agreement Across Different Items')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()


def visualize_agreement(results, user_pairs, agreement_percentages):
    # Create a list of labels with user_id pairs
    # labels = [f"User {user_pair[0]} vs User {user_pair[1]}" for user_pair in user_pairs]
    labels = [f"{user_pair[0]} vs {user_pair[1]}" for user_pair in user_pairs]
    # Create a bar chart
    plt.bar(range(len(results)), agreement_percentages, tick_label=labels)
    plt.xlabel('User Pair')
    plt.ylabel('Agreement Percentage')
    plt.title('Agreement between User Responses')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def dist_agreement_prcnt(agreement_percentages):
    plt.hist(agreement_percentages, bins=10, edgecolor='black')
    plt.xlabel('Agreement Percentage')
    plt.ylabel('Frequency')
    plt.title('Distribution of Agreement Percentages')
    plt.show()


def disagreement_prcnt(agreement_percentages):
    disagreement_percentages = [100 - agreement for agreement in agreement_percentages]
    plt.hist(disagreement_percentages, bins=10, edgecolor='black')
    plt.xlabel('Disagreement Percentage')
    plt.ylabel('Frequency')
    plt.title('Distribution of Disagreement Percentages')
    plt.show()


# Function to visualize the agreement results with user_id on the bars
def visualize_results(results):
    user_pairs = list(results.keys())
    agreement_percentages = list(results.values())

    visualize_agreement(results, user_pairs, agreement_percentages)
    dist_agreement_prcnt(agreement_percentages)
    disagreement_prcnt(agreement_percentages)


# List of response files for each user
user_files = [
    'responses/user_responses_test_asaf.json',
    'responses/user_responses_test_lee_or.json',
    'responses/user_responses_test_lior.json',
    'responses/user_responses_test_michaela_2.json',
    'responses/user_responses_test_oren.json',
    'responses/user_responses_test_ronny.json',
    'responses/user_responses_test_saggie.json',
    'responses/user_responses_test_shabi.json'
]
user_files = ['cleaned_responses.json']
# Load responses from the files
responses = load_responses(user_files)

# Compare responses and calculate agreement
agreement_results = compare_responses(responses)
# Calculate agreement across different items
item_agreements = agreement_by_item(responses)
# Sort results for user pair agreement
sorted_agreement_results = dict(sorted(agreement_results.items(), key=lambda item: item[1], reverse=True))
sorted_item_agreement_results = dict(sorted(item_agreements.items(), key=lambda item: item[1], reverse=True))

# Print the results in a table
print("User Pair Agreement (%)")
for pair, agreement in sorted_agreement_results.items():
    print(f"User {pair[0]} vs User {pair[1]}: {agreement:.2f}%")

# Visualize the agreement results
visualize_results(sorted_agreement_results)

# Print and visualize agreement across different items
print("\nAgreement Across Different Items:")
for item, agreement in sorted_item_agreement_results.items():
    print(f"{item}: {agreement:.2f}%")

# Visualize the agreement across different items
visualize_item_agreement(sorted_item_agreement_results)
