import json
from datetime import datetime, timedelta
from collections import defaultdict

# Load the JSON file
with open("upwork_responses.json", "r") as file:
    data = json.load(file)

# Dictionary to store user-wise timestamps
user_sessions = defaultdict(list)

# Convert timestamps and group by user_id
for entry in data:
    timestamp = datetime.strptime(f"{entry['date']} {entry['time']}", "%Y-%m-%d %H:%M:%S")
    user_sessions[entry["user_id"]].append(timestamp)


# Function to calculate work intervals and average time per image
def analyze_sessions(user_sessions, gap_minutes=10):
    user_analysis = {}

    for user_id, timestamps in user_sessions.items():
        timestamps.sort()  # Sort timestamps in ascending order
        sessions = []
        current_session = [timestamps[0]]

        # Identify working sessions
        for i in range(1, len(timestamps)):
            time_gap = (timestamps[i] - timestamps[i - 1]).total_seconds() / 60  # Convert to minutes
            if time_gap <= gap_minutes:  # If gap is small, continue the session
                current_session.append(timestamps[i])
            else:  # If gap is large, start a new session
                sessions.append(current_session)
                current_session = [timestamps[i]]

        if current_session:
            sessions.append(current_session)  # Add last session

        # Calculate total work time
        total_time_spent_seconds = sum((session[-1] - session[0]).total_seconds() for session in sessions)
        total_images = len(timestamps)
        avg_time_per_image = total_time_spent_seconds / total_images if total_images else 0
        total_time_spent_hours = total_time_spent_seconds / 3600  # Convert to hours

        # Save results
        user_analysis[user_id] = {
            "sessions": [(session[0], session[-1]) for session in sessions],  # Start and end of each session
            "total_images": total_images,
            "total_time": total_time_spent_hours,
            "avg_time_per_image": avg_time_per_image
        }

    return user_analysis


# Run analysis
result = analyze_sessions(user_sessions)

# Print results
for user, info in result.items():
    print(f"User {user}:")
    print(f"  Total Images: {info['total_images']}")
    print(f"  Total Time: {info['total_time']}")
    print(f"  Avg Time per Image: {timedelta(seconds=info['avg_time_per_image'])}")
    print("  Sessions:")
    for session in info["sessions"]:
        print(f"    {session[0]} -> {session[1]}")
    print("-" * 40)
