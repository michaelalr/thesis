import os
import random
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import pandas as pd
from objects_lists import kitchen, living_room, bathroom, bedroom

images_with_detection_path = "C:\\Users\\miki\\PycharmProjects\\thesis\\use_sun"


def get_random_image(folder_path):
    # Get a list of image files in the folder
    images = [img for img in os.listdir(folder_path) if img.endswith(('.jpg', '.png'))]
    # Return a random image
    return random.choice(images)


def get_random_object(objects_list):
    # Select a random object from the list
    return random.choice(objects_list)


def show_image(image_path, containers, object_name):
    # Create the main window
    root = tk.Tk()
    root.title("Select Container for Object")

    # Load and display the image
    img = Image.open(image_path)
    img = img.resize((500, 500), Image.Resampling.LANCZOS)  # Use LANCZOS for resampling
    img_tk = ImageTk.PhotoImage(img)
    label = tk.Label(root, image=img_tk)
    label.pack()

    # Display the object name
    object_label = tk.Label(root, text=f"Where would you store: {object_name}")
    object_label.pack()

    # Create a listbox to display container choices
    container_list = tk.Listbox(root)
    for container in containers:
        container_list.insert(tk.END, container)
    container_list.pack()

    # "None" option for no suitable container
    none_option = tk.Button(root, text="None of the above",
                            command=lambda: save_and_exit('None', image_path, object_name, root))
    none_option.pack()

    # Function to get selected container and exit
    def save_selection():
        selected_container = container_list.get(tk.ACTIVE)  # Get selected container
        save_and_exit(selected_container, image_path, object_name, root)

    # Button to confirm selection
    confirm_button = tk.Button(root, text="Confirm Selection", command=save_selection)
    confirm_button.pack()

    # Start the Tkinter loop
    root.mainloop()


def save_and_exit(selected_container, image_name, object_name, root):
    # Save the response and close the window
    print(f"Selected: {selected_container} for {object_name} in {image_name}")
    save_response(image_name, object_name, selected_container)
    root.destroy()


# Create or append the user response to a CSV
def save_response(image_name, object_name, chosen_container, user_id="user1"):
    data = {'Image': [image_name], 'Object': [object_name], 'Container': [chosen_container], 'User': [user_id]}
    df = pd.DataFrame(data)
    # Save data in CSV (append mode)
    df.to_csv('user_responses.csv', mode='a', header=False, index=False)


def distribute_images(images, num_users=3):
    # Shuffle the image list to randomize the selection
    random.shuffle(images)

    # Split images into 1/3 and 2/3
    split_index = len(images) // 3
    shared_images = images[:split_index]  # Images that all users will see
    remaining_images = images[split_index:]

    # Divide remaining images among users
    user_images = {f"user_{i + 1}": [] for i in range(num_users)}

    for i, img in enumerate(remaining_images):
        user_images[f"user_{(i % num_users) + 1}"].append(img)

    # Add the shared images to each user
    for i in range(num_users):
        user_images[f"user_{i + 1}"].extend(shared_images)

    return user_images


def main():
    # Assuming folder path and objects are already defined
    folder_path = images_with_detection_path
    objects_list = kitchen

    # Load all images in the folder
    images = [img for img in os.listdir(folder_path) if img.endswith(('.jpg', '.png'))]

    # Distribute images among users
    user_images = distribute_images(images)

    # Loop over users and images
    for user, imgs in user_images.items():
        for img in imgs:
            # Get a random object
            object_name = get_random_object(objects_list)

            # Show the image and let the user select a container
            containers = ["Drawer", "Cabinet", "Closet"]  # Dummy container list
            show_image(os.path.join(folder_path, img), containers, object_name)


if __name__ == '__main__':
    main()
