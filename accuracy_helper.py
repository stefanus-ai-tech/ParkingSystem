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

def calculate_character_accuracy(detected_text, true_text):
    """
    Menghitung akurasi karakter demi karakter.
    Returns dict dengan detail perbandingan setiap karakter.
    """
    # Normalize strings: lowercase dan hapus spasi
    detected_clean = detected_text.lower().replace(" ", "")
    true_clean = true_text.lower().replace(" ", "")
    
    # Buat list untuk menyimpan hasil perbandingan
    char_comparison = []
    correct_chars = 0
    total_chars = max(len(detected_clean), len(true_clean))
    
    # Iterasi setiap posisi karakter
    max_len = max(len(detected_clean), len(true_clean))
    
    for i in range(max_len):
        detected_char = detected_clean[i] if i < len(detected_clean) else None
        true_char = true_clean[i] if i < len(true_clean) else None
        
        is_correct = detected_char == true_char
        if is_correct and detected_char is not None:
            correct_chars += 1
            
        char_comparison.append({
            "position": i,
            "detected": detected_char,
            "true": true_char,
            "correct": is_correct
        })
    
    accuracy = (correct_chars / total_chars * 100) if total_chars > 0 else 0
    
    return {
        "accuracy": round(accuracy, 2),
        "correct_chars": correct_chars,
        "total_chars": total_chars,
        "char_details": char_comparison,
        "detected_clean": detected_clean,
        "true_clean": true_clean
    }

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
    Sekarang dengan analisis karakter demi karakter.
    """
    if not true_plate or not true_type:
        return {
            "plate_accuracy": 0,
            "type_accuracy": 0,
            "overall_accuracy": 0,
            "message": "Ground truth tidak ditemukan."
        }

    # Analisis karakter demi karakter untuk plat nomor
    plate_char_analysis = calculate_character_accuracy(groq_plate, true_plate)
    plate_acc = plate_char_analysis["accuracy"] / 100  # Convert to 0-1 scale
    
    # Analisis karakter demi karakter untuk tipe kendaraan
    type_char_analysis = calculate_character_accuracy(groq_type, true_type)
    type_acc = type_char_analysis["accuracy"] / 100  # Convert to 0-1 scale
    
    # Overall accuracy: rata-rata dari keduanya
    overall_acc = (plate_acc + type_acc) / 2
    
    # Exact match untuk referensi
    plate_exact_match = groq_plate.upper().replace(" ", "") == true_plate.upper().replace(" ", "")
    type_exact_match = groq_type.lower() == true_type.lower()
    
    return {
        "groq_plate": groq_plate,
        "groq_type": groq_type,
        "true_plate": true_plate,
        "true_type": true_type,
        "plate_accuracy": round(plate_acc * 100, 2),
        "type_accuracy": round(type_acc * 100, 2),
        "overall_accuracy": round(overall_acc * 100, 2),
        "plate_exact_match": plate_exact_match,
        "type_exact_match": type_exact_match,
        "plate_char_analysis": plate_char_analysis,
        "type_char_analysis": type_char_analysis,
        "detailed_comparison": {
            "plate_errors": [detail for detail in plate_char_analysis["char_details"] if not detail["correct"]],
            "type_errors": [detail for detail in type_char_analysis["char_details"] if not detail["correct"]]
        }
    }

def print_detailed_analysis(result):
    """
    Mencetak analisis detail hasil akurasi.
    """
    print(f"\n{'='*50}")
    print("DETAILED ACCURACY ANALYSIS")
    print(f"{'='*50}")
    
    print(f"\nGroq Plate: '{result['groq_plate']}'")
    print(f"True Plate: '{result['true_plate']}'")
    print(f"Plate Accuracy: {result['plate_accuracy']}%")
    print(f"Exact Match: {result['plate_exact_match']}")
    
    print(f"\nGroq Type: '{result['groq_type']}'")
    print(f"True Type: '{result['true_type']}'")
    print(f"Type Accuracy: {result['type_accuracy']}%")
    print(f"Exact Match: {result['type_exact_match']}")
    
    print(f"\nOverall Accuracy: {result['overall_accuracy']}%")
    
    # Detail karakter plat nomor
    print(f"\n{'-'*30}")
    print("PLATE CHARACTER ANALYSIS:")
    print(f"Clean Detected: '{result['plate_char_analysis']['detected_clean']}'")
    print(f"Clean True:     '{result['plate_char_analysis']['true_clean']}'")
    print(f"Correct chars: {result['plate_char_analysis']['correct_chars']}/{result['plate_char_analysis']['total_chars']}")
    
    if result['detailed_comparison']['plate_errors']:
        print("Plate Errors:")
        for error in result['detailed_comparison']['plate_errors']:
            detected = error['detected'] or 'MISSING'
            true = error['true'] or 'EXTRA'
            print(f"  Position {error['position']}: Got '{detected}' but expected '{true}'")
    
    # Detail karakter tipe kendaraan
    print(f"\n{'-'*30}")
    print("TYPE CHARACTER ANALYSIS:")
    print(f"Clean Detected: '{result['type_char_analysis']['detected_clean']}'")
    print(f"Clean True:     '{result['type_char_analysis']['true_clean']}'")
    print(f"Correct chars: {result['type_char_analysis']['correct_chars']}/{result['type_char_analysis']['total_chars']}")
    
    if result['detailed_comparison']['type_errors']:
        print("Type Errors:")
        for error in result['detailed_comparison']['type_errors']:
            detected = error['detected'] or 'MISSING'
            true = error['true'] or 'EXTRA'
            print(f"  Position {error['position']}: Got '{detected}' but expected '{true}'")

# Example usage:
# if __name__ == "__main__":
#     # Test dengan contoh data
#     test_groq_plate = "B 1234 ABC"
#     test_groq_type = "car"
#     test_true_plate = "B 1234 ABD"  # Ada error di karakter terakhir
#     test_true_type = "motorcycle"   # Ada error di tipe
    
#     result = calculate_accuracy(test_groq_plate, test_groq_type, test_true_plate, test_true_type)
#     print_detailed_analysis(result)