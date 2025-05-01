import json
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import linkage, dendrogram
from shapely.geometry import Polygon, Point, LineString


def load_json(filepath):
    """ Load JSON file and return the data """
    with open(filepath, "r") as f:
        return json.load(f)


# Function to load JSON files
def load_responses(user_files):
    responses = {}
    for file in user_files:
        user_data = load_json(file)
        for entry in user_data:
            user_id = entry.get('user_id')
            if user_id is not None:
                if user_id not in responses:
                    responses[user_id] = []
                responses[user_id].append(entry)
    return responses


def compute_iou(polygon1, polygon2):
    """Compute the IoU (Intersection over Union) between two geometries."""

    # Convert input lists to Shapely geometries based on their length
    def to_geometry(coords):
        if len(coords) == 1:  # Single point
            return Point(coords[0])
        elif len(coords) == 2:  # Line (2 points)
            return LineString(coords)
        else:  # Polygon (3 or more points)
            return Polygon(coords)

    poly1 = to_geometry(np.array(polygon1))
    poly2 = to_geometry(np.array(polygon2))

    # Handle invalid cases
    if not poly1.is_valid or not poly2.is_valid:
        return 0.0

    # If both are empty, consider them fully overlapping
    if poly1.is_empty and poly2.is_empty:
        return 1.0

    # === Handle Point vs. Point ===
    if isinstance(poly1, Point) and isinstance(poly2, Point):
        return 1.0 if poly1.equals(poly2) else 0.0

    # === Handle LineString vs. LineString ===
    if isinstance(poly1, LineString) and isinstance(poly2, LineString):
        if poly1.equals(poly2):  # Identical lines
            return 1.0
        intersection_length = poly1.intersection(poly2).length
        total_length = poly1.length + poly2.length - intersection_length
        return intersection_length / total_length if total_length > 0 else 0.0

    # === Handle Point vs. LineString ===
    if isinstance(poly1, Point) and isinstance(poly2, LineString):
        return 1.0 if poly2.contains(poly1) else 0.0
    if isinstance(poly2, Point) and isinstance(poly1, LineString):
        return 1.0 if poly1.contains(poly2) else 0.0

    # === Handle Polygon vs. Point ===
    if isinstance(poly1, Polygon) and isinstance(poly2, Point):
        return 1.0 if poly1.contains(poly2) else 0.0
    if isinstance(poly2, Polygon) and isinstance(poly1, Point):
        return 1.0 if poly2.contains(poly1) else 0.0

    # === Handle Polygon vs. LineString ===
    if isinstance(poly1, Polygon) and isinstance(poly2, LineString):
        if poly1.contains(poly2):  # Line fully inside polygon
            return 1.0
        intersection_length = poly1.intersection(poly2).length
        return intersection_length / poly2.length if poly2.length > 0 else 0.0

    if isinstance(poly2, Polygon) and isinstance(poly1, LineString):
        if poly2.contains(poly1):
            return 1.0
        intersection_length = poly1.intersection(poly2).length
        return intersection_length / poly1.length if poly1.length > 0 else 0.0

    # === Handle Polygon vs. Polygon (Default IoU Calculation) ===
    intersection = poly1.intersection(poly2).area
    union = poly1.union(poly2).area
    # return intersection / union if poly1.intersects(poly2) else 0
    return intersection / union if union > 0 else 0.0


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
                        # if iou > 0.5:  # threshold for considering agreement
                        if iou >= 1:  # threshold for considering agreement
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
                        # if iou > 0.5:  # threshold for considering agreement
                        if iou >= 1:  # threshold for considering agreement
                            item_agreements[item1].append(1)
                        else:
                            item_agreements[item1].append(0)

    # Calculate average agreement for each item
    avg_item_agreements = {item: (sum(agreements) / len(agreements)) * 100 for item, agreements in
                           item_agreements.items()}

    return avg_item_agreements


# Function to visualize the agreement across different items
def visualize_item_agreement(item_agreements, user_id=""):
    sorted_items = sorted(item_agreements.items(), key=lambda x: x[1], reverse=True)
    items = [item[0] for item in sorted_items]
    agreement_percentages = [item[1] for item in sorted_items]

    plt.bar(items, agreement_percentages)
    plt.xlabel('Item')
    plt.ylabel('Average Agreement (%)')
    title = f'Agreement Across Different Items - User {user_id}' if user_id != "" else "Agreement Across Different Items"
    plt.title(title)
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


# Function to visualize the mean agreement between human users and random responses
def visualize_mean_agreement(df):
    mean_agreement_per_user = df.groupby('human_user_id')['agreement_score'].mean()

    # Print mean agreement for each user
    print("Mean Agreement Between Each Human User and Random:")
    print(mean_agreement_per_user)

    # Visualize mean agreement
    plt.figure(figsize=(12, 6))
    sns.barplot(x=mean_agreement_per_user.index, y=mean_agreement_per_user.values)
    plt.title('Mean Agreement Score per Human User')
    plt.xlabel('User ID')
    plt.ylabel('Mean Agreement Score (IoU)')
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


def agreement_over_time(df):
    df['datetime'] = pd.to_datetime(df['datetime'])
    df_time_grouped = df.groupby(df['datetime'].dt.date).size()

    plt.figure(figsize=(10, 6))
    plt.plot(df_time_grouped.index, df_time_grouped.values, marker='o', linestyle='-')
    plt.xlabel("Date")
    plt.ylabel("Number of Responses")
    plt.title("User Responses Over Time")
    plt.xticks(rotation=45)
    plt.grid()
    plt.show()


def agreement_per_user(agreement_results):
    user_agreements = {}

    # Compute each user's average agreement across all their comparisons
    for (user1, user2), agreement in agreement_results.items():
        user_agreements[user1] = user_agreements.get(user1, []) + [agreement]
        user_agreements[user2] = user_agreements.get(user2, []) + [agreement]

    # Average the agreement per user
    user_agreements = {user: sum(agreements) / len(agreements) for user, agreements in user_agreements.items()}

    print("\nAgreement Per User:")
    for user, agreement in sorted(user_agreements.items(), key=lambda item: item[1], reverse=True):
        print(f"User {user}: {agreement:.2f}%")

    # Visualize
    visualize_item_agreement(user_agreements)


def users_hierarchical_clustering(agreement_results):
    user_ids = list(set([user for pair in agreement_results.keys() for user in pair]))
    user_ids.sort()

    # Create a distance matrix from agreement scores
    matrix = np.zeros((len(user_ids), len(user_ids)))

    for i, user1 in enumerate(user_ids):
        for j, user2 in enumerate(user_ids):
            if i != j:
                # Convert agreement to distance (higher agreement → lower distance)
                agreement = agreement_results.get((user1, user2), agreement_results.get((user2, user1), 0))
                matrix[i, j] = 100 - agreement  # 100% disagreement means max distance

    # Perform hierarchical clustering
    linkage_matrix = linkage(matrix, method='ward')

    plt.figure(figsize=(10, 5))
    dendrogram(linkage_matrix, labels=user_ids, leaf_rotation=45)
    plt.title("User Clustering Based on Agreement")
    plt.xlabel("User ID")
    plt.ylabel("Distance")
    plt.show()


def heatmap_user_agreement(agreement_results):
    # Step 1: Extract unique user IDs
    user_ids = list(set(user for pair in agreement_results.keys() for user in pair))
    user_ids.sort()

    # Step 2: Create an empty matrix
    num_users = len(user_ids)
    matrix = np.zeros((num_users, num_users))

    # Step 3: Fill the matrix with agreement percentages
    for i, user1 in enumerate(user_ids):
        for j, user2 in enumerate(user_ids):
            if i != j:
                # Check both (user1, user2) and (user2, user1) before defaulting to 0
                matrix[i, j] = agreement_results.get((user1, user2), agreement_results.get((user2, user1), 0))

    # Create a heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(matrix, xticklabels=user_ids, yticklabels=user_ids, annot=True, fmt=".1f", cmap="coolwarm")
    plt.title("User Agreement Heatmap")
    plt.xlabel("User ID")
    plt.ylabel("User ID")
    plt.show()


def distribution_agreement_scores(sorted_agreement_results):
    scores = list(sorted_agreement_results.values())

    plt.figure(figsize=(8, 5))
    plt.hist(scores, bins=10, edgecolor='black', alpha=0.7)
    plt.xlabel("Agreement Percentage")
    plt.ylabel("Frequency")
    plt.title("Distribution of Agreement Scores")
    plt.grid()
    plt.show()


def most_controversial_items(item_agreements):
    # Sort items by lowest agreement
    least_agreed_items = dict(sorted(item_agreements.items(), key=lambda item: item[1])[:5])

    print("\nMost Controversial Items (Lowest Agreement):")
    for item, agreement in least_agreed_items.items():
        print(f"{item}: {agreement:.2f}%")

    # Visualize the controversial items
    visualize_item_agreement(least_agreed_items)


# Function to visualize the agreement results with user_id on the bars
def visualize_results(results):
    user_pairs = list(results.keys())
    agreement_percentages = list(results.values())

    visualize_agreement(results, user_pairs, agreement_percentages)
    # dist_agreement_prcnt(agreement_percentages)
    # disagreement_prcnt(agreement_percentages)


def main(user_files, responses_df):
    # Load responses from the files
    responses = load_responses(user_files)

    # Compare responses and calculate agreement
    agreement_results = compare_responses(responses)
    # Calculate agreement across different items
    item_agreements = agreement_by_item(responses)
    # Sort results for user pair agreement
    sorted_agreement_results = dict(sorted(agreement_results.items(), key=lambda item: item[1], reverse=True))
    sorted_item_agreement_results = dict(sorted(item_agreements.items(), key=lambda item: item[1], reverse=True))

    # -----------------------------------------------

    # Print the results in a table
    print("User Pair Agreement (%)")
    for pair, agreement in sorted_agreement_results.items():
        print(f"User {pair[0]} vs User {pair[1]}: {agreement:.2f}%")

    # Visualize the agreement results
    visualize_results(sorted_agreement_results)

    # -----------------------------------------------

    # Print and visualize agreement across different items
    print("\nAgreement Across Different Items:")
    for item, agreement in sorted_item_agreement_results.items():
        print(f"{item}: {agreement:.2f}%")

    # Visualize the agreement across different items
    visualize_item_agreement(sorted_item_agreement_results)

    # -----------------------------------------------

    agreement_over_time(df=responses_df)

    # -----------------------------------------------

    most_controversial_items(item_agreements=item_agreements)

    # -----------------------------------------------

    agreement_per_user(agreement_results=agreement_results)

    # -----------------------------------------------

    users_hierarchical_clustering(agreement_results=agreement_results)

    # -----------------------------------------------

    heatmap_user_agreement(agreement_results=agreement_results)

    # -----------------------------------------------

    distribution_agreement_scores(sorted_agreement_results=sorted_agreement_results)


# Convert the polygon string into a list of coordinates
def parse_polygon(polygon_str):
    return np.array(json.loads(polygon_str))


def compute_human_vs_random_agreement(human_responses, random_responses):
    # Compare the random responses with human responses on common pairs
    common_pairs = []
    for random_response in random_responses:
        for human_response in human_responses:
            if random_response['image_path'] == human_response['image_path'] and random_response['chosen_item'] == \
                    human_response['chosen_item']:
                random_polygon = parse_polygon(random_response['chosen_polygon'])
                human_polygon = parse_polygon(human_response['chosen_polygon'])

                # Calculate IoU agreement
                iou_score = compute_iou(random_polygon, human_polygon)

                # Store the result for this pair
                common_pairs.append({
                    'image_path': random_response['image_path'],
                    'chosen_item': random_response['chosen_item'],
                    'human_user_id': human_response['user_id'],
                    'agreement_score': iou_score
                })

    df = pd.DataFrame(common_pairs)
    return df


def stat_and_plot_human_random(df):
    # Visualize the mean agreement between human users and random responses
    visualize_mean_agreement(df)

    # Calculate and visualize agreement across items for each user
    users = df['human_user_id'].unique()
    for user in users:
        user_data = df[df['human_user_id'] == user]
        item_agreements = user_data.groupby('chosen_item')['agreement_score'].mean().to_dict()

        print(f"\nAgreement Across Items for User {user}:")
        print(sorted(item_agreements.items(), key=lambda x: x[1], reverse=True))

        visualize_item_agreement(item_agreements=item_agreements, user_id=str(user))

    # Boxplot to show the distritem_agreement_per_user[item_agreement_per_user["human_user_id"] == user]ibution of agreement scores for each user
    plt.figure(figsize=(12, 8))
    sns.boxplot(x='human_user_id', y='agreement_score', data=df)
    plt.title('Agreement Score Distribution per Human User')
    plt.xlabel('User ID')
    plt.ylabel('Agreement Score (IoU)')
    plt.show()


def agreement_human_random(human_responses_json, random_responses_json):
    # Load data
    human_responses = load_json(human_responses_json)
    random_responses = load_json(random_responses_json)

    # Compute agreements
    df = compute_human_vs_random_agreement(human_responses, random_responses)
    stat_and_plot_human_random(df=df)


def full_human_agreement(cleaned_response_csv, agreement_pairs_json):
    # Load the cleaned responses
    df = pd.read_csv(cleaned_response_csv)

    # Group by image_path and chosen_item
    grouped = df.groupby(['image_path', 'chosen_item'])

    # Function to check 100% agreement among users
    def all_users_agree(group):
        users = set(group['user_id'])
        # Check if all 3 users are present and all chose the same polygon
        return len(users) == 3 and group['chosen_polygon'].nunique() == 1

    # Filter groups with 100% agreement from all 3 users
    agreed_groups = grouped.filter(all_users_agree)

    # Get unique image_path–chosen_item pairs with agreement
    agreed_pairs = agreed_groups[['image_path', 'chosen_item']].drop_duplicates()
    # Convert to desired dict format
    result_dict = agreed_pairs.groupby('image_path')['chosen_item'].apply(list).to_dict()

    # Also create a list of all image paths with agreement
    agreed_image_paths = list(result_dict.keys())
    with open("../image_details/agreed_images.json", 'w') as f:
        json.dump(agreed_image_paths, f, indent=2)

    # Save as JSON
    with open(agreement_pairs_json, 'w') as f:
        json.dump(result_dict, f, indent=2)

    print(f"Saved agreed pairs to {agreement_pairs_json}")


if __name__ == '__main__':
    # List of response files for each user
    # user_files = [
    #     'responses/user_responses_test_asaf.json',
    #     'responses/user_responses_test_lee_or.json',
    #     'responses/user_responses_test_lior.json',
    #     'responses/user_responses_test_michaela_2.json',
    #     'responses/user_responses_test_oren.json',
    #     'responses/user_responses_test_ronny.json',
    #     'responses/user_responses_test_saggie.json',
    #     'responses/user_responses_test_shabi.json'
    # ]

    # user_files = ['../baselines/human/cleaned_responses.json']
    # responses_df = pd.read_csv("../baselines/human/cleaned_responses.csv")
    # main(user_files=user_files, responses_df=responses_df)

    # agreement_human_random(human_responses_json='../baselines/human/cleaned_responses.json',
    #                        random_responses_json="../baselines/random/random_train_responses.json")

    full_human_agreement(cleaned_response_csv='../baselines/human/cleaned_responses.csv', agreement_pairs_json='../baselines/human/agreement_pairs.json')
