import os
import json
import base64
import time
from dotenv import load_dotenv
from groq import Groq
from PIL import Image # To ensure we only process valid image files
import io

# Load environment variables from .env
load_dotenv()

# --- Configuration ---
TARGET_DIRS = ["choosenCar"] # Directories to process
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp'}
API_CALL_DELAY_SECONDS = 2 # Delay between Groq API calls to avoid rate limits

# --- Groq Client Initialization ---
try:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY not found in .env file. Exiting.")
        exit()
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    groq_client = None
    exit()

# --- Helper Groq Analysis Function (adapted from main.py) ---
async def analyze_image_for_labeling(image_bytes: bytes):
    if not groq_client:
        print("Groq client not initialized.")
        return None

    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analisa gambar ini dan identifikasi jenis kendaraan (Mobil atau Motor) dan plat nomornya. TANPA PENJELASAN SAMA SEKALI"
                                    "Jika plat nomor tidak terbaca jelas atau tidak ada, output 'TIDAK_TERDETEKSI' untuk Plat_Nomor. "
                                    "Jika jenis kendaraan tidak jelas, output 'TIDAK_DIKETAHUI' untuk Vehicle_Type. "
                                    "Format output HANYA JSON: {\"Vehicle_Type\": \"<jenis>\", \"Plat_Nomor\": \"<plat>\"}. "
                                    "Pastikan plat nomor hanya mengandung huruf dan angka, tanpa spasi berlebih atau karakter aneh. Jangan ada teks lain selain JSON."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}" 
                            }
                        }
                    ]
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            temperature=0.1,
            max_tokens=150,
            # response_format={"type": "json_object"} # Uncomment if model fully supports reliable JSON mode
        )
        
        response_content = chat_completion.choices[0].message.content
        # print(f"Raw Groq Response for labeling: {response_content}") # Debugging

        json_part = response_content
        # Try to find JSON block if markdown is present
        if "```json" in response_content:
            json_part = response_content.split("```json")[1].split("```")[0].strip()
        elif response_content.strip().startswith("{") and response_content.strip().endswith("}"):
            json_part = response_content.strip()
        else:
            # If not clearly JSON, attempt to extract it or fail
            print(f"  Warning: Groq response for labeling doesn't look like clean JSON: {response_content}")
            # You might need more sophisticated extraction here if this happens often
            try: # Basic attempt to find a JSON object within the string
                start_index = response_content.find('{')
                end_index = response_content.rfind('}') + 1
                if start_index != -1 and end_index != 0 and end_index > start_index:
                    json_part = response_content[start_index:end_index]
                else:
                    raise ValueError("No JSON object found")
            except Exception:
                 print(f"  Could not extract JSON from: {response_content}")
                 return None


        data = json.loads(json_part)
        
        plat = data.get("Plat_Nomor", "TIDAK_TERDETEKSI")
        tipe = data.get("Vehicle_Type", "TIDAK_DIKETAHUI")

        # Normalize and validate
        plat_cleaned = plat.upper().replace(" ", "") if plat else "TIDAK_TERDETEKSI"
        
        tipe_capitalized = tipe.capitalize() if tipe else "TIDAK_DIKETAHUI"
        if tipe_capitalized not in ["Mobil", "Motor", "TIDAK_DIKETAHUI"]:
            print(f"  Warning: Groq detected an unknown vehicle type: {tipe_capitalized}. Setting to TIDAK_DIKETAHUI.")
            tipe_capitalized = "TIDAK_DIKETAHUI"

        if plat_cleaned == "TIDAK_TERDETEKSI" or tipe_capitalized == "TIDAK_DIKETAHUI":
            print(f"  Info: Groq could not confidently detect plate/type (Plat: {plat_cleaned}, Type: {tipe_capitalized}). Skipping label update for this image.")
            return None # Don't add uncertain labels

        return {"Vehicle_Type": tipe_capitalized, "Plat_Nomor": plat_cleaned}

    except json.JSONDecodeError as e:
        print(f"  Error parsing Groq JSON response: {e}. Content: {response_content}")
        return None
    except Exception as e:
        print(f"  An unexpected error occurred during Groq API call: {e}")
        return None

# --- Directory Processing Function ---
async def process_directory(dir_path):
    full_dir_path = os.path.join(BASE_DIR, dir_path)
    if not os.path.isdir(full_dir_path):
        print(f"Directory not found: {full_dir_path}. Skipping.")
        return

    print(f"\nProcessing directory: {dir_path}")
    labels_file_path = os.path.join(full_dir_path, "labels.json")
    
    # Load existing labels
    if os.path.exists(labels_file_path):
        try:
            with open(labels_file_path, 'r') as f:
                labels_data = json.load(f)
            print(f"  Loaded existing labels from {labels_file_path}")
        except json.JSONDecodeError:
            print(f"  Warning: labels.json in {dir_path} is corrupted. Starting with empty labels.")
            labels_data = {}
    else:
        labels_data = {}
        print(f"  No existing labels.json found in {dir_path}. Creating a new one.")

    image_files = [f for f in os.listdir(full_dir_path) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS]
    
    if not image_files:
        print("  No image files found in this directory.")
        return

    processed_count = 0
    for image_filename in image_files:
        image_path = os.path.join(full_dir_path, image_filename)
        
        # Optional: Skip if already labeled and you don't want to overwrite
        # if image_filename in labels_data:
        #     print(f"  Skipping '{image_filename}', already has a label.")
        #     continue

        print(f"  Processing image: {image_filename}...")
        
        try:
            with open(image_path, "rb") as img_file:
                image_bytes = img_file.read()
            
            # Sanity check if it's a valid image using Pillow (optional but good)
            try:
                img = Image.open(io.BytesIO(image_bytes))
                img.verify()
            except Exception as pil_e:
                print(f"    Warning: Pillow could not verify image {image_filename}: {pil_e}. Skipping.")
                continue

            groq_label = await analyze_image_for_labeling(image_bytes)

            if groq_label:
                labels_data[image_filename] = {
                    "plat_nomor": groq_label["Plat_Nomor"],
                    "vehicle_type": groq_label["Vehicle_Type"]
                }
                print(f"    Groq labeled: Plat='{groq_label['Plat_Nomor']}', Type='{groq_label['Vehicle_Type']}'")
                processed_count +=1
            else:
                print(f"    Groq could not provide a valid label for {image_filename}.")

            # Be respectful to the API
            print(f"    Waiting for {API_CALL_DELAY_SECONDS} seconds...")
            time.sleep(API_CALL_DELAY_SECONDS)

        except FileNotFoundError:
            print(f"    Error: Image file not found at {image_path}")
        except Exception as e:
            print(f"    Error processing image {image_filename}: {e}")

    # Save updated labels
    try:
        with open(labels_file_path, 'w') as f:
            json.dump(labels_data, f, indent=4, sort_keys=True)
        print(f"  Successfully updated {labels_file_path} with {processed_count} new/updated labels.")
    except Exception as e:
        print(f"  Error writing labels to {labels_file_path}: {e}")


# --- Main Execution ---
async def main():
    if not groq_client:
        print("Groq client failed to initialize. Exiting.")
        return

    for directory in TARGET_DIRS:
        await process_directory(directory)
    
    print("\n--- Labeling Process Finished ---")
    print("Please review and correct the generated 'labels.json' files in each directory.")

if __name__ == "__main__":
    import asyncio
    # For Windows, you might need to set the event loop policy
    if os.name == 'nt':
         asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())