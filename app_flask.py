import pandas as pd
from flask import Flask, request, jsonify, render_template
import random

app = Flask(__name__)

# Load CSV data (replace 'user_1_images.csv' with the appropriate user CSV)
csv_data = pd.read_csv('csv_files/user_1_images.csv')  # Load CSV into DataFrame
# csv_data = df.to_dict(orient='records')  # Convert DataFrame to list of dictionaries


@app.route('/')
def index():
    # Take a random row from the DataFrame
    random_row = csv_data.sample(n=1).iloc[0]  # This works for DataFrame
    image_path = random_row['image_path']  # Full path including /static/images/
    random_item = random.choice(eval(random_row['common_items']))  # Pick a random item from the list

    # Render the HTML page, passing the image path and item
    return render_template('index.html', image_path=image_path, random_item=random_item)


# @app.route('/load_csv')
# def load_csv():
#     # Adjust the image path to point to static/images
#     csv_data['image_path'] = csv_data['image_path'].apply(lambda x: f"/static/images/{x.split('/')[-1]}")
#     return jsonify(csv_data.to_dict(orient='records'))  # Convert the DataFrame to a list of dictionaries for JSON

@app.route('/load_csv', methods=['GET'])
def load_csv():
    csv_list = csv_data.to_dict(orient='records')  # Convert DataFrame to list of dictionaries
    return jsonify(csv_list)  # Send list of dictionaries to the frontend





@app.route('/save_answer', methods=['POST'])
def save_answer():
    user_response = request.json
    # Append user response to their answer CSV
    df = pd.DataFrame([user_response])
    df.to_csv(f"answers_user_1.csv", mode='a', header=False, index=False)
    return jsonify(success=True)


if __name__ == '__main__':
    app.run(debug=True)
