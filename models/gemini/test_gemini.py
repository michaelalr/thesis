import google.generativeai as genai
import os

# from dotenv import load_dotenv # Optional: For loading from a .env file

# Optional: Load environment variables from a .env file if you created one
# load_dotenv()

# Configure the API key
try:
    # Attempt to get the API key from the environment variable
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key not found in environment variable 'GOOGLE_API_KEY'")

    genai.configure(api_key=api_key)
    print("Google AI SDK configured successfully.")

except ValueError as e:
    print(f"Error: {e}")
    print("Please set the GOOGLE_API_KEY environment variable.")
    exit()  # Exit if the key isn't configured
except Exception as e:
    print(f"An unexpected error occurred during configuration: {e}")
    exit()

# Choose a text generation model (e.g., gemini-1.5-flash-latest)
# Note: 'gemini-2.0-flash' in your original snippet is likely incorrect.
# Use 'gemini-1.5-flash-latest' or 'gemini-pro'.
model_name = 'gemini-1.5-flash-latest'
print(f"Using model: {model_name}")

try:
    model = genai.GenerativeModel(model_name)

    # Generate content
    prompt = "Explain how AI works in simple terms."
    print(f"Sending prompt: '{prompt}'")
    response = model.generate_content(prompt)

    # Print the response
    print("\nResponse:")
    print(response.text)

except Exception as e:
    print(f"\nAn error occurred during content generation: {e}")
    # You might see specific errors related to API access, billing, etc. here
    if hasattr(response, 'prompt_feedback'):
        print(response.prompt_feedback)