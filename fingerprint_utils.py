# fingerprint_and_face_handler.py

from pyfingerprint.pyfingerprint import PyFingerprint
import sqlite3
import cv2
import os
import numpy as np
import time
import json
import pickle
import glob
import datetime

# Import modul ArcFace dan lainnya
try:
    from mtcnn_utils import detect_face_mtcnn, draw_face_box
    from arcface_utils import preprocess_face, extract_embedding, save_embeddings, load_embeddings
    from head_pose import calculate_face_orientation, draw_face_orientation, is_face_frontal
    ARCFACE_AVAILABLE = True
except ImportError:
    print("[!] Modul ArcFace tidak tersedia. Fitur pengenalan wajah lanjutan tidak akan bekerja.")
    ARCFACE_AVAILABLE = False

# Coba import modul LCD jika tersedia
try:
    import lcd_utils
    LCD_AVAILABLE = True
except ImportError:
    print("[!] Modul LCD tidak tersedia. Tampilan LCD tidak akan bekerja.")
    LCD_AVAILABLE = False

# Coba import modul selenoid jika tersedia
try:
    from selenoid_utils import Selenoid
    SELENOID_AVAILABLE = True
except ImportError:
    print("[!] Modul selenoid tidak tersedia. Selenoid tidak akan bekerja.")
    SELENOID_AVAILABLE = False

# Konfigurasi sensor sidik jari
PORT = '/dev/ttyUSB0'   # Ubah kalau port-nya beda
BAUDRATE = 57600

# Konfigurasi kamera
CAMERA_DEVICES = ['/dev/video1', '/dev/video2', 0]  # Coba /dev/video1, /dev/video2, kemudian indeks 0
CAMERA_ID = 0  # Default kamera untuk kompatibilitas

# Konfigurasi database
DB_PATH = 'biometrics.db'
EMBEDDINGS_PATH = 'embeddings.pkl'  # Path ke file embeddings ArcFace di folder utama

# Konfigurasi selenoid
SELENOID_PIN = 18  # GPIO pin untuk selenoid
UNLOCK_DURATION = 5  # Durasi membuka selenoid (detik)

# Inisialisasi LCD jika tersedia
lcd = None
if LCD_AVAILABLE:
    try:
        lcd = lcd_utils.LCD()
        lcd.clear()
        lcd.display_message("Sistem siap", "Tempelkan jari")
    except Exception as e:
        print(f"[!] Gagal inisialisasi LCD: {e}")
        LCD_AVAILABLE = False

# Inisialisasi selenoid jika tersedia
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
        except:
            pass

def unlock_door():
    """Membuka selenoid jika tersedia"""
    if SELENOID_AVAILABLE and selenoid:
        try:
            selenoid.unlock(UNLOCK_DURATION)
            return True
        except Exception as e:
            print(f"[!] Gagal membuka selenoid: {e}")
    else:
        print("[+] Simulasi: Selenoid terbuka")
        time.sleep(UNLOCK_DURATION)
        print("[+] Simulasi: Selenoid tertutup kembali")
    return False

def migrate_database():
    """Memperbarui struktur database lama ke struktur terbaru"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Periksa apakah kolom face_embedding_path sudah ada
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    column_names = [column[1] for column in columns]
    
    # Jika kolom belum ada, tambahkan kolom baru
    if 'face_embedding_path' not in column_names:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN face_embedding_path TEXT")
            conn.commit()
            print("[+] Database berhasil diperbarui dengan kolom 'face_embedding_path'")
        except sqlite3.Error as e:
            print(f"[!] Error saat memperbarui database: {e}")
    
    # Buat tabel unknown_faces jika belum ada
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS unknown_faces (
        id INTEGER PRIMARY KEY,
        image_path TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    )
    ''')
    conn.commit()
    conn.close()

def create_database():
    """Membuat database jika belum ada"""
    # Cek apakah database sudah ada
    db_exists = os.path.exists(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Buat tabel users untuk menyimpan data pengguna
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        fingerprint_id INTEGER UNIQUE,
        face_encoding TEXT,
        face_embedding_path TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Buat tabel unknown_faces untuk menyimpan wajah tidak dikenal
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS unknown_faces (
        id INTEGER PRIMARY KEY,
        image_path TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT
    )
    ''')
    
    conn.commit()
    conn.close()
    
    # Jika database sudah ada, jalankan migrasi
    if db_exists:
        migrate_database()
    
    print("[+] Database siap digunakan")

def initialize_sensor():
    try:
        f = PyFingerprint(PORT, BAUDRATE, 0xFFFFFFFF, 0x00000000)
        if not f.verifyPassword():
            raise ValueError('Password sensor salah.')
        return f
    except Exception as e:
        print('[!] Gagal inisialisasi sensor:', e)
        return None

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

def capture_face(resolution="480p", fps=15):
    """
    Mengambil gambar wajah dari kamera
    
    Args:
        resolution (str): Resolusi kamera yang digunakan
        fps (int): Frame rate yang digunakan
        
    Returns:
        tuple: (gambar_wajah, bounding_box) jika berhasil, (None, None) jika gagal
    """
    # Inisialisasi kamera dengan pengaturan yang dioptimalkan
    cap = initialize_camera(resolution=resolution, fps=fps)
    if not cap:
        print("[!] Gagal inisialisasi kamera.")
        display_lcd("Kamera Error", "Coba lagi")
        return None, None
    
    print("[+] Kamera siap. Posisikan wajah di depan kamera...")
    display_lcd("Posisikan", "wajah Anda")
    
    face_img = None
    bbox = None
    start_time = time.time()
    timeout = 15  # Batas waktu 15 detik
    
    while time.time() - start_time < timeout:
        # Baca frame dari kamera
        ret, frame = cap.read()
        if not ret:
            print("[!] Gagal membaca frame dari kamera.")
            continue
        
        try:
            # Verifikasi frame valid
            if frame is None or frame.size == 0:
                print("[!] Frame tidak valid, melewati...")
                continue
                
            # Deteksi wajah dengan MTCNN
            face_img, bbox = detect_face_mtcnn(frame)
            
            # Jika wajah terdeteksi
            if bbox is not None:
                # Gambar kotak di sekitar wajah
                frame_with_box = draw_face_box(frame, bbox)
                
                # Tampilkan frame
                cv2.putText(frame_with_box, "Wajah terdeteksi!", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(frame_with_box, "Tekan 'SPASI' untuk mengambil gambar", 
                          (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imshow("Pengambilan Wajah", frame_with_box)
                
                key = cv2.waitKey(1)
                if key == 32:  # Spasi
                    print("[+] Gambar wajah diambil.")
                    break
            else:
                # Jika tidak ada wajah, tampilkan frame biasa
                cv2.putText(frame, "Tidak ada wajah terdeteksi", (10, 30), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, "Posisikan wajah Anda di depan kamera", 
                          (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                cv2.imshow("Pengambilan Wajah", frame)
                
                key = cv2.waitKey(1)
                if key == 27:  # ESC
                    print("[!] Pengguna membatalkan pengambilan wajah.")
                    break
        except Exception as e:
            print(f"[!] Error saat mendeteksi wajah: {e}")
            continue
    
    # Bersihkan resources
    cap.release()
    cv2.destroyAllWindows()
    
    # Cek apakah wajah berhasil diambil
    if face_img is None or bbox is None:
        print("[!] Gagal mengambil gambar wajah.")
        display_lcd("Gagal", "mengambil wajah")
        return None, None
    
    print("[+] Gambar wajah berhasil diambil.")
    return face_img, bbox

def capture_face_arcface(username):
    """
    Mengambil 5 foto wajah untuk ArcFace dan mengekstrak embedding
    
    Args:
        username: Nama pengguna untuk menyimpan foto dan embedding
    
    Returns:
        str: Path ke file embedding yang disimpan
    """
    if not ARCFACE_AVAILABLE:
        print("[!] Fitur ArcFace tidak tersedia. Menggunakan metode capture_face standar...")
        return capture_face()
    
    # Buka kamera
    cap = cv2.VideoCapture(CAMERA_ID)
    
    if not cap.isOpened():
        print(f"[!] Gagal membuka kamera {CAMERA_ID}")
        return None
    
    # Buat direktori untuk menyimpan foto
    photo_dir = 'photos'
    os.makedirs(photo_dir, exist_ok=True)
    
    # Periksa apakah nama sudah ada dalam database
    embeddings_dict = load_embeddings(EMBEDDINGS_PATH)
    if username in embeddings_dict:
        print(f"[INFO] Nama '{username}' sudah ada dalam database embedding.")
        response = input(f"Apakah Anda ingin menimpa data '{username}'? (y/n): ")
        if response.lower() != 'y':
            print("[!] Pembatalan pengambilan foto.")
            cap.release()
            return None
        print(f"[INFO] Data untuk '{username}' akan ditimpa.")
    
    print(f"\n=== PENGAMBILAN FOTO WAJAH UNTUK: {username} ===")
    print("Ambil 5 foto dengan pose berbeda:")
    print("1. Wajah frontal")
    print("2. Wajah miring ke kiri")
    print("3. Wajah miring ke kanan")
    print("4. Ekspresi tersenyum")
    print("5. Ekspresi lain (bebas)")
    print("\nTekan SPASI untuk mengambil foto (5 foto diperlukan)")
    print("Tekan 'a' untuk mengaktifkan/menonaktifkan penampilan sudut wajah")
    print("Tekan ESC untuk keluar")
    
    embeddings = []
    photos_captured = 0
    required_photos = 5
    instruction_text = "Wajah frontal"
    show_angles = True  # Tampilkan sudut orientasi wajah secara default
    
    while photos_captured < required_photos:
        ret, frame = cap.read()
        if not ret:
            print("[!] Gagal membaca frame dari kamera!")
            break
        
        # Deteksi wajah dengan MTCNN
        face_img, bbox = detect_face_mtcnn(frame)
        
        # Tampilkan frame dengan kotak wajah dan orientasi wajah jika diaktifkan
        if bbox is not None:
            # Hitung orientasi wajah
            pitch, yaw, roll = calculate_face_orientation(bbox, frame.shape)
            
            # Tampilkan kotak wajah dan sudut jika diaktifkan
            if show_angles:
                frame = draw_face_orientation(frame, bbox, pitch, yaw, roll)
            else:
                frame = draw_face_box(frame, bbox)
            
            # Tambahkan indikator posisi wajah frontal
            is_frontal = is_face_frontal(pitch, yaw, roll)
            frontal_status = "FRONTAL" if is_frontal else "TIDAK FRONTAL"
            frontal_color = (0, 255, 0) if is_frontal else (0, 0, 255)
            cv2.putText(frame, frontal_status, (frame.shape[1] - 150, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, frontal_color, 2)
        
        # Tampilkan instruksi dan jumlah foto
        cv2.putText(frame, f"Foto {photos_captured+1}/5: {instruction_text}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Pengguna: {username}", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Tekan SPASI untuk mengambil foto", 
                    (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Tampilkan frame
        cv2.imshow("Pengambilan Foto", frame)
        
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break
        elif key == 97:  # 'a' untuk toggle sudut
            show_angles = not show_angles
            status = "aktif" if show_angles else "nonaktif"
            print(f"[INFO] Penampilan sudut wajah: {status}")
        elif key == 32 and bbox is not None:  # SPASI
            # Pra-pemrosesan wajah
            face_tensor = preprocess_face(face_img)
            
            if face_tensor is not None:
                # Simpan foto
                photo_path = os.path.join(photo_dir, f"{username}_{photos_captured+1}.jpg")
                cv2.imwrite(photo_path, face_img)
                
                # Ekstrak embedding
                embedding = extract_embedding(face_tensor)
                embeddings.append(embedding)
                
                photos_captured += 1
                print(f"[+] Foto {photos_captured}/5 diambil dan disimpan ke {photo_path}")
                
                # Update instruksi untuk foto berikutnya
                if photos_captured == 1:
                    instruction_text = "Wajah miring ke kiri"
                elif photos_captured == 2:
                    instruction_text = "Wajah miring ke kanan"
                elif photos_captured == 3:
                    instruction_text = "Ekspresi tersenyum"
                elif photos_captured == 4:
                    instruction_text = "Ekspresi lain (bebas)"
                
                # Berikan jeda untuk perubahan pose
                time.sleep(1)
    
    cap.release()
    cv2.destroyAllWindows()
    
    if photos_captured > 0:
        # Hitung rata-rata embedding
        avg_embedding = np.mean(np.array(embeddings), axis=0)
        
        # Muat embedding yang sudah ada (jika ada)
        embeddings_dict = load_embeddings(EMBEDDINGS_PATH)
        
        # Simpan embedding baru
        embeddings_dict[username] = avg_embedding
        save_embeddings(embeddings_dict, EMBEDDINGS_PATH)
        
        print(f"[+] Berhasil menyimpan rata-rata embedding untuk {username} dari {photos_captured} foto")
        print(f"[+] Embedding disimpan di {EMBEDDINGS_PATH}")
        
        return EMBEDDINGS_PATH
    else:
        print("[!] Tidak ada foto yang diambil.")
        return None

def import_face_embedding(embedding_path, username=None):
    """
    Mengimpor embedding wajah yang sudah ada dari file
    
    Args:
        embedding_path: Path ke file embedding (JSON, NPY, atau PKL)
        username: Nama pengguna untuk memilih data dari file jika berisi banyak data (opsional)
    
    Returns:
        Path ke file embedding yang diimpor
    """
    if not os.path.exists(embedding_path):
        print(f"[!] File embedding tidak ditemukan: {embedding_path}")
        return None
    
    try:
        # Buat direktori embeddings jika belum ada
        os.makedirs('embeddings', exist_ok=True)
        
        # Salin file embedding ke direktori embeddings
        filename = os.path.basename(embedding_path)
        
        # Jika file berformat PKL (pickle)
        if embedding_path.endswith('.pkl'):
            with open(embedding_path, 'rb') as f:
                embedding_data = pickle.load(f)
                print(f"[INFO] Data embedding pickle dimuat: {type(embedding_data)}")
                
                # Cek apakah data berupa dictionary (mungkin berisi beberapa orang)
                if isinstance(embedding_data, dict):
                    # Jika username disediakan, coba ambil data spesifik
                    if username and username in embedding_data:
                        print(f"[INFO] Mengambil data embedding untuk user: {username}")
                        user_data = embedding_data[username]
                        
                        # Buat file pickle baru khusus untuk pengguna ini
                        user_filename = f"{username}_embedding.pkl"
                        destination = f'embeddings/{user_filename}'
                        
                        with open(destination, 'wb') as dest_file:
                            pickle.dump(user_data, dest_file)
                        
                        print(f"[+] Embedding wajah untuk {username} berhasil diimpor: {destination}")
                        return destination
                    
                    # Jika tidak ada username yang cocok atau username tidak disediakan
                    elif username:
                        print(f"[!] Username '{username}' tidak ditemukan dalam file embedding")
                        available_users = list(embedding_data.keys())
                        print(f"[INFO] User yang tersedia: {available_users}")
                        
                        # Minta user memilih dari daftar yang tersedia
                        while True:
                            choice = input("Masukkan nama user dari daftar di atas (atau 'batal' untuk membatalkan): ")
                            if choice.lower() == 'batal':
                                return None
                            if choice in embedding_data:
                                user_data = embedding_data[choice]
                                user_filename = f"{choice}_embedding.pkl"
                                destination = f'embeddings/{user_filename}'
                                
                                with open(destination, 'wb') as dest_file:
                                    pickle.dump(user_data, dest_file)
                                
                                print(f"[+] Embedding wajah untuk {choice} berhasil diimpor: {destination}")
                                return destination
                            else:
                                print(f"[!] Username '{choice}' tidak ditemukan, coba lagi")
                    
                    # Jika tidak ada username, tampilkan daftar dan minta user memilih
                    else:
                        available_users = list(embedding_data.keys())
                        print(f"[INFO] File berisi embedding untuk beberapa user: {available_users}")
                        
                        while True:
                            choice = input("Masukkan nama user dari daftar di atas (atau 'batal' untuk membatalkan): ")
                            if choice.lower() == 'batal':
                                return None
                            if choice in embedding_data:
                                user_data = embedding_data[choice]
                                user_filename = f"{choice}_embedding.pkl"
                                destination = f'embeddings/{user_filename}'
                                
                                with open(destination, 'wb') as dest_file:
                                    pickle.dump(user_data, dest_file)
                                
                                print(f"[+] Embedding wajah untuk {choice} berhasil diimpor: {destination}")
                                return destination
                            else:
                                print(f"[!] Username '{choice}' tidak ditemukan, coba lagi")
                
                # Jika bukan dictionary, simpan langsung
                else:
                    destination = f'embeddings/{filename}'
                    with open(destination, 'wb') as dest_file:
                        pickle.dump(embedding_data, dest_file)
                    print(f"[+] Embedding wajah berhasil diimpor: {destination}")
                    return destination
        
        # Jika file berformat JSON
        elif embedding_path.endswith('.json'):
            with open(embedding_path, 'r') as f:
                embedding_data = json.load(f)
                # Validasi format embedding
                if not isinstance(embedding_data, dict):
                    print("[!] Format embedding tidak valid")
                    return None
                
                # Cek apakah berisi data untuk multiple user
                if username and username in embedding_data:
                    user_data = embedding_data[username]
                    user_filename = f"{username}_embedding.json"
                    destination = f'embeddings/{user_filename}'
                    
                    with open(destination, 'w') as dest_file:
                        json.dump(user_data, dest_file)
                    
                    print(f"[+] Embedding wajah untuk {username} berhasil diimpor: {destination}")
                    return destination
                else:
                    # Simpan ke file baru
                    destination = f'embeddings/{filename}'
                    with open(destination, 'w') as dest_file:
                        json.dump(embedding_data, dest_file)
                    print(f"[+] Embedding wajah berhasil diimpor: {destination}")
                    return destination
        
        # Jika file berformat NPY (numpy array)
        elif embedding_path.endswith('.npy'):
            embedding_array = np.load(embedding_path)
            destination = f'embeddings/{filename}'
            np.save(destination, embedding_array)
            print(f"[+] Embedding wajah berhasil diimpor: {destination}")
            return destination
        else:
            # Salin file langsung
            import shutil
            destination = f'embeddings/{filename}'
            shutil.copy2(embedding_path, destination)
            print(f"[+] Embedding wajah berhasil diimpor: {destination}")
            return destination
    
    except Exception as e:
        print(f"[!] Gagal mengimpor embedding wajah: {e}")
        return None

def capture_unknown_face(resolution="480p", fps=15):
    """
    Mengambil gambar wajah tidak dikenal dan menyimpannya
    
    Args:
        resolution (str): Resolusi kamera yang digunakan
        fps (int): Frame rate yang digunakan
        
    Returns:
        str: Path ke gambar yang disimpan jika berhasil, None jika gagal
    """
    # Inisialisasi kamera
    cap = initialize_camera(resolution=resolution, fps=fps)
    if not cap:
        print("[!] Gagal inisialisasi kamera.")
        return None
    
    print("[+] Mengambil gambar wajah yang tidak dikenal...")
    display_lcd("Memotret", "Wajah asing")
    
    # Buat folder untuk menyimpan gambar jika belum ada
    os.makedirs("unknown_faces", exist_ok=True)
    
    # Ambil satu frame
    ret, frame = cap.read()
    if not ret:
        print("[!] Gagal membaca frame dari kamera.")
        cap.release()
        return None
    
    # Cek apakah ada wajah menggunakan MTCNN jika tersedia
    if ARCFACE_AVAILABLE:
        try:
            face_img, bbox = detect_face_mtcnn(frame)
            if bbox is None:
                print("[!] Tidak ada wajah terdeteksi")
                return None
            
            # Tambahkan kotak di sekitar wajah
            frame = draw_face_box(frame, bbox)
        except Exception as e:
            print(f"[!] Error dalam deteksi wajah: {e}")
            # Jika gagal menggunakan MTCNN, gunakan Haar Cascade
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            
            if len(faces) == 0:
                print("[!] Tidak ada wajah terdeteksi")
                return None
            
            # Tambahkan kotak di sekitar wajah
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
    else:
        # Gunakan Haar Cascade jika MTCNN tidak tersedia
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            print("[!] Tidak ada wajah terdeteksi")
            return None
        
        # Tambahkan kotak di sekitar wajah
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
    
    # Tambahkan teks "UNKNOWN" pada gambar
    cv2.putText(frame, "UNKNOWN", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # Tambahkan timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    cv2.putText(frame, timestamp, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # Simpan gambar
    image_path = os.path.join("unknown_faces", f"unknown_{timestamp}.jpg")
    cv2.imwrite(image_path, frame)
    
    # Tambahkan gambar ke database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO unknown_faces (image_path, notes) VALUES (?, ?)", 
                (image_path, "Wajah tidak dikenal terdeteksi"))
    conn.commit()
    conn.close()
    
    print(f"[+] Gambar wajah tidak dikenal disimpan di: {image_path}")
    
    # Bersihkan resources
    cap.release()
    
    return image_path

def enroll_user(existing_embedding_path=None):
    """
    Mendaftarkan pengguna baru dengan sidik jari dan wajah
    
    Args:
        existing_embedding_path: Path ke file embedding wajah yang sudah ada (opsional)
    """
    # Ambil informasi pengguna
    name = input("Masukkan nama pengguna: ")
    
    # Daftarkan sidik jari
    print("\n[STEP 1] Pendaftaran Sidik Jari")
    fingerprint_id = enroll_fingerprint()
    if fingerprint_id is None:
        return False
    
    # Proses data wajah
    face_encoding = None
    face_embedding_path = None
    
    # Pilihan metode wajah
    print("\n[STEP 2] Pendaftaran Wajah")
    print("Pilih metode pendaftaran wajah:")
    print("1. Ambil 5 foto dengan ArcFace (rekomendasi)")
    print("2. Ambil 1 foto (metode sederhana)")
    print("3. Gunakan embedding yang sudah ada")
    
    face_method = input("Pilih metode (1/2/3): ")
    
    if face_method == "1" and ARCFACE_AVAILABLE:
        # Gunakan metode ArcFace dengan 5 foto
        face_embedding_path = capture_face_arcface(name)
        if face_embedding_path is None:
            # Jika gagal, hapus sidik jari yang sudah terdaftar
            delete_fingerprint(fingerprint_id)
            return False
    elif face_method == "3" or (face_method == "1" and not ARCFACE_AVAILABLE and existing_embedding_path):
        # Gunakan embedding yang sudah ada
        if not existing_embedding_path:
            existing_embedding_path = input("Masukkan path ke file embedding wajah (.json/.npy/.pkl): ")
        
        print(f"\n[STEP 2] Mengimpor Embedding Wajah dari {existing_embedding_path}")
        face_embedding_path = import_face_embedding(existing_embedding_path, name)
        if face_embedding_path is None:
            # Jika gagal impor, hapus sidik jari yang sudah terdaftar
            delete_fingerprint(fingerprint_id)
            return False
    else:
        # Metode default: ambil 1 foto
        print("\n[STEP 2] Pendaftaran Wajah dengan Satu Foto")
        face_encoding = capture_face()
        if face_encoding is None:
            # Jika gagal mengambil wajah, hapus sidik jari yang sudah terdaftar
            delete_fingerprint(fingerprint_id)
            return False
    
    # Simpan ke database
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, fingerprint_id, face_encoding, face_embedding_path) VALUES (?, ?, ?, ?)",
            (name, fingerprint_id, face_encoding, face_embedding_path)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        print(f"[+] Pengguna {name} berhasil didaftarkan dengan ID: {user_id}")
        return True
    except sqlite3.IntegrityError:
        print("[!] Error: Sidik jari sudah terdaftar untuk pengguna lain")
        return False
    except Exception as e:
        print(f"[!] Gagal menyimpan ke database: {e}")
        return False

def enroll_fingerprint():
    """Mendaftarkan sidik jari baru dan mengembalikan ID template"""
    f = initialize_sensor()
    if not f:
        return None

    try:
        print('[INFO] Mencari slot kosong untuk menyimpan sidik jari...')
        count = f.getTemplateCount()
        if count >= f.getStorageCapacity():
            print('[!] Penyimpanan penuh.')
            return None

        print('[INFO] Tempelkan jari Anda...')
        while not f.readImage():
            pass

        f.convertImage(0x01)

        print('[INFO] Angkat jari dan tempelkan kembali...')
        while f.readImage():
            pass
        while not f.readImage():
            pass

        f.convertImage(0x02)

        if f.compareCharacteristics() == 0:
            print('[!] Jari tidak cocok, coba lagi.')
            return None

        f.createTemplate()
        positionNumber = f.storeTemplate()
        print(f'[+] Sidik jari berhasil disimpan di ID: {positionNumber}')
        return positionNumber

    except Exception as e:
        print('[!] Gagal mendaftar sidik jari:', e)
        return None

def delete_fingerprint(template_id):
    """Menghapus sidik jari dari sensor dan database"""
    f = initialize_sensor()
    if not f:
        return False

    try:
        if f.deleteTemplate(template_id):
            print(f'[+] Sidik jari di ID {template_id} berhasil dihapus.')
            
            # Hapus juga dari database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET fingerprint_id = NULL WHERE fingerprint_id = ?", (template_id,))
            conn.commit()
            conn.close()
            
            return True
        else:
            print('[!] Gagal menghapus template.')
            return False
    except Exception as e:
        print('[!] Gagal menghapus template:', e)
        return False

def scan_fingerprint():
    """
    Memindai sidik jari dan mengembalikan ID pengguna jika dikenali
    
    Returns:
        int/None: ID pengguna jika sidik jari dikenali, None jika tidak
    """
    # Tampilkan pesan di LCD
    display_lcd("Scan Sidik Jari", "Tempelkan jari")
    
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

        positionNumber = result[0]
        accuracyScore = result[1]

        if positionNumber == -1:
            print('[!] Sidik jari tidak dikenali.')
            display_lcd("Akses Ditolak", "Sidik jari asing")
            
            # Tangkap wajah tidak dikenal jika sidik jari tidak dikenali
            capture_unknown_face()
            
            return None
        else:
            print(f'[+] Dikenali! ID Fingerprint: {positionNumber}, Akurasi: {accuracyScore}')
            
            # Ambil data pengguna dari database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM users WHERE fingerprint_id = ?", (positionNumber,))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                print(f'[+] Pengguna: {user[1]} (ID: {user[0]})')
                display_lcd(f"Dikenali: {user[1]}", "Scan wajah...")
                return user[0]  # Return user_id
            else:
                print('[!] Data pengguna tidak ditemukan di database.')
                display_lcd("Data Error", "Kontak admin")
                return None

    except Exception as e:
        print('[!] Gagal saat scan:', e)
        display_lcd("Sensor Error", "Coba lagi")
        return None

def verify_identity(fingerprint_id=None, face_check=True, threshold=0.55, resolution="480p", fps=15):
    """
    Memverifikasi identitas menggunakan sidik jari dan/atau wajah
    
    Args:
        fingerprint_id (int): ID sidik jari yang akan diverifikasi (opsional)
        face_check (bool): Apakah akan memeriksa wajah
        threshold (float): Threshold kecocokan wajah (0-1)
        resolution (str): Resolusi kamera yang digunakan
        fps (int): Frame rate yang digunakan
        
    Returns:
        tuple: (status, user_data) jika berhasil, (False, None) jika gagal
    """
    print(f"\n[+] Memverifikasi identitas {'dengan wajah' if face_check else 'tanpa wajah'}...")
    display_lcd("Verifikasi", "identitas...")
    
    if fingerprint_id is None:
        # Jika tidak ada fingerprint_id yang diberikan, verifikasi dengan wajah saja
        if not face_check:
            print("[!] Tidak ada metode verifikasi yang dipilih")
            display_lcd("Error", "Pilih metode")
            return False, None
        
        # Verifikasi dengan wajah
        if not ARCFACE_AVAILABLE:
            print("[!] Modul pengenalan wajah tidak tersedia")
            display_lcd("Error", "Modul wajah")
            return False, None
        
        # Inisialisasi kamera
        cap = initialize_camera(resolution=resolution, fps=fps)
        if not cap:
            print("[!] Gagal inisialisasi kamera")
            display_lcd("Error", "Kamera")
            return False, None
        
        # Muat database embedding wajah
        try:
            embeddings_dict = load_embeddings(EMBEDDINGS_PATH)
            if not embeddings_dict:
                print("[!] Database wajah kosong")
                display_lcd("Database", "Wajah kosong")
                cap.release()
                return False, None
        except Exception as e:
            print(f"[!] Gagal memuat embeddings: {e}")
            display_lcd("Error", "Data wajah")
            cap.release()
            return False, None
        
        print("[+] Database wajah dimuat. Silakan lihat ke kamera...")
        display_lcd("Lihat ke", "kamera")
        
        # Setup untuk pengambilan wajah
        face_found = False
        best_match_name = None
        best_match_score = 0
        face_embedding = None
        start_time = time.time()
        timeout = 15  # 15 detik timeout
        
        print("[+] Mencari wajah dalam frame...")
        
        while time.time() - start_time < timeout and not face_found:
            try:
                # Ambil frame dari kamera
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("[!] Gagal membaca frame dari kamera")
                    continue
                
                # Deteksi wajah
                face_img, bbox = detect_face_mtcnn(frame)
                
                if face_img is not None and bbox is not None:
                    # Tampilkan kotak di sekitar wajah
                    frame = draw_face_box(frame, bbox)
                    
                    # Proses wajah
                    face_tensor = preprocess_face(face_img)
                    if face_tensor is not None:
                        # Cek orientasi wajah
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
                        
                        # Hanya lakukan pengenalan jika wajah frontal
                        if frontal:
                            # Ekstrak embedding
                            face_embedding = extract_embedding(face_tensor)
                            
                            # Bandingkan dengan database
                            for name, saved_embeddings in embeddings_dict.items():
                                # Handle kedua format embedding (list atau array tunggal)
                                if isinstance(saved_embeddings, list):
                                    # Format list (multiple embeddings)
                                    for emb in saved_embeddings:
                                        similarity = compute_similarity(face_embedding, emb)
                                        if similarity > best_match_score:
                                            best_match_score = similarity
                                            best_match_name = name
                                else:
                                    # Format array tunggal (satu embedding)
                                    similarity = compute_similarity(face_embedding, saved_embeddings)
                                    if similarity > best_match_score:
                                        best_match_score = similarity
                                        best_match_name = name
                            
                            # Tampilkan skor kecocokan
                            cv2.putText(frame, f"Kecocokan: {best_match_score:.2f}", (10, 140), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                            
                            # Periksa apakah kecocokan cukup tinggi
                            if best_match_score >= threshold:
                                cv2.putText(frame, f"Dikenali: {best_match_name} ({best_match_score:.2f})", 
                                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                                face_found = True
                            else:
                                cv2.putText(frame, f"Tidak dikenali ({best_match_score:.2f})", 
                                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Tampilkan waktu tersisa
                remaining = int(timeout - (time.time() - start_time))
                cv2.putText(frame, f"Waktu: {remaining}s", (10, frame.shape[0] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Tampilkan threshold
                cv2.putText(frame, f"Threshold: {threshold}", (frame.shape[1] - 150, frame.shape[0] - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Tampilkan frame
                cv2.imshow("Verifikasi Wajah", frame)
                if cv2.waitKey(1) == 27:  # ESC
                    break
            except Exception as e:
                print(f"[!] Error saat mendeteksi wajah: {e}")
                continue
        
        # Bersihkan resource
        cap.release()
        cv2.destroyAllWindows()
        
        # Jika wajah ditemukan dan dikenali
        if face_found:
            # Cari pengguna di database berdasarkan nama
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, fingerprint_id FROM users WHERE name = ?", (best_match_name,))
            user_data = cursor.fetchone()
            conn.close()
            
            if user_data:
                print(f"[+] Wajah dikenali sebagai {best_match_name} (skor: {best_match_score:.2f})")
                display_lcd("Wajah dikenali", best_match_name)
                return True, user_data
            else:
                print(f"[!] Wajah dikenali sebagai {best_match_name} tapi tidak ada dalam database")
                display_lcd("Error", "Data tidak cocok")
                return False, None
        else:
            print("[!] Wajah tidak dikenali atau timeout")
            display_lcd("Wajah", "Tidak dikenali")
            # Jika wajah tidak dikenali, simpan sebagai wajah tidak dikenal
            capture_unknown_face(resolution=resolution, fps=fps)
            return False, None
    
    # Jika ada fingerprint_id
    else:
        # Cari pengguna di database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, fingerprint_id, face_embedding_path FROM users WHERE fingerprint_id = ?", (fingerprint_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if not user_data:
            print(f"[!] Sidik jari dengan ID {fingerprint_id} tidak terdaftar dalam database")
            display_lcd("Sidik jari", "Tidak terdaftar")
            return False, None
        
        user_id, name, _, face_embedding_path = user_data
        
        print(f"[+] Sidik jari dikenali sebagai {name}")
        display_lcd("Sidik jari OK", name)
        
        # Jika tidak perlu cek wajah, langsung return True
        if not face_check:
            return True, user_data
        
        # Jika perlu cek wajah
        print("[+] Memverifikasi wajah sebagai langkah kedua...")
        display_lcd("Verifikasi", "wajah...")
        
        # Cek apakah ada embedding wajah tersimpan
        if face_embedding_path and face_embedding_path == EMBEDDINGS_PATH and ARCFACE_AVAILABLE:
            # Lakukan verifikasi wajah
            cap = initialize_camera(resolution=resolution, fps=fps)
            if not cap:
                print("[!] Gagal inisialisasi kamera")
                display_lcd("Error", "Kamera")
                return False, None
            
            # Muat database embedding
            try:
                embeddings_dict = load_embeddings(EMBEDDINGS_PATH)
                if not embeddings_dict or name not in embeddings_dict:
                    print(f"[!] Data wajah untuk {name} tidak ditemukan")
                    display_lcd("Data Wajah", f"Tidak ada: {name}")
                    cap.release()
                    return False, None
            except Exception as e:
                print(f"[!] Gagal memuat embeddings: {e}")
                display_lcd("Error", "Data wajah")
                cap.release()
                return False, None
            
            # Ambil embedding tersimpan
            saved_embeddings = embeddings_dict[name]
            
            print("[+] Silakan lihat ke kamera untuk verifikasi wajah...")
            display_lcd("Verifikasi", "Lihat ke kamera")
            
            # Setup untuk pengambilan wajah
            face_verified = False
            start_time = time.time()
            timeout = 15
            
            # Perbaikan cek Numpy array
            # Cek apakah saved_embeddings ada dan valid
            if isinstance(saved_embeddings, list):
                if len(saved_embeddings) == 0:
                    print(f"[!] Data wajah untuk {name} kosong")
                    display_lcd("Data Wajah", "Kosong")
                    cap.release()
                    return False, None
            elif isinstance(saved_embeddings, np.ndarray):
                if saved_embeddings.size == 0:
                    print(f"[!] Data wajah untuk {name} kosong")
                    display_lcd("Data Wajah", "Kosong")
                    cap.release()
                    return False, None
            else:
                print(f"[!] Format data wajah tidak valid")
                display_lcd("Error", "Format data")
                cap.release()
                return False, None
            
            while time.time() - start_time < timeout and not face_verified:
                try:
                    # Ambil frame dari kamera
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        print("[!] Gagal membaca frame dari kamera")
                        continue
                    
                    # Deteksi wajah
                    face_img, bbox = detect_face_mtcnn(frame)
                    
                    if face_img is not None and bbox is not None:
                        # Tampilkan kotak di sekitar wajah
                        frame = draw_face_box(frame, bbox)
                        
                        # Proses wajah
                        face_tensor = preprocess_face(face_img)
                        if face_tensor is not None:
                            # Cek orientasi wajah
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
                            
                            # Hanya lakukan pengenalan jika wajah frontal
                            if frontal:
                                # Ekstrak embedding
                                face_embedding = extract_embedding(face_tensor)
                                
                                # Bandingkan dengan embedding tersimpan
                                if isinstance(saved_embeddings, list):
                                    # Format list (multiple embeddings)
                                    best_similarity = 0
                                    for emb in saved_embeddings:
                                        similarity = compute_similarity(face_embedding, emb)
                                        best_similarity = max(best_similarity, similarity)
                                else:
                                    # Format array tunggal (satu embedding)
                                    best_similarity = compute_similarity(face_embedding, saved_embeddings)
                                
                                # Tampilkan skor kecocokan
                                cv2.putText(frame, f"Kecocokan: {best_similarity:.2f}", (10, 140), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                                
                                # Verifikasi apakah wajah cocok dengan sidik jari
                                if best_similarity >= threshold:
                                    cv2.putText(frame, f"Verifikasi Berhasil: {name} ({best_similarity:.2f})", 
                                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                                    face_verified = True
                                else:
                                    cv2.putText(frame, f"Verifikasi Gagal ({best_similarity:.2f})", 
                                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    # Tampilkan waktu tersisa
                    remaining = int(timeout - (time.time() - start_time))
                    cv2.putText(frame, f"Waktu: {remaining}s", (10, frame.shape[0] - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                    # Tampilkan threshold
                    cv2.putText(frame, f"Threshold: {threshold}", (frame.shape[1] - 150, frame.shape[0] - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # Tampilkan nama yang diverifikasi
                    cv2.putText(frame, f"Verifikasi: {name}", (frame.shape[1] - 200, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    
                    # Tampilkan frame
                    cv2.imshow("Verifikasi Wajah", frame)
                    if cv2.waitKey(1) == 27:  # ESC
                        break
                except Exception as e:
                    print(f"[!] Error saat mendeteksi wajah: {e}")
                    continue
            
            # Bersihkan resource
            cap.release()
            cv2.destroyAllWindows()
            
            if face_verified:
                print(f"[+] Verifikasi wajah berhasil untuk {name}")
                display_lcd("Verifikasi OK", name)
                return True, user_data
            else:
                print(f"[!] Verifikasi wajah gagal untuk {name}")
                display_lcd("Verifikasi", "Gagal")
                # Simpan wajah yang tidak cocok
                capture_unknown_face(resolution=resolution, fps=fps)
                return False, None
        else:
            print("[!] Tidak ada data wajah tersimpan untuk verifikasi")
            display_lcd("Tidak ada", "Data wajah")
            return True, user_data  # Tetap return True karena sidik jari cocok

def display_embedding_file(file_path):
    """
    Menampilkan informasi dari file embedding
    
    Args:
        file_path: Path ke file embedding (.pkl, .json, .npy)
    """
    if not os.path.exists(file_path):
        print(f"[!] File embedding tidak ditemukan: {file_path}")
        return False
    
    try:
        # Jika file berformat PKL (pickle)
        if file_path.endswith('.pkl'):
            with open(file_path, 'rb') as f:
                embedding_data = pickle.load(f)
            
            print(f"\n=== Informasi File Embedding: {file_path} ===")
            print(f"Tipe data: {type(embedding_data)}")
            
            # Jika data berupa dictionary
            if isinstance(embedding_data, dict):
                print(f"Jumlah data: {len(embedding_data)}")
                print("Daftar key/nama pengguna:")
                
                for i, (key, value) in enumerate(embedding_data.items(), 1):
                    print(f"  {i}. {key}")
                    
                    # Tampilkan informasi tentang value
                    if isinstance(value, dict):
                        print(f"     Tipe: Dictionary dengan {len(value)} item")
                        print(f"     Keys: {list(value.keys())}")
                    elif isinstance(value, np.ndarray):
                        print(f"     Tipe: NumPy array dengan shape {value.shape}")
                    elif isinstance(value, list):
                        print(f"     Tipe: List dengan {len(value)} item")
                    else:
                        print(f"     Tipe: {type(value)}")
            
            # Jika data berupa NumPy array
            elif isinstance(embedding_data, np.ndarray):
                print(f"Shape: {embedding_data.shape}")
                print(f"Dtype: {embedding_data.dtype}")
            
            # Jika data berupa list
            elif isinstance(embedding_data, list):
                print(f"Jumlah item: {len(embedding_data)}")
                if len(embedding_data) > 0:
                    print(f"Tipe item pertama: {type(embedding_data[0])}")
            
            # Tipe data lainnya
            else:
                print(f"Informasi tambahan tidak tersedia untuk tipe data {type(embedding_data)}")
        
        # Jika file berformat JSON
        elif file_path.endswith('.json'):
            with open(file_path, 'r') as f:
                embedding_data = json.load(f)
            
            print(f"\n=== Informasi File Embedding: {file_path} ===")
            
            if isinstance(embedding_data, dict):
                print(f"Jumlah key: {len(embedding_data)}")
                print("Keys:")
                for key in embedding_data.keys():
                    print(f"  - {key}")
            elif isinstance(embedding_data, list):
                print(f"Jumlah item: {len(embedding_data)}")
        
        # Jika file berformat NPY
        elif file_path.endswith('.npy'):
            embedding_data = np.load(file_path)
            
            print(f"\n=== Informasi File Embedding: {file_path} ===")
            print(f"Tipe data: NumPy array")
            print(f"Shape: {embedding_data.shape}")
            print(f"Dtype: {embedding_data.dtype}")
        
        else:
            print(f"[!] Format file tidak didukung: {file_path}")
            return False
        
        return True
    
    except Exception as e:
        print(f"[!] Error saat membaca file embedding: {e}")
        return False

def list_files_in_directory(directory_path=None):
    """
    Menampilkan daftar file di suatu direktori
    
    Args:
        directory_path: Path direktori yang ingin dilihat isinya (opsional)
    """
    if directory_path is None or directory_path.strip() == "":
        directory_path = os.getcwd()  # Gunakan direktori saat ini jika tidak ada input
    
    try:
        # Pastikan path ada
        if not os.path.exists(directory_path):
            print(f"[!] Direktori tidak ditemukan: {directory_path}")
            return False
        
        # Pastikan itu adalah direktori
        if not os.path.isdir(directory_path):
            print(f"[!] Path yang dimasukkan bukan direktori: {directory_path}")
            return False
        
        # Dapatkan daftar semua file dan folder
        all_items = os.listdir(directory_path)
        
        # Pisahkan file dan folder
        files = [item for item in all_items if os.path.isfile(os.path.join(directory_path, item))]
        folders = [item for item in all_items if os.path.isdir(os.path.join(directory_path, item))]
        
        # Tampilkan hasil
        print(f"\n=== Isi Direktori: {directory_path} ===")
        
        print("\nFOLDER:")
        if folders:
            for i, folder in enumerate(sorted(folders), 1):
                print(f"  {i}. {folder}/")
        else:
            print("  (Tidak ada folder)")
        
        print("\nFILE:")
        if files:
            for i, file in enumerate(sorted(files), 1):
                file_path = os.path.join(directory_path, file)
                file_size = os.path.getsize(file_path)
                # Format ukuran file
                if file_size < 1024:
                    size_str = f"{file_size} B"
                elif file_size < 1024 * 1024:
                    size_str = f"{file_size / 1024:.1f} KB"
                else:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                print(f"  {i}. {file} ({size_str})")
        else:
            print("  (Tidak ada file)")
        
        # Tampilkan daftar file pickle khusus
        pickle_files = glob.glob(os.path.join(directory_path, "*.pkl"))
        if pickle_files:
            print("\nFILE PICKLE (.pkl):")
            for i, pkl in enumerate(sorted(pickle_files), 1):
                print(f"  {i}. {os.path.basename(pkl)}")
        
        return True
    
    except Exception as e:
        print(f"[!] Error saat membaca direktori: {e}")
        return False

def run_access_control_system():
    """Menjalankan sistem kontrol akses secara kontinu"""
    try:
        print("[INFO] Sistem kontrol akses dimulai")
        display_lcd("Sistem Siap", "Tempelkan jari")
        
        while True:
            # Menunggu verifikasi identitas
            # Tambahkan parameter explicit untuk menghindari error numpy array
            verification_result, _ = verify_identity()
            if verification_result:
                print("[+] Akses diberikan")
                # Buka pintu/selenoid sudah ditangani di dalam verify_identity()
                time.sleep(2)  # Tunggu sebentar sebelum siap menerima scan berikutnya
            else:
                print("[!] Akses ditolak")
                time.sleep(2)  # Tunggu sebentar sebelum siap menerima scan berikutnya
            
            # Reset LCD untuk scan berikutnya
            display_lcd("Sistem Siap", "Tempelkan jari")
            
            time.sleep(1)  # Mengurangi penggunaan CPU
    
    except KeyboardInterrupt:
        print("\n[INFO] Sistem dihentikan oleh pengguna")
    finally:
        # Cleanup
        if LCD_AVAILABLE and lcd:
            lcd.clear()
        if SELENOID_AVAILABLE and selenoid:
            selenoid.cleanup()
        print("[INFO] Sistem berhenti")

# Jalankan setup database saat modul diimpor
create_database()

# Fungsi utama jika dijalankan langsung
if __name__ == "__main__":
    print("===== SISTEM BIOMETRIK SIDIK JARI & WAJAH =====")
    print("1. Daftar Pengguna Baru (Sidik Jari & Wajah)")
    print("2. Daftar Pengguna dengan Embedding Wajah yang Sudah Ada")
    print("3. Verifikasi Identitas")
    print("4. Hapus Data Sidik Jari")
    print("5. Lihat Semua Pengguna")
    print("6. Tampilkan Informasi File Embedding")
    print("7. Lihat Daftar File di Folder")
    print("8. Jalankan Sistem Kontrol Akses")
    print("9. Lihat Wajah Tidak Dikenal")
    
    choice = input("Pilih menu: ")
    
    if choice == "1":
        enroll_user()
    elif choice == "2":
        # Tampilkan informasi data embedding yang tersedia
        if os.path.exists(EMBEDDINGS_PATH):
            print("\n[INFO] Menampilkan data embedding yang tersedia:")
            display_embedding_file(EMBEDDINGS_PATH)
            
            # Pilih nama dari daftar embedding
            try:
                with open(EMBEDDINGS_PATH, 'rb') as f:
                    embeddings_dict = pickle.load(f)
                
                if not isinstance(embeddings_dict, dict) or len(embeddings_dict) == 0:
                    print("[!] File embedding tidak berisi data yang valid")
                else:
                    print("\nPilih nama dari daftar di atas yang ingin didaftarkan sidik jari:")
                    username = input("Masukkan nama: ")
                    
                    if username in embeddings_dict:
                        # Daftarkan sidik jari untuk username yang sudah ada
                        print(f"\n[INFO] Mendaftarkan sidik jari untuk {username}")
                        fingerprint_id = enroll_fingerprint()
                        
                        if fingerprint_id is not None:
                            # Simpan ke database
                            try:
                                conn = sqlite3.connect(DB_PATH)
                                cursor = conn.cursor()
                                
                                # Cek apakah pengguna sudah ada di database
                                cursor.execute("SELECT id FROM users WHERE name = ?", (username,))
                                existing_user = cursor.fetchone()
                                
                                if existing_user:
                                    # Update data pengguna yang sudah ada
                                    cursor.execute(
                                        "UPDATE users SET fingerprint_id = ?, face_embedding_path = ? WHERE name = ?",
                                        (fingerprint_id, EMBEDDINGS_PATH, username)
                                    )
                                    print(f"[+] Data untuk {username} diperbarui dengan sidik jari baru")
                                else:
                                    # Buat data pengguna baru
                                    cursor.execute(
                                        "INSERT INTO users (name, fingerprint_id, face_embedding_path) VALUES (?, ?, ?)",
                                        (username, fingerprint_id, EMBEDDINGS_PATH)
                                    )
                                    print(f"[+] Pengguna {username} berhasil didaftarkan dengan sidik jari baru")
                                
                                conn.commit()
                                conn.close()
                            except sqlite3.IntegrityError:
                                print("[!] Error: Sidik jari sudah terdaftar untuk pengguna lain")
                                delete_fingerprint(fingerprint_id)
                            except Exception as e:
                                print(f"[!] Gagal menyimpan ke database: {e}")
                                delete_fingerprint(fingerprint_id)
                        else:
                            print("[!] Gagal mendaftarkan sidik jari")
                    else:
                        print(f"[!] Nama '{username}' tidak ditemukan dalam data embedding")
            except Exception as e:
                print(f"[!] Error membaca file embedding: {e}")
        else:
            print("[!] File embedding tidak ditemukan, gunakan opsi 1 untuk mendaftar")
    elif choice == "3":
        verify_identity()
    elif choice == "4":
        template_id = int(input("Masukkan ID sidik jari yang ingin dihapus: "))
        delete_fingerprint(template_id)
    elif choice == "5":
        # Tampilkan semua pengguna dari database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, fingerprint_id, face_embedding_path FROM users")
        users = cursor.fetchall()
        conn.close()
        
        if users:
            print("\n=== Daftar Pengguna ===")
            for user in users:
                print(f"ID: {user[0]}, Nama: {user[1]}, ID Sidik Jari: {user[2]}, Embedding: {user[3] or 'Tidak ada'}")
        else:
            print("[!] Belum ada pengguna terdaftar")
    elif choice == "6":
        embedding_path = input("Masukkan path ke file embedding wajah (.json/.npy/.pkl): ")
        display_embedding_file(embedding_path)
    elif choice == "7":
        directory_path = input("Masukkan path direktori (kosongkan untuk direktori saat ini): ")
        list_files_in_directory(directory_path)
    elif choice == "8":
        run_access_control_system()
    elif choice == "9":
        # Tampilkan daftar wajah tidak dikenal
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, image_path, timestamp, notes FROM unknown_faces ORDER BY timestamp DESC")
        unknown_faces = cursor.fetchall()
        conn.close()
        
        if unknown_faces:
            print("\n=== Daftar Wajah Tidak Dikenal ===")
            for face in unknown_faces:
                print(f"ID: {face[0]}, Path: {face[1]}, Waktu: {face[2]}, Catatan: {face[3]}")
        else:
            print("[!] Belum ada wajah tidak dikenal")
    else:
        print("[!] Pilihan tidak valid")
