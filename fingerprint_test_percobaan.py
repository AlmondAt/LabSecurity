#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skenario Percobaan 1: 
Selenoid merespon jika sidik jari benar, jika tidak tidak terjadi apa2,
LCD MENAMPILKAN KONDISI BENAR DAN TIDAKNYA.
"""

from pyfingerprint.pyfingerprint import PyFingerprint
import time
import sqlite3
import os
import RPi.GPIO as GPIO

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

# Konfigurasi sensor sidik jari
PORT = '/dev/ttyUSB0'   # Ubah kalau port-nya beda
BAUDRATE = 57600

# Konfigurasi database
DB_PATH = 'biometrics.db'

# Konfigurasi selenoid
SELENOID_PIN = 18  # GPIO pin untuk selenoid
UNLOCK_DURATION = 5  # Durasi membuka selenoid (detik)

# Inisialisasi LCD
lcd = None
if LCD_AVAILABLE:
    try:
        lcd = LCD()
        lcd.init()
        lcd.clear()
        lcd.display_message("Test Sidik Jari", "Siap...")
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
                display_lcd(f"Akses Diterima", f"Selamat {user[1]}")
                
                # Buka selenoid karena sidik jari benar
                unlock_door()
                
                return user[0]  # Return user_id
            else:
                print('[!] Data pengguna tidak ditemukan di database.')
                display_lcd("Data Error", "Kontak admin")
                return None

    except Exception as e:
        print(f'[!] Gagal saat scan: {e}')
        display_lcd("Sensor Error", "Coba lagi")
        return None

def main():
    """Fungsi utama program percobaan"""
    # Tampilkan pesan selamat datang
    display_lcd("Test Percobaan 1", "Scan Sidik Jari")
    time.sleep(2)
    
    # Loop utama
    try:
        while True:
            print("\n[PERCOBAAN 1] Tes Verifikasi Sidik Jari")
            display_lcd("Tempelkan", "Sidik Jari")
            
            # Scan sidik jari
            user_id = scan_fingerprint()
            
            if user_id is not None:
                # Sidik jari benar, selenoid sudah terbuka di fungsi scan_fingerprint
                time.sleep(3)
            else:
                # Sidik jari salah, tidak ada aksi selenoid
                time.sleep(3)
            
            # Reset tampilan
            display_lcd("Test Percobaan 1", "Scan Sidik Jari")
            
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