import google.generativeai as genai
import google.api_core.exceptions  # For specific API error handling
import os
import json
from PIL import Image, UnidentifiedImageError  # To handle image data and errors
import time  # To add delays for retries and rate limiting
import re  # For parsing the bounding box
from urllib.parse import urlparse  # To help extract filename from URL
import logging  # For robust logging

# --- Configuration ---

# 1. Logging Setup
LOG_FILE = 'processing_log.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'  # Append mode, keeps log across runs
)
# Also log to console (optional, can be noisy for full run)
# logging.getLogger().addHandler(logging.StreamHandler())

print(f"Logging detailed progress to {LOG_FILE}")

# 2. API Key Setup
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("API key not found in environment variable 'GOOGLE_API_KEY'")
    genai.configure(api_key=api_key)
    logging.info("Google AI SDK configured successfully.")
except ValueError as e:
    logging.error(f"Configuration Error: {e}. Please set GOOGLE_API_KEY environment variable.")
    exit()
except Exception as e:
    logging.error(f"An unexpected error occurred during configuration: {e}")
    exit()

# 3. Model Selection
MODEL_NAME = "gemini-1.5-flash-latest"
try:
    model = genai.GenerativeModel(MODEL_NAME)
    logging.info(f"Using model: {MODEL_NAME}")
except Exception as e:
    logging.error(f"Failed to initialize model {MODEL_NAME}: {e}")
    exit()

# 4. File Paths
INPUT_JSON_PATH = "train_data.json"
OUTPUT_JSON_PATH = "train_data_with_gemini_bboxes_as_strings.json"  # Output file
LOCAL_IMAGE_BASE_DIR = "./images"  # Base directory for local images

# 5. Processing & Reliability Settings
PROCESS_LIMIT = None  # Set to None to process all 6500+ entries
SAVE_INTERVAL = 50  # Save progress every X entries
MAX_API_RETRIES = 3  # Max attempts for API calls
INITIAL_RETRY_DELAY_SECONDS = 5  # Initial delay, increases for subsequent retries
API_CALL_DELAY_SECONDS = 1  # Delay between successful API calls (politeness)

# 6. Prompt Definition
PROMPT_TEMPLATE = """
Analyze the provided image of a kitchen.
Identify the item: '{item_name}'
Determine the most likely storage location for this item, considering only drawers or cabinet doors visible in the image.
Provide the bounding box coordinates for this storage location as a Python list of four integers: [x_min, y_min, x_max, y_max].
The coordinates should be relative to the image dimensions (top-left is [0,0]).
Only output the list of coordinates and nothing else. For example: [100, 200, 300, 400]
If you cannot determine a likely storage location (drawer or cabinet door) for this item, output: [0, 0, 0, 0]
"""


# --- Helper Functions ---

def parse_bounding_box(response_text):
    """Attempts to extract a bounding box list [xmin, ymin, xmax, ymax] from the model's text response."""
    # Returns the list [xmin, ymin, xmax, ymax] or [0,0,0,0] on failure
    try:
        match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', response_text)
        if match:
            bbox = [int(p) for p in match.groups()]
            if all(coord >= 0 for coord in bbox):
                if bbox[2] >= bbox[0] and bbox[3] >= bbox[1]:
                    return bbox
                else:
                    logging.warning(f"Parsed bbox with max < min: {bbox} from text: {response_text}")
                    return [0, 0, 0, 0]
            else:
                logging.warning(f"Parsed non-negative bbox with invalid values: {bbox} from text: {response_text}")
                return [0, 0, 0, 0]
        else:
            # Log only if response text was not empty, otherwise it might just be a refusal / safety block
            if response_text and response_text.strip():
                logging.warning(f"Could not parse bbox list from text: {response_text}")
            return [0, 0, 0, 0]
    except Exception as e:
        logging.error(f"Error parsing bbox list from text '{response_text}': {e}")
        return [0, 0, 0, 0]


def bbox_to_polygon_list(bbox_list):
    """Converts [xmin, ymin, xmax, ymax] list to polygon list [[xmin,ymin],[xmin,ymax],[xmax,ymax],[xmax,ymin]]"""
    if bbox_list == [0, 0, 0, 0] or len(bbox_list) != 4:
        return [[0, 0], [0, 0], [0, 0], [0, 0]]
    else:
        xmin, ymin, xmax, ymax = bbox_list
        return [[xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin]]


def save_results(results, filepath):
    """Saves the results list to a JSON file."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        # Use print for this key status update so it appears prominently
        print(f"Progress saved successfully to {filepath}")
        logging.info(f"Progress saved successfully with {len(results)} entries to {filepath}")
    except Exception as e:
        logging.error(f"Error saving results to {filepath}: {e}")


# --- Main Processing Logic ---

def main():
    # --- Checkpoint Loading ---
    results_to_save = []
    processed_image_paths = set()
    if os.path.exists(OUTPUT_JSON_PATH):
        try:
            with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                results_to_save = json.load(f)
            # Ensure it's a list
            if not isinstance(results_to_save, list):
                logging.warning(f"Existing output file {OUTPUT_JSON_PATH} does not contain a list. Starting fresh.")
                results_to_save = []
            else:
                processed_image_paths = {entry.get('image_path') for entry in results_to_save if
                                         entry.get('image_path')}
                print(
                    f"Loaded {len(results_to_save)} existing results from {OUTPUT_JSON_PATH}. Found {len(processed_image_paths)} processed image paths.")
                logging.info(f"Resuming. Loaded {len(results_to_save)} existing results from {OUTPUT_JSON_PATH}.")
        except json.JSONDecodeError:
            logging.warning(f"Could not decode JSON from existing {OUTPUT_JSON_PATH}. Starting fresh.")
            results_to_save = []
            processed_image_paths = set()
        except Exception as e:
            logging.error(f"Error loading existing results from {OUTPUT_JSON_PATH}: {e}. Starting fresh.")
            results_to_save = []
            processed_image_paths = set()
    else:
        print("Output file not found. Starting fresh.")
        logging.info("Output file not found. Starting fresh.")
    # --- End Checkpoint Loading ---

    # --- Load Input Data ---
    try:
        with open(INPUT_JSON_PATH, 'r', encoding='utf-8') as f:
            input_data = json.load(f)
        logging.info(f"Loaded {len(input_data)} total entries from {INPUT_JSON_PATH}")
    except FileNotFoundError:
        logging.error(f"CRITICAL: Input file not found at {INPUT_JSON_PATH}. Cannot continue.")
        return
    except json.JSONDecodeError:
        logging.error(f"CRITICAL: Could not decode JSON from {INPUT_JSON_PATH}. Cannot continue.")
        return
    except Exception as e:
        logging.error(f"CRITICAL: An unexpected error occurred loading input JSON: {e}. Cannot continue.")
        return
    # --- End Load Input Data ---

    items_to_process = input_data[:PROCESS_LIMIT] if PROCESS_LIMIT is not None else input_data
    total_input_items = len(items_to_process)
    skipped_count = 0
    processed_count_session = 0  # Count items processed in this run
    api_call_errors = 0

    print(
        f"Starting processing. Total entries to consider: {total_input_items}. Already processed: {len(processed_image_paths)}.")

    # Define the default bbox list for error cases
    default_bbox_list = [0, 0, 0, 0]

    for i, entry in enumerate(items_to_process):

        image_url_from_json = entry.get("image_path")
        chosen_item = entry.get("chosen_item")
        room_type = entry.get("room_type", "unknown_room")

        current_entry_log_prefix = f"Entry {i + 1}/{total_input_items} (URL: {image_url_from_json})"

        # --- Checkpoint Skipping ---
        if image_url_from_json in processed_image_paths:
            skipped_count += 1
            if i < 10 or i % 1000 == 0:  # Log skipping occasionally to avoid flood
                logging.info(f"{current_entry_log_prefix}: Already processed. Skipping.")
            continue
        # --- End Checkpoint Skipping ---

        logging.info(f"{current_entry_log_prefix}: Processing...")

        # Initialize with defaults for this entry
        gemini_bbox_list = default_bbox_list
        image = None

        if not image_url_from_json or not chosen_item:
            logging.warning(f"{current_entry_log_prefix}: Skipping - missing 'image_path' or 'chosen_item'.")
            # Need to decide if we save skipped entries with defaults, let's not for now.
            continue

        # 1. Construct local image path and load image
        local_image_path = ""  # Define outside try block
        try:
            parsed_url = urlparse(image_url_from_json)
            filename = os.path.basename(parsed_url.path)
            if not filename:
                raise ValueError("Could not extract filename from URL")
            local_image_path = os.path.join(LOCAL_IMAGE_BASE_DIR, room_type, filename)
            logging.info(f"{current_entry_log_prefix}: Loading local image: {local_image_path}")
            image = Image.open(local_image_path)
            logging.info(f"{current_entry_log_prefix}: Image loaded successfully.")

        except FileNotFoundError:
            logging.error(
                f"{current_entry_log_prefix}: Local image file not found at '{local_image_path}'. Assigning default bbox.")
            image = None
        except UnidentifiedImageError:
            logging.error(
                f"{current_entry_log_prefix}: Cannot identify image file (possibly corrupt) at '{local_image_path}'. Assigning default bbox.")
            image = None
        except ValueError as e:
            logging.error(
                f"{current_entry_log_prefix}: Could not determine local path from URL: {e}. Assigning default bbox.")
            image = None
        except Exception as e:
            logging.error(
                f"{current_entry_log_prefix}: Could not open local image '{local_image_path}': {e}. Assigning default bbox.")
            image = None

        # 2. Call API only if image loaded successfully
        if image:
            prompt = PROMPT_TEMPLATE.format(item_name=chosen_item)
            response_text = ""  # Store response text if needed

            for attempt in range(MAX_API_RETRIES):
                try:
                    logging.info(
                        f"{current_entry_log_prefix}: Calling Gemini API (Attempt {attempt + 1}/{MAX_API_RETRIES})...")
                    response = model.generate_content([prompt, image])
                    response_text = response.text  # Store text before parsing
                    gemini_bbox_list = parse_bounding_box(response_text)  # Overwrite default if successful
                    logging.info(
                        f"{current_entry_log_prefix}: API call successful. Parsed BBox List: {gemini_bbox_list}")
                    # Successful call, break retry loop
                    break

                    # --- Retryable Errors ---
                except (google.api_core.exceptions.ServiceUnavailable,
                        google.api_core.exceptions.DeadlineExceeded,
                        google.api_core.exceptions.InternalServerError) as e:
                    logging.warning(
                        f"{current_entry_log_prefix}: API Attempt {attempt + 1} failed (Retryable Server Error): {e}")
                    if attempt == MAX_API_RETRIES - 1:
                        logging.error(
                            f"{current_entry_log_prefix}: Max retries reached for server error. Assigning default bbox.")
                        api_call_errors += 1
                        gemini_bbox_list = default_bbox_list  # Ensure default on final failure
                    else:
                        delay = INITIAL_RETRY_DELAY_SECONDS * (2 ** attempt)  # Exponential backoff
                        logging.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)

                except google.api_core.exceptions.ResourceExhausted as e:
                    # Specific handling for rate limits
                    logging.warning(f"{current_entry_log_prefix}: API Attempt {attempt + 1} failed (Rate Limit): {e}")
                    if attempt == MAX_API_RETRIES - 1:
                        logging.error(
                            f"{current_entry_log_prefix}: Max retries reached after rate limit. Assigning default bbox.")
                        api_call_errors += 1
                        gemini_bbox_list = default_bbox_list
                    else:
                        delay = 60 * (attempt + 1)  # Wait longer for rate limits
                        logging.info(f"Rate limit hit. Sleeping for {delay} seconds before retry...")
                        time.sleep(delay)

                # --- Non-Retryable / Other Errors ---
                except Exception as e:
                    logging.error(f"{current_entry_log_prefix}: Non-retryable error calling Gemini API or parsing: {e}",
                                  exc_info=True)  # Log traceback
                    api_call_errors += 1
                    gemini_bbox_list = default_bbox_list  # Assign default
                    break  # Exit retry loop for other errors

            # Close the image file handle after API call attempts
            image.close()

            # Brief pause after successful/failed API attempt before next entry (politeness)
            time.sleep(API_CALL_DELAY_SECONDS)

        # --- End API Call Logic ---

        # 3. Convert final BBox list (parsed or default) and Polygon list to Strings
        gemini_bbox_list_string = json.dumps(gemini_bbox_list)
        polygon_points_list = bbox_to_polygon_list(gemini_bbox_list)
        gemini_bbox_polygon_string = json.dumps(polygon_points_list)

        # 4. Create new entry and append to results
        new_entry = entry.copy()
        new_entry["gemini_bbox_list_string"] = gemini_bbox_list_string
        new_entry["gemini_bbox_polygon_string"] = gemini_bbox_polygon_string
        results_to_save.append(new_entry)  # Append to the list that includes existing results
        processed_count_session += 1  # Increment count for this session

        # --- Periodic Saving (Checkpoint) ---
        # Check if it's time to save (based on total entries processed *in this session*)
        if processed_count_session > 0 and processed_count_session % SAVE_INTERVAL == 0:
            print(f"\n--- Processed {processed_count_session} entries in this session. Saving checkpoint... ---")
            save_results(results_to_save, OUTPUT_JSON_PATH)
            print(f"--- Checkpoint saved. Continuing processing... ---")
        # --- End Periodic Saving ---

    # --- Final Save ---
    print(f"\nLoop finished. Processed {processed_count_session} new entries in this session.")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} entries that were already processed in previous runs.")
    if api_call_errors > 0:
        print(f"Encountered {api_call_errors} final errors during API calls (check log).")

    print("Performing final save...")
    save_results(results_to_save, OUTPUT_JSON_PATH)
    print("--- Processing Complete ---")
    logging.info(f"--- Processing Complete. Total entries in output file: {len(results_to_save)} ---")


if __name__ == "__main__":
    main()