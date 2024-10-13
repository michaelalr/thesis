import tensorflow_datasets as tfds
import tensorflow as tf
import matplotlib.pyplot as plt


# Step 1: Load the SUN dataset with a limited number of examples using split
def load_partial_sun_dataset(num_samples=100):
    # Load a small subset of the dataset without as_supervised=True
    dataset, info = tfds.load('sun397', split=f'train[:{num_samples}]', with_info=True)

    # Get label names for the dataset
    label_names = info.features['label'].names
    return dataset, label_names


# Step 2: Filter the dataset by specific categories
def filter_by_category(dataset, label_names, categories):
    # Function to filter dataset based on the category using tf.py_function
    def filter_func(sample):
        label = sample['label']

        # Use tf.py_function to convert tensor to Python integer and apply filtering
        def label_filter_fn(label):
            category_name = label_names[int(label)]  # Convert to Python integer

            # Debug print statement to show the category name
            # print(f"Label: {label}, Category Name: {category_name}")

            return category_name in categories

        # Wrap the label filter function using tf.py_function
        return tf.py_function(func=label_filter_fn, inp=[label], Tout=tf.bool)

    # Apply the filter to the dataset
    filtered_dataset = dataset.filter(filter_func)
    return filtered_dataset


# Function to display some images from the limited dataset
def display_samples(dataset, label_names, num_samples=5):
    # Create a vertical layout
    plt.figure(figsize=(5, num_samples * 5))  # Adjust height based on number of samples

    # Iterate through dataset items
    for i, sample in enumerate(dataset.take(num_samples)):
        image = sample['image']  # Access image from the dictionary
        label = sample['label']  # Access label from the dictionary
        category_name = label_names[label.numpy()]  # Convert label to category name

        plt.subplot(num_samples, 1, i + 1)  # Create subplot in a single column
        plt.imshow(image)
        plt.axis('off')
        plt.title(f'Category: {category_name}')

    plt.show()


# Main function to load and filter the dataset
def main():
    # Load a small subset of the SUN dataset
    dataset, label_names = load_partial_sun_dataset(num_samples=500)

    # Define the categories you want to filter (kitchen, bathroom, living room)
    target_categories = ['/k/kitchen', '/b/bathroom', '/l/living_room', '/b/bedroom']

    # Filter the dataset by those categories
    filtered_dataset = filter_by_category(dataset, label_names, target_categories)

    # Display the number of examples in the filtered dataset
    print(f"Number of examples in the filtered dataset: {len(list(filtered_dataset))}")

    # Display some sample images
    display_samples(filtered_dataset, label_names, num_samples=34)


if __name__ == '__main__':
    main()
