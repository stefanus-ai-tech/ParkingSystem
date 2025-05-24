import datetime
import json
import math
import os

# Menggunakan fungsi load/save dari vehicleIn agar konsisten
from vehicleIn import load_parking_data, save_parking_data

def calculate_fee(minutes: int, vehicle_type: str):
    """
    Fungsi untuk menghitung biaya parkir berdasarkan durasi dan jenis kendaraan.
    """
    if vehicle_type == "Mobil":
        if minutes <= 60:  # Biaya Rp 5.000 untuk jam pertama
            return 5000
        else:
            # 5000 untuk jam pertama + (ceil((total_menit - 60) / 60) * 2000) untuk jam berikutnya
            additional_hours = math.ceil((minutes - 60) / 60)
            return 5000 + additional_hours * 2000
    elif vehicle_type == "Motor":
        # Rp 2.000 per jam, pembulatan ke atas
        return math.ceil(minutes / 60) * 2000
    return 0

def process_exit(plat_nomor: str, detected_vehicle_type: str): # Tambahkan detected_vehicle_type
    """
    Memproses keluarnya kendaraan.
    Menghitung durasi, biaya, dan memperbarui parking_data.json.
    """
    parking_data = load_parking_data()
    plat_nomor_cleaned = plat_nomor.upper().replace(" ", "")

    if plat_nomor_cleaned not in parking_data or parking_data[plat_nomor_cleaned].get("exit_time") is not None:
        return {
            "status": "error",
            "message": f"Kendaraan dengan plat nomor {plat_nomor} tidak ditemukan terparkir atau sudah keluar."
        }

    record = parking_data[plat_nomor_cleaned]
    # Gunakan vehicle_type yang tercatat saat masuk untuk kalkulasi biaya, bukan yang baru terdeteksi
    # Ini penting jika deteksi saat keluar salah tipe kendaraannya
    vehicle_type_at_entry = record["vehicle_type"] 

    try:
        entry_time = datetime.datetime.fromisoformat(record["entry_time"])
    except ValueError:
         return {
            "status": "error",
            "message": f"Format waktu masuk tidak valid untuk plat {plat_nomor}."
        }

    exit_time = datetime.datetime.now()
    duration_seconds = (exit_time - entry_time).total_seconds()
    duration_minutes = int(duration_seconds / 60)
    #duration_minutes = int(math.ceil(600))  # Buat debugging lebih mudah, pakai 600 menit

    fee = calculate_fee(duration_minutes, vehicle_type_at_entry)

    record["exit_time"] = exit_time.isoformat()
    record["fee"] = fee
    record["duration_minutes"] = duration_minutes
    
    # Jika deteksi jenis kendaraan saat keluar berbeda, bisa dicatat atau diabaikan
    # Untuk saat ini, kita pakai yang dari entry untuk konsistensi biaya
    if vehicle_type_at_entry.lower() != detected_vehicle_type.lower():
        print(f"Peringatan: Tipe kendaraan terdeteksi saat keluar ({detected_vehicle_type}) berbeda dengan saat masuk ({vehicle_type_at_entry}) untuk plat {plat_nomor}.")


    save_parking_data(parking_data)
    return {
        "status": "success",
        "message": f"Kendaraan {vehicle_type_at_entry} dengan plat {plat_nomor} berhasil keluar.",
        "plat_nomor": plat_nomor,
        "vehicle_type": vehicle_type_at_entry, # Tampilkan tipe saat masuk
        "entry_time": record["entry_time"],
        "exit_time": record["exit_time"],
        "duration_minutes": duration_minutes,
        "fee_rupiah": fee
    }