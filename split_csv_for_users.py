import pandas as pd


def split_csv_for_users(csv_file_path, num_users):
    df = pd.read_csv(csv_file_path)
    num_images = len(df)

    # Split 10% shared images
    shared_images = df.sample(frac=0.10)

    # Split 90% remaining images randomly across users
    remaining_images = df.drop(shared_images.index).sample(frac=1).reset_index(drop=True)

    # Create CSV files for each user
    for i in range(num_users):
        # Combine shared images with a random portion of remaining images for this user
        user_images = pd.concat([shared_images, remaining_images[i::num_users]]).reset_index(drop=True)

        # Save user-specific CSV file
        user_images.to_csv(f'user_{i + 1}_images.csv', index=False)

    print(f'Successfully created CSV files for {num_users} users.')


if __name__ == '__main__':
    csv_file_path = '/csv_files/image_details_5.csv'
    num_users = 3
    split_csv_for_users(csv_file_path=csv_file_path, num_users=num_users)
