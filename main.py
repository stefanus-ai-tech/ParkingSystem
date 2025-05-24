import os
import json
import base64
import time # <--- Add this import
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from groq import Groq
from PIL import Image # Untuk validasi gambar
import io

# Impor fungsi dari modul lain
from vehicleIn import process_entry, load_parking_data as load_current_parking_data
from vehicleOut import process_exit
from accuracy_helper import calculate_accuracy, get_ground_truth, get_labeled_image_paths, LABELED_CAR_DIR, LABELED_MOTORCYCLE_DIR

# Load environment variables dari .env
load_dotenv()

# Inisialisasi FastAPI app
app = FastAPI()

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Atau spesifikasikan domain frontend Anda
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Groq Client
try:
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    if not os.environ.get("GROQ_API_KEY"):
        print("PERINGATAN: GROQ_API_KEY tidak ditemukan di .env. Fungsi deteksi plat tidak akan bekerja.")
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    groq_client = None


# Mount static files (untuk frontend HTML, CSS, JS dan gambar yang dilabeli)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/choosenCar", StaticFiles(directory=LABELED_CAR_DIR), name="choosenCar")
app.mount("/choosenMotorCycle", StaticFiles(directory=LABELED_MOTORCYCLE_DIR), name="choosenMotorCycle")


# --- Helper Groq ---
async def analyze_image_with_groq(image_bytes: bytes):
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq client tidak terinisialisasi. Cek API Key.")

    # Encode image to base64
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')
    
    start_time = time.time() # <--- Record start time

    chat_completion = groq_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analisa gambar ini dan identifikasi jenis kendaraan (Mobil atau Motor) dan plat nomornya. "
                                "Jika plat nomor tidak terbaca jelas atau tidak ada, tulis 'TIDAK_TERDETEKSI'. "
                                "Jika jenis kendaraan tidak jelas, tulis 'TIDAK_DIKETAHUI'. "
                                "Format output JSON: {\"Vehicle_Type\": \"<jenis>\", \"Plat_Nomor\": \"<plat>\"}."
                                "Pastikan plat nomor hanya mengandung huruf dan angka, tanpa spasi berlebih atau karakter aneh."
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
    )
    
    end_time = time.time() # <--- Record end time
    inference_time_seconds = round(end_time - start_time, 3) # <--- Calculate duration

    response_content = chat_completion.choices[0].message.content
    # print(f"Raw Groq Response: {response_content}") 
    try:
        # Mencoba membersihkan dan parsing JSON
        # Llama Vision mungkin tidak selalu menghasilkan JSON yang sempurna, perlu pre-processing
        json_part = response_content
        if "```json" in response_content:
            json_part = response_content.split("```json")[1].split("```")[0].strip()
        
        data = json.loads(json_part)
        
        # Normalisasi hasil
        plat = data.get("Plat_Nomor", "TIDAK_TERDETEKSI").upper().replace(" ", "")
        tipe = data.get("Vehicle_Type", "TIDAK_DIKETAHUI").capitalize()
        if tipe not in ["Mobil", "Motor"]:
            tipe = "TIDAK_DIKETAHUI"

        return {
            "Vehicle_Type": tipe, 
            "Plat_Nomor": plat,
            "inference_time_seconds": inference_time_seconds # <--- Include inference time
        }
    except (json.JSONDecodeError, AttributeError, IndexError) as e:
        print(f"Error parsing Groq JSON response: {e}, Content: {response_content}")
        return {
            "Vehicle_Type": "ERROR_PARSING", 
            "Plat_Nomor": "ERROR_PARSING",
            "inference_time_seconds": inference_time_seconds # <--- Still return time even on parse error
        }


# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    # Menyajikan file index.html dari folder static
    html_file_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(html_file_path):
        with open(html_file_path, 'r') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend tidak ditemukan</h1>")


@app.post("/process_image/")
async def process_image_endpoint(
    action_type: str = Form(...),  # 'in' atau 'out'
    image_file: UploadFile = File(None), # Bisa None jika pakai labeled_image_name
    labeled_image_name: str = Form(None) # Nama file gambar dari folder berlabel
):
    image_bytes = None
    actual_image_filename_for_gt = None # Nama file untuk dicocokkan dengan ground truth

    if labeled_image_name and labeled_image_name != "none":
        # Jika gambar berlabel dipilih, gunakan itu
        # Path harus relatif terhadap direktori root proyek
        # Contoh: labeled_image_name bisa "choosenCar/car1_B1234ABC.jpg"
        image_path = os.path.join(BASE_DIR, labeled_image_name)
        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail=f"Gambar berlabel {labeled_image_name} tidak ditemukan.")
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        actual_image_filename_for_gt = os.path.basename(labeled_image_name)
    elif image_file:
        # Jika file baru diupload
        # Validasi tipe file sederhana
        if image_file.content_type not in ["image/jpeg", "image/png", "image/gif"]:
            raise HTTPException(status_code=400, detail="Format file tidak didukung. Harap unggah JPG, PNG, atau GIF.")
        
        # Validasi ukuran file (misal, maks 5MB)
        MAX_SIZE = 5 * 1024 * 1024 
        contents = await image_file.read()
        if len(contents) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="Ukuran file terlalu besar. Maksimum 5MB.")
        
        # Cek apakah file benar-benar gambar
        try:
            img = Image.open(io.BytesIO(contents))
            img.verify() # Verifikasi dasar
        except Exception:
            raise HTTPException(status_code=400, detail="File yang diunggah bukan gambar yang valid.")
        
        image_bytes = contents # Gunakan lagi contents yang sudah dibaca
        actual_image_filename_for_gt = image_file.filename # Untuk kasus jika user mengunggah file dari choosenCar/MotorCycle
    else:
        raise HTTPException(status_code=400, detail="Tidak ada gambar yang diunggah atau dipilih.")

    groq_analysis_result = None # Initialize
    try:
        groq_analysis_result = await analyze_image_with_groq(image_bytes) # <--- Store the whole result
    except HTTPException as e: 
        return JSONResponse(status_code=e.status_code, content={"status": "error", "message": e.detail})
    except Exception as e:
        print(f"Error saat analisa Groq: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Gagal menganalisa gambar dengan Groq: {str(e)}"})

    # The groq_analysis_result now contains Vehicle_Type, Plat_Nomor, and inference_time_seconds
    # print(f"Groq Analysis Result: {groq_analysis_result}") # For debugging

    if groq_analysis_result["Vehicle_Type"] == "ERROR_PARSING" or groq_analysis_result["Plat_Nomor"] == "ERROR_PARSING":
        return JSONResponse(status_code=500, content={
            "status": "error", 
            "message": "Gagal memparsing hasil dari Groq.",
            "groq_result": groq_analysis_result # Send the result which includes time
        })
    
    if groq_analysis_result["Plat_Nomor"] == "TIDAK_TERDETEKSI" or groq_analysis_result["Vehicle_Type"] == "TIDAK_DIKETAHUI":
         return JSONResponse(status_code=400, content={
            "status": "error", 
            "message": "Plat nomor atau jenis kendaraan tidak dapat dideteksi oleh Groq.",
            "groq_result": groq_analysis_result # Send the result which includes time
        })

    plat_nomor = groq_analysis_result["Plat_Nomor"]
    vehicle_type = groq_analysis_result["Vehicle_Type"]

    # Proses berdasarkan action_type
    if action_type == "in":
        result = process_entry(plat_nomor, vehicle_type)
    elif action_type == "out":
        result = process_exit(plat_nomor, vehicle_type) # Kirim vehicle_type hasil deteksi
    else:
        raise HTTPException(status_code=400, detail="Action type tidak valid.")

    # Kalkulasi akurasi jika gambar yang diproses adalah gambar yang dilabeli
    accuracy_info = None
    if actual_image_filename_for_gt: # Cek apakah kita punya nama file untuk dicari labelnya
        ground_truth = get_ground_truth(actual_image_filename_for_gt)
        if ground_truth:
            accuracy_info = calculate_accuracy(
                plat_nomor, vehicle_type,
                ground_truth["plat_nomor"], ground_truth["vehicle_type"]
            )
        else:
             accuracy_info = {"message": f"Tidak ada label ditemukan untuk {actual_image_filename_for_gt}. Akurasi tidak dihitung."}


    # Gabungkan hasil proses dengan info Groq dan akurasi
    final_response = {
        **result, 
        "groq_result": { # Nest Groq specific results under groq_result key
            "Plat_Nomor": plat_nomor,
            "Vehicle_Type": vehicle_type,
            "inference_time_seconds": groq_analysis_result.get("inference_time_seconds") # Add it here
        }
    }
    if accuracy_info:
        final_response["accuracy_info"] = accuracy_info
    
    return JSONResponse(content=final_response)

@app.get("/parking_data")
async def get_parking_data():
    """Mengembalikan semua data parkir saat ini."""
    return JSONResponse(content=load_current_parking_data())

@app.get("/labeled_images")
async def get_list_of_labeled_images():
    """Mengembalikan daftar file gambar yang sudah dilabeli."""
    return JSONResponse(content={"images": get_labeled_image_paths()})


# Untuk menjalankan aplikasi: uvicorn main:app --reload
if __name__ == "__main__":
    import uvicorn
    # Pastikan BASE_DIR sudah terdefinisi di scope global
    static_dir = os.path.join(BASE_DIR, "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir) # Buat folder static jika belum ada
        print(f"Folder 'static' dibuat di {static_dir}")
    
    # Buat file parking_data.json kosong jika belum ada
    parking_file = os.path.join(BASE_DIR, "parking_data.json")
    if not os.path.exists(parking_file):
        with open(parking_file, "w") as f:
            json.dump({}, f)
        print(f"File 'parking_data.json' dibuat di {parking_file}")
        
    # Buat folder choosenCar dan ChoosenMotorCycle jika belum ada
    for folder in [LABELED_CAR_DIR, LABELED_MOTORCYCLE_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Folder '{os.path.basename(folder)}' dibuat di {folder}")
            # Buat file labels.json kosong di dalamnya
            with open(os.path.join(folder, "labels.json"), "w") as f:
                json.dump({}, f)
            print(f"File 'labels.json' kosong dibuat di {os.path.join(folder, 'labels.json')}")


    print(f"Aplikasi akan berjalan. Akses di http://127.0.0.1:8001")
    print(f"Pastikan file frontend (index.html, style.css, script.js) ada di folder: {static_dir}")
    uvicorn.run(app, host="0.0.0.0", port=8001)
