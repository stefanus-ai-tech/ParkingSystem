import json
import os
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LABELED_CAR_DIR = os.path.join(BASE_DIR, "choosenCar")
LABELED_MOTORCYCLE_DIR = os.path.join(BASE_DIR, "choosenMotorCycle")

def load_labels(directory):
    labels_path = os.path.join(directory, "labels.json")
    if os.path.exists(labels_path):
        with open(labels_path, 'r') as f:
            return json.load(f)
    return {}

CAR_LABELS = load_labels(LABELED_CAR_DIR)
MOTORCYCLE_LABELS = load_labels(LABELED_MOTORCYCLE_DIR)
ALL_LABELS = {**CAR_LABELS, **MOTORCYCLE_LABELS} # Combine labels

def get_ground_truth(image_filename):
    """
    Mendapatkan ground truth dari ALL_LABELS berdasarkan nama file.
    """
    return ALL_LABELS.get(image_filename)

def get_labeled_image_paths():
    """
    Mengembalikan daftar path relatif untuk gambar yang dilabeli.
    """
    car_images = [os.path.join("choosenCar", f) for f in CAR_LABELS.keys()]
    motorcycle_images = [os.path.join("choosenMotorCycle", f) for f in MOTORCYCLE_LABELS.keys()]
    return car_images + motorcycle_images


def calculate_plate_similarity(str1, str2):
    """
    Menghitung kemiripan antara dua string plat nomor (0.0 hingga 1.0).
    Mengabaikan spasi dan case.
    """
    s1 = "".join(str1.split()).upper()
    s2 = "".join(str2.split()).upper()
    return SequenceMatcher(None, s1, s2).ratio()

def calculate_accuracy(groq_plate, groq_type, true_plate, true_type):
    """
    Menghitung akurasi berdasarkan output Groq dan ground truth.
    """
    if not true_plate or not true_type:
        return {
            "plate_accuracy": 0,
            "type_accuracy": 0,
            "overall_accuracy": 0,
            "message": "Ground truth tidak ditemukan."
        }

    plate_acc = 1 if groq_plate.upper().replace(" ", "") == true_plate.upper().replace(" ", "") else 0
    # Atau gunakan similarity untuk plat:
    # plate_acc = calculate_plate_similarity(groq_plate, true_plate)

    type_acc = 1 if groq_type.lower() == true_type.lower() else 0
    
    overall_acc = 1 if plate_acc == 1 and type_acc == 1 else 0
    
    return {
        "groq_plate": groq_plate,
        "groq_type": groq_type,
        "true_plate": true_plate,
        "true_type": true_type,
        "plate_accuracy": round(plate_acc * 100, 2),
        "type_accuracy": round(type_acc * 100, 2),
        "overall_accuracy": round(overall_acc * 100, 2)
    }