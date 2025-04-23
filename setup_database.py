import os
import argparse
from database_utils import AccessDatabase
from fingerprint_utils import FingerprintSensor

def setup_directories():
    """Membuat direktori yang diperlukan untuk sistem"""
    directories = [
        'data',
        'data/unknown',
        'photos',
        'models'
    ]
    
    print("Membuat direktori...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  {directory}/")
    
    print("Direktori berhasil dibuat.")

def setup_database():
    """Inisialisasi database"""
    print("Inisialisasi database...")
    db = AccessDatabase()
    
    if db.connect():
        print("Database berhasil diinisialisasi.")
        db.close()
        return True
    else:
        print("Gagal menginisialisasi database!")
        return False

def create_admin_user(name="Admin", finger_id=None):
    """Membuat pengguna admin"""
    print(f"Membuat pengguna admin '{name}'...")
    db = AccessDatabase()
    
    if not db.connect():
        print("Gagal terhubung ke database!")
        return False
    
    # Periksa apakah admin sudah ada
    admin_result = db.get_user_by_name(name)
    
    if admin_result["success"]:
        print(f"Pengguna admin '{name}' sudah ada dengan ID: {admin_result['user_id']}")
        db.close()
        return True
    
    # Jika perlu mendaftarkan sidik jari
    if finger_id is not None:
        result = db.add_user(name, finger_id, access_level=2)
    else:
        result = db.add_user(name, access_level=2)
    
    if result["success"]:
        print(f"Pengguna admin '{name}' berhasil dibuat dengan ID: {result['user_id']}")
        db.close()
        return True
    else:
        print(f"Gagal membuat pengguna admin: {result['message']}")
        db.close()
        return False

def register_admin_fingerprint(name="Admin"):
    """Mendaftarkan sidik jari untuk admin"""
    print("Mendaftarkan sidik jari admin...")
    
    # Inisialisasi sensor sidik jari
    sensor = FingerprintSensor()
    if not sensor.connect():
        print("Gagal terhubung ke sensor sidik jari!")
        return None
    
    # Tetapkan ID 1 untuk admin
    finger_id = 1
    
    print("Silakan ikuti instruksi untuk mendaftarkan sidik jari admin:")
    result = sensor.enroll_finger(finger_id)
    
    if result["success"]:
        print(f"Pendaftaran sidik jari admin berhasil dengan ID: {result['finger_id']}")
        sensor.disconnect()
        return finger_id
    else:
        print(f"Pendaftaran sidik jari admin gagal: {result['message']}")
        sensor.disconnect()
        return None

def init_system(with_admin=True, with_fingerprint=False):
    """Inisialisasi seluruh sistem"""
    print("\n=== Inisialisasi Sistem Kontrol Akses ===\n")
    
    # Buat direktori
    setup_directories()
    
    # Inisialisasi database
    if not setup_database():
        return False
    
    # Buat pengguna admin jika diminta
    if with_admin:
        finger_id = None
        
        # Daftarkan sidik jari admin jika diminta
        if with_fingerprint:
            finger_id = register_admin_fingerprint()
        
        if not create_admin_user(finger_id=finger_id):
            print("Peringatan: Gagal membuat pengguna admin, tetapi setup tetap dilanjutkan.")
    
    print("\n=== Inisialisasi Selesai ===")
    print("Sistem siap digunakan.")
    print("Jalankan 'python access_control_system.py' untuk memulai sistem.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Setup Sistem Kontrol Akses')
    parser.add_argument('--no-admin', action='store_true', help='Jangan buat pengguna admin')
    parser.add_argument('--with-fingerprint', action='store_true', help='Daftarkan sidik jari admin')
    
    args = parser.parse_args()
    
    init_system(with_admin=not args.no_admin, with_fingerprint=args.with_fingerprint) 