import cv2
import numpy as np
import time
import threading
import os
import signal
import sys
from datetime import datetime

# Import modul utilitas
from fingerprint_utils import FingerprintSensor
from lcd_utils import LCD
from selenoid_utils import Selenoid
from database_utils import AccessDatabase
from mtcnn_utils import detect_face_mtcnn
from arcface_utils import preprocess_face, extract_embedding, compute_similarity
from head_pose import calculate_face_orientation, is_face_frontal

# Konstanta
# Gunakan daftar kamera yang akan dicoba secara berurutan
CAMERA_DEVICES = ['/dev/video1', '/dev/video2', 0]  # Coba /dev/video1 dulu, lalu /dev/video2, lalu indeks 0
FACE_RECOGNITION_THRESHOLD = 0.6
UNKNOWN_CAPTURE_DELAY = 2  # Delay capture 2 detik untuk wajah tidak dikenal
ACCESS_TIMEOUT = 10  # Timeout 10 detik untuk verifikasi wajah setelah sidik jari

class AccessControlSystem:
    def __init__(self, camera_devices=CAMERA_DEVICES):
        self.camera_devices = camera_devices
        self.camera_index = None  # Akan diisi dengan device yang berhasil dibuka
        self.running = False
        self.cap = None
        
        # Inisialisasi komponen
        self.db = AccessDatabase()
        self.fingerprint = FingerprintSensor()
        self.lcd = LCD()
        self.selenoid = Selenoid()
        
        # Status sistem
        self.current_user = None
        self.face_verification_mode = False
        self.face_verification_start_time = 0
        self.unknown_capture_timer = 0
        
        # Thread
        self.fingerprint_thread = None
        self.camera_thread = None
    
    def initialize(self):
        """Inisialisasi semua komponen sistem"""
        print("Inisialisasi sistem kontrol akses...")
        
        # Buat direktori jika belum ada
        os.makedirs('data', exist_ok=True)
        
        # Inisialisasi database
        if not self.db.connect():
            print("GAGAL: Tidak dapat menghubungkan ke database")
            return False
        
        # Inisialisasi LCD
        if not self.lcd.init():
            print("PERINGATAN: Tidak dapat menginisialisasi LCD")
            # Lanjutkan meskipun LCD tidak tersedia
        
        # Inisialisasi selenoid
        if not self.selenoid.init():
            print("PERINGATAN: Tidak dapat menginisialisasi selenoid")
            # Lanjutkan meskipun selenoid tidak tersedia
        
        # Inisialisasi sensor sidik jari
        if not self.fingerprint.connect():
            print("PERINGATAN: Tidak dapat menghubungkan ke sensor sidik jari")
            # Lanjutkan meskipun sensor tidak tersedia
        
        # Tampilkan pesan selamat datang
        self.lcd.clear()
        self.lcd.display("Sistem Kontrol", 1)
        self.lcd.display("Akses Siap", 2)
        
        print("Sistem kontrol akses berhasil diinisialisasi")
        return True
    
    def start(self):
        """Memulai sistem kontrol akses"""
        if self.running:
            print("Sistem sudah berjalan")
            return
        
        # Inisialisasi kamera - coba semua device yang tersedia
        self.cap = None
        for device in self.camera_devices:
            try:
                print(f"Mencoba membuka kamera {device}...")
                self.cap = cv2.VideoCapture(device)
                if self.cap is not None and self.cap.isOpened():
                    self.camera_index = device
                    print(f"Berhasil membuka kamera {device}")
                    break
                else:
                    print(f"Tidak dapat membuka kamera {device}")
            except Exception as e:
                print(f"Error saat membuka kamera {device}: {e}")
                if self.cap:
                    self.cap.release()
                    self.cap = None
        
        if self.cap is None or not self.cap.isOpened():
            print("GAGAL: Tidak dapat membuka kamera manapun")
            return False
        
        self.running = True
        
        # Mulai thread untuk memindai sidik jari
        self.fingerprint_thread = threading.Thread(target=self.fingerprint_scan_loop)
        self.fingerprint_thread.daemon = True
        self.fingerprint_thread.start()
        
        # Mulai thread untuk pemrosesan kamera
        self.camera_thread = threading.Thread(target=self.camera_process_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        print("Sistem kontrol akses berjalan")
        
        # Tampilkan pesan pada LCD
        self.lcd.clear()
        self.lcd.display("Tempelkan Jari", 1)
        self.lcd.display("Pada Sensor", 2)
        
        # Setup penanganan sinyal untuk pembersihan yang baik
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        return True
    
    def stop(self):
        """Menghentikan sistem kontrol akses"""
        self.running = False
        
        # Tunggu thread selesai
        if self.fingerprint_thread and self.fingerprint_thread.is_alive():
            self.fingerprint_thread.join(timeout=1.0)
        
        if self.camera_thread and self.camera_thread.is_alive():
            self.camera_thread.join(timeout=1.0)
        
        # Tutup kamera jika terbuka
        if self.cap and self.cap.isOpened():
            self.cap.release()
        
        # Bersihkan komponen
        self.selenoid.cleanup()
        self.fingerprint.disconnect()
        self.lcd.backlight(False)
        self.db.close()
        
        cv2.destroyAllWindows()
        print("Sistem kontrol akses dihentikan")
    
    def signal_handler(self, sig, frame):
        """Handler untuk sinyal terminasi"""
        print("\nMenghentikan sistem...")
        self.stop()
        sys.exit(0)
    
    def fingerprint_scan_loop(self):
        """Loop untuk memindai sidik jari"""
        while self.running:
            if not self.face_verification_mode:
                # Coba pindai sidik jari
                result = self.fingerprint.scan_finger()
                
                if result["success"]:
                    finger_id = result["finger_id"]
                    print(f"Sidik jari terdeteksi: ID {finger_id}")
                    
                    # Cari pengguna dalam database
                    user_result = self.db.get_user_by_finger_id(finger_id)
                    
                    if user_result["success"]:
                        # Pengguna ditemukan
                        self.current_user = user_result
                        print(f"Pengguna ditemukan: {user_result['name']}")
                        
                        # Tampilkan pesan di LCD
                        self.lcd.clear()
                        self.lcd.backlight(True)
                        self.lcd.display(f"Halo, {user_result['name']}", 1)
                        self.lcd.display("Verifikasi Wajah", 2)
                        
                        # Aktifkan mode verifikasi wajah
                        self.face_verification_mode = True
                        self.face_verification_start_time = time.time()
                        
                        # Log akses sidik jari
                        self.db.log_access(
                            user_result["user_id"],
                            "fingerprint",
                            True,
                            "Verifikasi sidik jari berhasil"
                        )
                    else:
                        # Sidik jari tidak dikenal
                        print("Sidik jari tidak terdaftar dalam database")
                        
                        # Tampilkan pesan di LCD
                        self.lcd.clear()
                        self.lcd.display("Sidik Jari", 1)
                        self.lcd.display("Tidak Dikenal!", 2)
                        
                        # Aktifkan timer untuk mengambil gambar orang tidak dikenal
                        self.unknown_capture_timer = time.time()
                        
                        # Reset setelah beberapa detik
                        time.sleep(3)
                        self.lcd.clear()
                        self.lcd.display("Tempelkan Jari", 1)
                        self.lcd.display("Pada Sensor", 2)
            
            # Delay untuk mengurangi beban CPU
            time.sleep(0.5)
    
    def camera_process_loop(self):
        """Loop untuk memproses gambar dari kamera"""
        while self.running:
            # Baca frame dari kamera
            ret, frame = self.cap.read()
            if not ret:
                print("Error: Gagal membaca frame dari kamera")
                time.sleep(1)
                continue
            
            # Tampilkan frame (opsional, hapus jika tidak diperlukan)
            if self.face_verification_mode:
                cv2.imshow("Verifikasi Wajah", frame)
            
            # Jika dalam mode verifikasi wajah
            if self.face_verification_mode:
                # Cek timeout
                current_time = time.time()
                if current_time - self.face_verification_start_time > ACCESS_TIMEOUT:
                    print("Timeout verifikasi wajah")
                    self.lcd.clear()
                    self.lcd.display("Timeout", 1)
                    self.lcd.display("Coba Lagi", 2)
                    time.sleep(2)
                    
                    # Reset mode verifikasi
                    self.face_verification_mode = False
                    self.current_user = None
                    
                    # Tampilkan pesan awal
                    self.lcd.clear()
                    self.lcd.display("Tempelkan Jari", 1)
                    self.lcd.display("Pada Sensor", 2)
                    
                    # Tutup jendela kamera
                    cv2.destroyWindow("Verifikasi Wajah")
                    continue
                
                # Deteksi wajah
                face_img, bbox = detect_face_mtcnn(frame)
                
                if face_img is not None and bbox is not None:
                    # Pra-pemrosesan wajah
                    face_tensor = preprocess_face(face_img)
                    
                    if face_tensor is not None:
                        # Ekstrak embedding
                        embedding = extract_embedding(face_tensor)
                        
                        # Dapatkan nama pengguna saat ini
                        current_name = self.current_user["name"]
                        
                        # Cek apakah pengguna memiliki data wajah
                        if current_name in self.db.embeddings:
                            # Hitung similarity
                            stored_embedding = self.db.embeddings[current_name]
                            similarity = compute_similarity(embedding, stored_embedding)
                            
                            # Tampilkan similarity
                            cv2.putText(frame, f"Similarity: {similarity:.4f}", 
                                     (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            # Jika similarity di atas threshold
                            if similarity >= FACE_RECOGNITION_THRESHOLD:
                                print(f"Verifikasi wajah berhasil: {current_name}, similarity: {similarity:.4f}")
                                
                                # Tampilkan pesan di LCD
                                self.lcd.clear()
                                self.lcd.display("Akses Diterima", 1)
                                self.lcd.display(f"Selamat Datang!", 2)
                                
                                # Buka selenoid
                                self.selenoid.unlock(5)
                                
                                # Log akses
                                self.db.log_access(
                                    self.current_user["user_id"],
                                    "face",
                                    True,
                                    f"Verifikasi wajah berhasil (similarity: {similarity:.4f})"
                                )
                                
                                # Reset mode verifikasi
                                self.face_verification_mode = False
                                self.current_user = None
                                
                                # Tunggu sebentar, kemudian kembali ke pesan awal
                                time.sleep(5)
                                self.lcd.clear()
                                self.lcd.display("Tempelkan Jari", 1)
                                self.lcd.display("Pada Sensor", 2)
                                
                                # Tutup jendela kamera
                                cv2.destroyWindow("Verifikasi Wajah")
                            else:
                                # Tampilkan di frame
                                cv2.putText(frame, "Verifikasi wajah gagal", 
                                         (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                        else:
                            # Pengguna belum memiliki data wajah
                            cv2.putText(frame, "Data wajah belum terdaftar", 
                                     (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            
                            # Tanyakan apakah ingin mendaftarkan wajah
                            cv2.putText(frame, "Tekan 'Y' untuk mendaftarkan wajah", 
                                     (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                            
                            # Tampilkan pesan di LCD
                            self.lcd.clear()
                            self.lcd.display("Tidak Ada Data", 1)
                            self.lcd.display("Wajah Y=Daftar", 2)
                    
                    # Update tampilan
                    cv2.imshow("Verifikasi Wajah", frame)
            
            # Jika timer untuk mengambil gambar orang tidak dikenal aktif
            elif self.unknown_capture_timer > 0:
                current_time = time.time()
                if current_time - self.unknown_capture_timer > UNKNOWN_CAPTURE_DELAY:
                    # Simpan gambar orang tidak dikenal
                    image_path = self.db.save_unknown_face(frame)
                    
                    if image_path:
                        print(f"Gambar orang tidak dikenal disimpan: {image_path}")
                        
                        # Log akses tidak dikenal
                        self.db.log_unknown_access(image_path, None, "Sidik jari tidak dikenal")
                    
                    # Reset timer
                    self.unknown_capture_timer = 0
            
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF
            
            # Tekan 'q' untuk keluar
            if key == ord('q'):
                self.running = False
                break
            
            # Tekan 'y' untuk mendaftarkan wajah jika dalam mode verifikasi
            elif key == ord('y') and self.face_verification_mode and self.current_user:
                if face_img is not None and bbox is not None:
                    # Pra-pemrosesan wajah
                    face_tensor = preprocess_face(face_img)
                    
                    if face_tensor is not None:
                        # Ekstrak embedding
                        embedding = extract_embedding(face_tensor)
                        
                        # Simpan embedding dengan nama pengguna
                        self.db.embeddings[self.current_user["name"]] = embedding
                        self.db.save_embeddings()
                        
                        print(f"Data wajah untuk {self.current_user['name']} berhasil didaftarkan")
                        
                        # Tampilkan pesan di LCD
                        self.lcd.clear()
                        self.lcd.display("Pendaftaran", 1)
                        self.lcd.display("Berhasil!", 2)
                        
                        # Buka selenoid (akses diterima)
                        self.selenoid.unlock(5)
                        
                        # Log akses
                        self.db.log_access(
                            self.current_user["user_id"],
                            "face_registration",
                            True,
                            "Pendaftaran wajah berhasil"
                        )
                        
                        # Reset mode verifikasi
                        self.face_verification_mode = False
                        self.current_user = None
                        
                        # Tunggu sebentar, kemudian kembali ke pesan awal
                        time.sleep(5)
                        self.lcd.clear()
                        self.lcd.display("Tempelkan Jari", 1)
                        self.lcd.display("Pada Sensor", 2)
                        
                        # Tutup jendela kamera
                        cv2.destroyWindow("Verifikasi Wajah")
            
            # Delay untuk mengurangi beban CPU
            time.sleep(0.03)

def setup_new_user():
    """Mendaftarkan pengguna baru dengan sidik jari"""
    print("\n=== Pendaftaran Pengguna Baru ===")
    name = input("Masukkan nama pengguna: ")
    
    # Inisialisasi sensor sidik jari
    sensor = FingerprintSensor()
    if not sensor.connect():
        print("Gagal terhubung ke sensor sidik jari")
        return
    
    print("\nProses pendaftaran sidik jari:")
    
    # Temukan ID tersedia
    finger_id = 1
    db = AccessDatabase()
    if db.connect():
        users = db.get_all_users()
        if users["success"] and len(users["users"]) > 0:
            existing_ids = [user["finger_id"] for user in users["users"] if user["finger_id"] is not None]
            if existing_ids:
                finger_id = max(existing_ids) + 1
    
    print(f"Menggunakan ID sidik jari: {finger_id}")
    
    # Daftarkan sidik jari
    result = sensor.enroll_finger(finger_id)
    
    if result["success"]:
        print(f"Pendaftaran sidik jari berhasil dengan ID: {result['finger_id']}")
        
        # Simpan ke database
        if db.connect():
            db_result = db.add_user(name, finger_id)
            if db_result["success"]:
                print(f"Pengguna {name} berhasil didaftarkan ke database")
            else:
                print(f"Error: {db_result['message']}")
            
            db.close()
    else:
        print(f"Pendaftaran sidik jari gagal: {result['message']}")
    
    sensor.disconnect()
    print("=== Pendaftaran Selesai ===")

def list_users():
    """Menampilkan daftar pengguna"""
    print("\n=== Daftar Pengguna ===")
    
    db = AccessDatabase()
    if db.connect():
        result = db.get_all_users()
        
        if result["success"] and len(result["users"]) > 0:
            print("ID  | Nama             | ID Sidik Jari | Data Wajah | Level Akses")
            print("-"*65)
            
            for user in result["users"]:
                face_status = "Ada" if user["has_face"] else "Tidak Ada"
                finger_id = user["finger_id"] if user["finger_id"] is not None else "-"
                print(f"{user['id']:<4}| {user['name']:<17}| {finger_id:<13}| {face_status:<10}| {user['access_level']}")
        else:
            print("Tidak ada pengguna terdaftar")
        
        db.close()
    else:
        print("Gagal terhubung ke database")
    
    print("="*65)

def show_menu():
    """Menampilkan menu utama"""
    print("\n=== Sistem Kontrol Akses ===")
    print("1. Mulai sistem")
    print("2. Daftarkan pengguna baru")
    print("3. Tampilkan daftar pengguna")
    print("0. Keluar")
    
    choice = input("Pilihan: ")
    return choice

def main():
    """Program utama"""
    while True:
        choice = show_menu()
        
        if choice == "1":
            # Mulai sistem
            system = AccessControlSystem()
            if system.initialize():
                system.start()
                
                # Tunggu thread utama
                try:
                    while system.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nMenekan Ctrl+C untuk keluar...")
                finally:
                    system.stop()
            else:
                print("Gagal menginisialisasi sistem")
        
        elif choice == "2":
            # Daftarkan pengguna baru
            setup_new_user()
        
        elif choice == "3":
            # Tampilkan daftar pengguna
            list_users()
        
        elif choice == "0":
            print("Terima kasih telah menggunakan sistem kontrol akses")
            break
        
        else:
            print("Pilihan tidak valid")

if __name__ == "__main__":
    main() 