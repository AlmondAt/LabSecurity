#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skenario Percobaan 2: 
Selenoid merespon jika deteksi wajah benar, jika tidak tidak terjadi apa2, 
LCD menampilkan benar dan tidaknya.
"""

import cv2
import numpy as np
import time
import sqlite3
import os
import pickle

# Import modul selenoid dan LCD
try:
    from selenoid_utils import Selenoid
    SELENOID_AVAILABLE = True
except ImportError:
    print("[!] Modul selenoid tidak tersedia. Simulasi akan digunakan.")
    SELENOID_AVAILABLE = False

try:
    from lcd_utils import LCD
    LCD_AVAILABLE = True
except ImportError:
    print("[!] Modul LCD tidak tersedia. Output akan ditampilkan di console.")
    LCD_AVAILABLE = False

# Import modul face recognition
try:
    from mtcnn_utils import detect_face_mtcnn, draw_face_box
    from arcface_utils import preprocess_face, extract_embedding, compute_similarity, load_embeddings
    from head_pose import calculate_face_orientation, is_face_frontal
    ARCFACE_AVAILABLE = True
except ImportError as e:
    print(f"[!] Modul pengenalan wajah tidak tersedia: {e}")
    ARCFACE_AVAILABLE = False

# Konfigurasi kamera
CAMERA_DEVICES = ['/dev/video1', '/dev/video2', 0]  # Coba /dev/video1, /dev/video2, kemudian indeks 0
CAMERA_ID = 0  # Default kamera

# Konfigurasi database dan embeddings
DB_PATH = 'biometrics.db'
EMBEDDINGS_PATH = 'embeddings.pkl'  # Path ke file embeddings ArcFace

# Konfigurasi selenoid
SELENOID_PIN = 18  # GPIO pin untuk selenoid
UNLOCK_DURATION = 5  # Durasi membuka selenoid (detik)

# Konfigurasi threshold
FACE_RECOGNITION_THRESHOLD = 0.6  # Threshold untuk kecocokan wajah (0-1)

# Inisialisasi LCD
lcd = None
if LCD_AVAILABLE:
    try:
        lcd = LCD()
        lcd.init()
        lcd.clear()
        lcd.display_message("Test Wajah", "Siap...")
        time.sleep(2)
    except Exception as e:
        print(f"[!] Gagal inisialisasi LCD: {e}")
        LCD_AVAILABLE = False

# Inisialisasi selenoid
selenoid = None
if SELENOID_AVAILABLE:
    try:
        selenoid = Selenoid(SELENOID_PIN)
        selenoid.init()
    except Exception as e:
        print(f"[!] Gagal inisialisasi selenoid: {e}")
        SELENOID_AVAILABLE = False

def display_lcd(line1, line2=""):
    """Tampilkan pesan ke LCD jika tersedia"""
    if LCD_AVAILABLE and lcd:
        try:
            lcd.display_message(line1, line2)
        except Exception as e:
            print(f"[!] Error LCD: {e}")
            print(f"{line1} - {line2}")
    else:
        print(f"{line1} - {line2}")

def unlock_door():
    """Membuka selenoid jika tersedia"""
    if SELENOID_AVAILABLE and selenoid:
        try:
            print("[+] Membuka selenoid...")
            selenoid.unlock(UNLOCK_DURATION)
            return True
        except Exception as e:
            print(f"[!] Gagal membuka selenoid: {e}")
    else:
        print("[+] Simulasi: Selenoid terbuka")
        time.sleep(UNLOCK_DURATION)
        print("[+] Simulasi: Selenoid tertutup kembali")
    return False

def initialize_camera():
    """Inisialisasi kamera untuk pengenalan wajah"""
    try:
        # Coba setiap kemungkinan perangkat kamera
        for device in CAMERA_DEVICES:
            print(f"[INFO] Mencoba membuka kamera: {device}")
            try:
                cap = cv2.VideoCapture(device)
                if cap.isOpened():
                    print(f"[INFO] Berhasil membuka kamera: {device}")
                    return cap
                else:
                    print(f"[INFO] Gagal membuka kamera: {device}")
                    cap.release()
            except Exception as e:
                print(f"[INFO] Error saat membuka kamera {device}: {e}")
        
        # Jika semua gagal, coba indeks default sebagai fallback
        print(f"[INFO] Mencoba kamera default (indeks 0)")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise ValueError("Tidak dapat membuka kamera manapun")
        return cap
    except Exception as e:
        print(f"[!] Gagal inisialisasi kamera: {e}")
        return None

def verify_face():
    """
    Verifikasi wajah pengguna dengan kamera
    
    Returns:
        tuple: (success, user_name) jika berhasil, (False, None) jika gagal
    """
    # Periksa apakah modul ArcFace tersedia
    if not ARCFACE_AVAILABLE:
        print("[!] Modul pengenalan wajah tidak tersedia")
        display_lcd("Error Modul", "Wajah")
        return False, None
    
    # Muat database embeddings wajah
    try:
        embeddings_dict = load_embeddings(EMBEDDINGS_PATH)
        if not embeddings_dict:
            print("[!] File embeddings kosong atau tidak tersedia")
            display_lcd("Data Wajah", "Tidak tersedia")
            return False, None
    except Exception as e:
        print(f"[!] Gagal memuat embeddings: {e}")
        display_lcd("Error Data", "Wajah")
        return False, None
    
    # Inisialisasi kamera
    cap = initialize_camera()
    if not cap:
        display_lcd("Kamera Error", "Coba lagi")
        return False, None
    
    display_lcd("Scan Wajah", "Lihat ke kamera")
    
    # Pengaturan timeout dan threshold
    verified = False
    user_name = None
    start_time = time.time()
    timeout = 15  # Timeout setelah 15 detik
    
    print("[INFO] Posisikan wajah Anda di depan kamera untuk verifikasi...")
    
    while time.time() - start_time < timeout and not verified:
        ret, frame = cap.read()
        if not ret:
            continue
            
        # Deteksi wajah
        face_img, bbox = detect_face_mtcnn(frame)
        
        if bbox is not None:
            # Tampilkan kotak di sekitar wajah
            frame = draw_face_box(frame, bbox)
            
            # Proses wajah dan ekstrak embedding
            face_tensor = preprocess_face(face_img)
            if face_tensor is not None:
                # Hitung orientasi wajah
                pitch, yaw, roll = calculate_face_orientation(bbox, frame.shape)
                frontal = is_face_frontal(pitch, yaw, roll)
                
                # Verifikasi hanya dilakukan jika wajah frontal
                if frontal:
                    # Ekstrak embedding
                    embedding = extract_embedding(face_tensor)
                    
                    # Cari kecocokan terbaik
                    best_match_name = None
                    best_match_score = 0
                    
                    for name, embeddings_list in embeddings_dict.items():
                        for ref_embedding in embeddings_list:
                            similarity = compute_similarity(embedding, ref_embedding)
                            
                            if similarity > best_match_score:
                                best_match_score = similarity
                                best_match_name = name
                    
                    # Tampilkan hasil kecocokan
                    if best_match_score >= FACE_RECOGNITION_THRESHOLD:
                        # Tampilkan hasil positif
                        cv2.putText(frame, f"{best_match_name}: {best_match_score:.2f}", 
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                        cv2.putText(frame, "TERVERIFIKASI!", (frame.shape[1] - 200, 30), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                        verified = True
                        user_name = best_match_name
                    else:
                        # Tampilkan hasil negatif
                        cv2.putText(frame, f"Unknown: {best_match_score:.2f}", 
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Tampilkan waktu tersisa
        remaining = int(timeout - (time.time() - start_time))
        cv2.putText(frame, f"Waktu: {remaining}s", (10, frame.shape[0] - 10), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Tampilkan frame
        cv2.imshow("Verifikasi Wajah", frame)
        if cv2.waitKey(1) == 27:  # ESC untuk keluar
            break
    
    # Bersihkan sumber daya
    cap.release()
    cv2.destroyAllWindows()
    
    if verified:
        print(f"[+] Wajah terverifikasi untuk pengguna: {user_name}")
        display_lcd(f"Akses Diterima", f"Selamat {user_name}")
        return True, user_name
    else:
        print(f"[!] Gagal memverifikasi wajah")
        display_lcd("Akses Ditolak", "Wajah tidak cocok")
        return False, None

def main():
    """Fungsi utama program percobaan"""
    # Tampilkan pesan selamat datang
    display_lcd("Test Percobaan 2", "Scan Wajah")
    time.sleep(2)
    
    # Loop utama
    try:
        while True:
            print("\n[PERCOBAAN 2] Tes Verifikasi Wajah")
            display_lcd("Deteksi Wajah", "Siap...")
            time.sleep(1)
            
            # Verifikasi wajah
            success, user_name = verify_face()
            
            if success:
                # Wajah dikenali
                print(f"[+] Wajah dikenali: {user_name}")
                # Buka selenoid karena wajah dikenali
                unlock_door()
                time.sleep(3)
            else:
                # Wajah tidak dikenali
                print("[!] Wajah tidak dikenali")
                # Tidak ada aksi selenoid
                time.sleep(3)
            
            # Reset tampilan
            display_lcd("Test Percobaan 2", "Scan Wajah")
            
            # Tunggu sebentar sebelum memulai scan baru
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n[!] Program dihentikan oleh pengguna")
    except Exception as e:
        print(f"\n[!] Error: {e}")
    finally:
        # Bersihkan sumber daya
        if LCD_AVAILABLE and lcd:
            lcd.clear()
            lcd.display_message("Program", "Selesai")
        if SELENOID_AVAILABLE and selenoid:
            selenoid.cleanup()
        print("[+] Program selesai.")

if __name__ == "__main__":
    main() 