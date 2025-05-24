import datetime
import json
import os

PARKING_DATA_FILE = "parking_data.json"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARKING_DATA_PATH = os.path.join(BASE_DIR, PARKING_DATA_FILE)


def load_parking_data():
    if not os.path.exists(PARKING_DATA_PATH):
        return {}
    try:
        with open(PARKING_DATA_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {} # Return empty if file is corrupted or empty

def save_parking_data(data):
    with open(PARKING_DATA_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def process_entry(plat_nomor: str, vehicle_type: str):
    """
    Memproses masuknya kendaraan.
    Mencatat waktu masuk ke parking_data.json.
    """
    parking_data = load_parking_data()
    plat_nomor_cleaned = plat_nomor.upper().replace(" ", "")

    if plat_nomor_cleaned in parking_data and parking_data[plat_nomor_cleaned].get("exit_time") is None:
        return {
            "status": "error",
            "message": f"Kendaraan dengan plat nomor {plat_nomor} sudah terparkir.",
            "entry_time": parking_data[plat_nomor_cleaned]["entry_time"]
        }

    entry_time = datetime.datetime.now().isoformat()
    parking_data[plat_nomor_cleaned] = {
        "vehicle_type": vehicle_type,
        "entry_time": entry_time,
        "exit_time": None,
        "fee": None,
        "original_plat": plat_nomor # Simpan plat asli untuk display
    }
    save_parking_data(parking_data)
    return {
        "status": "success",
        "message": f"Kendaraan {vehicle_type} dengan plat {plat_nomor} berhasil masuk.",
        "plat_nomor": plat_nomor,
        "vehicle_type": vehicle_type,
        "entry_time": entry_time
    }