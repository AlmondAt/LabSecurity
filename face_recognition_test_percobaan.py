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
import argparse  # Tambahkan import argparse

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
CAMERA_DEVICES = [2, 1, 0]  # Coba /dev/video1, /dev/video2, kemudian indeks 0
CAMERA_ID = 0  # Default kamera

# Konfigurasi database dan embeddings
DB_PATH = 'biometrics.db'
EMBEDDINGS_PATH = 'embeddings.pkl'  # Path ke file embeddings ArcFace

# Konfigurasi selenoid
SELENOID_PIN = 18  # GPIO pin untuk selenoid
UNLOCK_DURATION = 5  # Durasi membuka selenoid (detik)

# Konfigurasi threshold
FACE_RECOGNITION_THRESHOLD = 0.55  # Threshold default diturunkan untuk meningkatkan tingkat pengenalan

# Parsing argumen command line
def parse_arguments():
    """Parse argumen command line"""
    parser = argparse.ArgumentParser(description='Program Pengenalan Wajah dengan ArcFace')
    parser.add_argument('--threshold', type=float, default=FACE_RECOGNITION_THRESHOLD, 
                        help=f'Threshold untuk kecocokan wajah (0-1, default: {FACE_RECOGNITION_THRESHOLD})')
    parser.add_argument('--resolution', type=str, choices=['480p', '720p'], default='480p',
                        help='Resolusi kamera (480p atau 720p, default: 480p)')
    parser.add_argument('--fps', type=int, default=15,
                        help='Frame rate kamera (5-30, default: 15)')
    parser.add_argument('--camera', type=int, default=None,
                        help='Indeks kamera yang digunakan (default: coba 2, 1, 0)')
    parser.add_argument('--embeddings', type=str, default=EMBEDDINGS_PATH,
                        help=f'Path file embedding (default: {EMBEDDINGS_PATH})')
    return parser.parse_args()

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

def initialize_camera(resolution="480p", fps=15):
    """
    Inisialisasi kamera untuk pengenalan wajah
    
    Args:
        resolution (str): Resolusi yang diinginkan ("480p" atau "720p")
        fps (int): Frame rate yang diinginkan
    
    Returns:
        cv2.VideoCapture: Objek kamera yang sudah diinisialisasi
    """
    try:
        # Tentukan pengaturan resolusi
        if resolution == "720p":
            width, height = 1280, 720
        else:  # 480p default
            width, height = 640, 480
            
        print(f"[INFO] Mencoba dengan pengaturan {width}x{height} @ {fps} FPS, format MJPEG")
            
        # Coba setiap kemungkinan perangkat kamera
        for device in CAMERA_DEVICES:
            print(f"[INFO] Mencoba membuka kamera: {device}")
            try:
                cap = cv2.VideoCapture(device)
                if cap.isOpened():
                    print(f"[INFO] Berhasil membuka kamera: {device}")
                    
                    # Atur properti kamera untuk stabilitas
                    # Atur format ke MJPEG
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
                    
                    # Atur resolusi
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    
                    # Atur FPS
                    cap.set(cv2.CAP_PROP_FPS, fps)
                    
                    # Coba membaca frame pertama untuk verifikasi kamera bekerja
                    ret, test_frame = cap.read()
                    if not ret or test_frame is None or test_frame.size == 0:
                        print(f"[INFO] Kamera {device} terbuka tetapi tidak dapat membaca frame. Mencoba dengan pengaturan alternatif...")
                        
                        # Coba resolusi alternatif jika menggunakan resolusi 720p
                        if resolution == "720p":
                            print("[INFO] Mencoba beralih ke 480p...")
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            ret, test_frame = cap.read()
                            if not ret or test_frame is None:
                                cap.release()
                                continue
                        else:
                            # Jika sudah 480p, coba resolusi 720p
                            print("[INFO] Mencoba beralih ke 720p...")
                            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                            ret, test_frame = cap.read()
                            if not ret or test_frame is None:
                                cap.release()
                                continue
                    
                    # Menampilkan informasi resolusi kamera yang sebenarnya
                    height, width = test_frame.shape[:2]
                    print(f"[INFO] Resolusi kamera aktual: {width}x{height}")
                    
                    # Baca frame kedua untuk verifikasi
                    ret, test_frame = cap.read()
                    if not ret:
                        print(f"[INFO] Kamera {device} tidak dapat membaca frame kedua. Mencoba kamera lain...")
                        cap.release()
                        continue
                        
                    print(f"[INFO] Kamera {device} siap digunakan")
                    
                    # Tambahkan delay untuk stabilisasi kamera
                    time.sleep(0.5)
                    
                    # Tampilkan informasi properti kamera
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    format_code = int(cap.get(cv2.CAP_PROP_FOURCC))
                    format_str = chr(format_code & 0xFF) + chr((format_code >> 8) & 0xFF) + chr((format_code >> 16) & 0xFF) + chr((format_code >> 24) & 0xFF)
                    print(f"[INFO] Properti kamera: {width}x{height}, {fps} FPS, Format: {format_str}")
                    
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
            
        # Atur properti kamera default
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Verifikasi kamera default
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            # Coba pengaturan alternatif
            if resolution == "720p":
                print("[INFO] Mencoba kamera default dengan 480p...")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            else:
                print("[INFO] Mencoba kamera default dengan 720p...")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                
            ret, test_frame = cap.read()
            if not ret or test_frame is None:
                raise ValueError("Kamera default tidak dapat membaca frame")
        
        # Menampilkan informasi resolusi kamera default
        height, width = test_frame.shape[:2]
        fps = cap.get(cv2.CAP_PROP_FPS)
        format_code = int(cap.get(cv2.CAP_PROP_FOURCC))
        format_str = chr(format_code & 0xFF) + chr((format_code >> 8) & 0xFF) + chr((format_code >> 16) & 0xFF) + chr((format_code >> 24) & 0xFF)
        print(f"[INFO] Properti kamera default: {width}x{height}, {fps} FPS, Format: {format_str}")
            
        print("[INFO] Menggunakan kamera default")
        return cap
    except Exception as e:
        print(f"[!] Gagal inisialisasi kamera: {e}")
        return None

def verify_face(threshold=FACE_RECOGNITION_THRESHOLD, resolution="480p", fps=15, 
                camera_devices=CAMERA_DEVICES, embeddings_path=EMBEDDINGS_PATH):
    """
    Verifikasi wajah pengguna dengan kamera
    
    Args:
        threshold (float): Threshold untuk pengenalan wajah (0-1)
        resolution (str): Resolusi kamera yang diinginkan
        fps (int): Frame rate kamera yang diinginkan
        camera_devices (list): Daftar indeks kamera yang akan dicoba
        embeddings_path (str): Path ke file embedding yang akan digunakan
        
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
        embeddings_dict = load_embeddings(embeddings_path)
        if not embeddings_dict:
            print(f"[!] File embeddings kosong atau tidak tersedia di: {embeddings_path}")
            display_lcd("Data Wajah", "Tidak tersedia")
            return False, None
        else:
            print(f"[+] Berhasil memuat database dengan {len(embeddings_dict)} orang")
    except Exception as e:
        print(f"[!] Gagal memuat embeddings: {e}")
        display_lcd("Error Data", "Wajah")
        return False, None
    
    # Inisialisasi kamera dengan pengaturan yang dioptimalkan untuk USB camera
    # Coba resolusi 480p terlebih dahulu, karena biasanya lebih stabil
    cap = initialize_camera(resolution=resolution, fps=fps)
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
    print(f"[INFO] Menggunakan threshold: {threshold}")
    
    while time.time() - start_time < timeout and not verified:
        try:
            ret, frame = cap.read()
            if not ret:
                print("[!] Gagal membaca frame dari kamera. Mencoba lagi...")
                time.sleep(0.1)
                continue
                
            # Deteksi wajah
            try:
                # Periksa apakah frame valid sebelum deteksi wajah
                if frame is None or frame.size == 0 or frame.shape[0] == 0 or frame.shape[1] == 0:
                    print("[!] Frame tidak valid, melewati...")
                    continue
                    
                face_img, bbox = detect_face_mtcnn(frame)
                
                if face_img is not None and bbox is not None:
                    # Tampilkan kotak di sekitar wajah
                    frame = draw_face_box(frame, bbox)
                    
                    # Proses wajah dan ekstrak embedding
                    face_tensor = preprocess_face(face_img)
                    if face_tensor is not None:
                        # Hitung orientasi wajah
                        pitch, yaw, roll = calculate_face_orientation(bbox, frame.shape)
                        frontal = is_face_frontal(pitch, yaw, roll)
                        
                        # Tampilkan informasi orientasi wajah pada frame
                        cv2.putText(frame, f"Pitch: {pitch:.1f}", (10, 60), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        cv2.putText(frame, f"Yaw: {yaw:.1f}", (10, 80), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        cv2.putText(frame, f"Roll: {roll:.1f}", (10, 100), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                        cv2.putText(frame, f"Frontal: {'Ya' if frontal else 'Tidak'}", (10, 120), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0) if frontal else (0, 0, 255), 1)
                                  
                        # Verifikasi hanya dilakukan jika wajah frontal
                        if frontal:
                            # Ekstrak embedding
                            embedding = extract_embedding(face_tensor)
                            
                            # Cari kecocokan terbaik
                            best_match_name = None
                            best_match_score = 0
                            
                            for name, embeddings_list in embeddings_dict.items():
                                if isinstance(embeddings_list, list):
                                    # Jika ada multiple embeddings untuk satu orang
                                    for ref_embedding in embeddings_list:
                                        similarity = compute_similarity(embedding, ref_embedding)
                                        if similarity > best_match_score:
                                            best_match_score = similarity
                                            best_match_name = name
                                else:
                                    # Jika hanya ada satu embedding
                                    similarity = compute_similarity(embedding, embeddings_list)
                                    if similarity > best_match_score:
                                        best_match_score = similarity
                                        best_match_name = name
                            
                            # Tampilkan hasil kecocokan
                            cv2.putText(frame, f"Kecocokan: {best_match_score:.2f}", (10, 140), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                                      
                            if best_match_score >= threshold:
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
            except Exception as e:
                print(f"[!] Error dalam deteksi wajah: {e}")
                continue
            
            # Tampilkan waktu tersisa
            remaining = int(timeout - (time.time() - start_time))
            cv2.putText(frame, f"Waktu: {remaining}s", (10, frame.shape[0] - 10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
            # Tampilkan threshold
            cv2.putText(frame, f"Threshold: {threshold}", (frame.shape[1] - 150, frame.shape[0] - 10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Tampilkan frame
            cv2.imshow("Verifikasi Wajah", frame)
            if cv2.waitKey(1) == 27:  # ESC untuk keluar
                break
                
        except Exception as e:
            print(f"[!] Error umum: {e}")
            continue
    
    # Bersihkan sumber daya
    cap.release()
    cv2.destroyAllWindows()
    
    if verified:
        print(f"[+] Wajah terverifikasi untuk pengguna: {user_name} (skor: {best_match_score:.2f})")
        display_lcd(f"Akses Diterima", f"Selamat {user_name}")
        return True, user_name
    else:
        print(f"[!] Gagal memverifikasi wajah")
        display_lcd("Akses Ditolak", "Wajah tidak cocok")
        return False, None

def main():
    """Fungsi utama program percobaan"""
    # Parse argumen
    args = parse_arguments()
    
    # Gunakan threshold dari argumen
    threshold = args.threshold
    
    # Gunakan file embedding dari argumen
    embeddings_path = args.embeddings
    
    # Tentukan kamera yang akan digunakan
    camera_devices = CAMERA_DEVICES
    if args.camera is not None:
        camera_devices = [args.camera] + camera_devices
    
    # Tampilkan informasi tentang program
    print("\n==============================================")
    print("PROGRAM PENGENALAN WAJAH DENGAN ARCFACE")
    print("Skenario Percobaan 2: Verifikasi Wajah")
    print("==============================================")
    print(f"File embedding: {embeddings_path}")
    print(f"Pengaturan kamera: MJPEG, {args.resolution}, {args.fps} FPS")
    print(f"Threshold kecocokan wajah: {threshold}")
    print("==============================================\n")
    
    # Tampilkan pesan selamat datang
    display_lcd("Test Percobaan 2", "Scan Wajah")
    time.sleep(2)
    
    # Loop utama
    try:
        while True:
            print("\n[PERCOBAAN 2] Tes Verifikasi Wajah")
            display_lcd("Deteksi Wajah", "Siap...")
            time.sleep(1)
            
            # Verifikasi wajah dengan parameter yang disesuaikan
            success, user_name = verify_face(threshold=threshold, 
                                           resolution=args.resolution, 
                                           fps=args.fps, 
                                           camera_devices=camera_devices,
                                           embeddings_path=embeddings_path)
            
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
            print("\nTekan Ctrl+C untuk menghentikan program, atau tunggu untuk scanning baru...")
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