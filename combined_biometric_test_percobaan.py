#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skenario Percobaan 3: 
- Selenoid terbuka jika sidik jari benar DAN wajah benar
- Sidik jari benar tapi wajah tidak cocok, selenoid tidak merespon
- Sidik jari salah, kamera menangkap gambar dan disimpan ke folder unknown
"""

from pyfingerprint.pyfingerprint import PyFingerprint
import cv2
import numpy as np
import time
import sqlite3
import os
import pickle
import datetime

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

# Konfigurasi sensor sidik jari
PORT = '/dev/ttyUSB0'   # Ubah kalau port-nya beda
BAUDRATE = 57600

# Konfigurasi kamera
CAMERA_DEVICES = ['/dev/video1', '/dev/video2', 0]  # Coba /dev/video1, /dev/video2, kemudian indeks 0
CAMERA_ID = 0  # Default kamera

# Konfigurasi database dan embeddings
DB_PATH = 'biometrics.db'
EMBEDDINGS_PATH = 'embeddings.pkl'  # Path ke file embeddings ArcFace

# Konfigurasi folder untuk gambar wajah tidak dikenal
UNKNOWN_FOLDER = 'faces/unknown'

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
        lcd.display_message("Test Kombo", "Siap...")
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

# Pastikan folder unknown tersedia
os.makedirs(UNKNOWN_FOLDER, exist_ok=True)

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

def initialize_sensor():
    """Inisialisasi sensor sidik jari"""
    try:
        f = PyFingerprint(PORT, BAUDRATE, 0xFFFFFFFF, 0x00000000)
        if not f.verifyPassword():
            raise ValueError('Password sensor salah.')
        return f
    except Exception as e:
        print(f'[!] Gagal inisialisasi sensor: {e}')
        return None

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

def capture_unknown_face():
    """
    Menangkap gambar wajah tidak dikenal dan menyimpannya
    
    Returns:
        str/None: Path ke gambar yang disimpan, None jika gagal
    """
    # Inisialisasi kamera
    cap = initialize_camera()
    if not cap:
        print("[!] Gagal inisialisasi kamera untuk wajah tidak dikenal")
        return None
    
    print("[INFO] Mencoba menangkap wajah tidak dikenal...")
    display_lcd("Menangkap wajah", "tidak dikenal")
    
    # Buat timestamps untuk nama file
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Path untuk menyimpan gambar
    filename = f"unknown_{timestamp}.jpg"
    filepath = os.path.join(UNKNOWN_FOLDER, filename)
    
    # Mencoba mendapatkan gambar selama beberapa detik
    start_time = time.time()
    timeout = 5  # Batas waktu 5 detik
    face_detected = False
    saved_path = None
    
    while time.time() - start_time < timeout and not face_detected:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Deteksi wajah menggunakan MTCNN
        face_img, bbox = detect_face_mtcnn(frame)
        
        if bbox is not None:
            # Gambar kotak di sekitar wajah
            frame_with_box = draw_face_box(frame.copy(), bbox)
            
            # Tampilkan gambar
            cv2.imshow("Captured Unknown Face", frame_with_box)
            cv2.waitKey(1)
            
            # Simpan gambar
            cv2.imwrite(filepath, frame)
            print(f"[+] Gambar wajah tidak dikenal disimpan: {filepath}")
            face_detected = True
            saved_path = filepath
            
            # Tunggu sebentar untuk menampilkan hasil
            time.sleep(1)
    
    # Bersihkan sumber daya
    cap.release()
    cv2.destroyAllWindows()
    
    # Simpan ke database jika wajah terdeteksi
    if face_detected:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO unknown_faces (image_path, notes) 
            VALUES (?, ?)
            ''', (filepath, "Captured after failed fingerprint verification"))
            conn.commit()
            conn.close()
            print("[+] Data wajah tidak dikenal disimpan ke database")
        except Exception as e:
            print(f"[!] Gagal menyimpan ke database: {e}")
    
    return saved_path

def scan_fingerprint():
    """
    Memindai sidik jari dan mengembalikan ID pengguna jika dikenali
    
    Returns:
        int/None: ID pengguna jika sidik jari dikenali, None jika tidak
    """
    display_lcd("Test Sidik Jari", "Tempelkan jari")
    
    f = initialize_sensor()
    if not f:
        display_lcd("Sensor Error", "Coba lagi")
        return None

    print('[INFO] Menunggu scan sidik jari...')
    try:
        while not f.readImage():
            pass

        f.convertImage(0x01)
        result = f.searchTemplate()

        position_number = result[0]
        accuracy_score = result[1]

        if position_number == -1:
            print('[!] Sidik jari tidak dikenali.')
            display_lcd("Akses Ditolak", "Sidik jari asing")
            
            # Tangkap wajah untuk sidik jari yang tidak dikenali
            capture_unknown_face()
            
            return None
        else:
            print(f'[+] Dikenali! ID Fingerprint: {position_number}, Akurasi: {accuracy_score}')
            
            # Ambil data pengguna dari database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users WHERE fingerprint_id = ?", (position_number,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                print(f'[+] Pengguna: {user[1]} (ID: {user[0]})')
                display_lcd(f"Sidik jari OK", f"Scan wajah...")
                return user  # Return (user_id, user_name)
            else:
                print('[!] Data pengguna tidak ditemukan di database.')
                display_lcd("Data Error", "Kontak admin")
                return None

    except Exception as e:
        print(f'[!] Gagal saat scan: {e}')
        display_lcd("Sensor Error", "Coba lagi")
        return None

def verify_face(expected_user_name=None):
    """
    Verifikasi wajah pengguna dengan kamera
    
    Args:
        expected_user_name: Nama pengguna yang diharapkan (opsional)
        
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
                        # Jika ada expected_user_name, periksa apakah cocok
                        if expected_user_name and best_match_name != expected_user_name:
                            # Wajah teridentifikasi tapi sebagai orang yang berbeda
                            cv2.putText(frame, f"Tidak Cocok! {best_match_name} != {expected_user_name}", 
                                      (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        else:
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
    
    # Verifikasi nama pengguna jika diharapkan
    if verified and expected_user_name and user_name != expected_user_name:
        print(f"[!] Wajah terverifikasi tetapi sebagai pengguna yang salah: {user_name} (diharapkan: {expected_user_name})")
        display_lcd("User Berbeda", f"{user_name}")
        return False, user_name
    
    if verified:
        print(f"[+] Wajah terverifikasi untuk pengguna: {user_name}")
        display_lcd(f"Wajah OK", f"Selamat {user_name}")
        return True, user_name
    else:
        print(f"[!] Gagal memverifikasi wajah")
        display_lcd("Akses Ditolak", "Wajah tidak cocok")
        return False, None

def main():
    """Fungsi utama program percobaan"""
    # Tampilkan pesan selamat datang
    display_lcd("Test Percobaan 3", "Sistem Kombo")
    time.sleep(2)
    
    # Loop utama
    try:
        while True:
            print("\n[PERCOBAAN 3] Tes Kombinasi Biometrik")
            display_lcd("Tempelkan", "Sidik Jari")
            
            # Step 1: Scan sidik jari
            user_data = scan_fingerprint()
            
            if user_data is None:
                # Sidik jari tidak dikenali, gambar sudah diambil di fungsi scan_fingerprint
                print("[!] Sidik jari tidak dikenali. Kembali ke awal.")
                time.sleep(3)
                display_lcd("Test Percobaan 3", "Coba lagi")
                time.sleep(2)
                continue
            
            # User data adalah tuple (id, name)
            user_id, user_name = user_data
            
            # Step 2: Verifikasi wajah
            print("\n[STEP 2] Verifikasi Wajah")
            face_success, face_user_name = verify_face(user_name)
            
            if face_success and face_user_name == user_name:
                # Sidik jari dan wajah cocok
                print(f"[+] Verifikasi biometrik lengkap untuk: {user_name}")
                display_lcd(f"Akses Diterima", f"Selamat {user_name}")
                # Buka selenoid
                unlock_door()
            else:
                # Sidik jari cocok tapi wajah tidak
                print("[!] Sidik jari cocok tetapi wajah tidak terverifikasi")
                display_lcd("Akses Ditolak", "Wajah Tidak Cocok")
                # Tidak ada aksi selenoid
            
            # Tunggu sebentar
            time.sleep(3)
            
            # Reset tampilan
            display_lcd("Test Percobaan 3", "Sistem Kombo")
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