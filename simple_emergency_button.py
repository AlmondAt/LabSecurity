#!/usr/bin/env python3
# simple_emergency_button.py
# Versi sederhana tombol emergency untuk membuka selenoid

import RPi.GPIO as GPIO
import time
import sys

# Konfigurasi
BUTTON_PIN = 17     # GPIO pin untuk tombol emergency
SELENOID_PIN = 18   # GPIO pin untuk selenoid
UNLOCK_DURATION = 15 # Durasi buka selenoid (dalam detik)

def setup():
    """Setup GPIO"""
    # Gunakan mode BCM
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup pin
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(SELENOID_PIN, GPIO.OUT)
    
    # Selenoid awalnya terkunci
    GPIO.output(SELENOID_PIN, GPIO.LOW)
    
    print("Tombol emergency siap")

def button_loop():
    """Monitoring tombol dalam loop"""
    print("Sistem berjalan. Tekan tombol emergency untuk membuka selenoid.")
    print("Tekan Ctrl+C untuk keluar")
    
    try:
        while True:
            # Jika tombol ditekan (active low karena pull-up)
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                print("\nTOMBOL EMERGENCY DITEKAN!")
                
                # Buka selenoid
                GPIO.output(SELENOID_PIN, GPIO.HIGH)
                print(f"Selenoid dibuka selama {UNLOCK_DURATION} detik...")
                
                # Tunggu selama durasi tertentu
                time.sleep(UNLOCK_DURATION)
                
                # Kunci kembali selenoid
                GPIO.output(SELENOID_PIN, GPIO.LOW)
                print("Selenoid dikunci kembali.")
                
                # Tunggu sampai tombol dilepas
                while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    time.sleep(0.1)
                
                print("Tombol dilepas. Sistem siap kembali.")
            
            # Mengurangi penggunaan CPU
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh pengguna")
    finally:
        # Cleanup
        GPIO.output(SELENOID_PIN, GPIO.LOW)  # Pastikan selenoid terkunci
        GPIO.cleanup()
        print("GPIO dibersihkan. Program berakhir.")

if __name__ == "__main__":
    setup()
    button_loop() 