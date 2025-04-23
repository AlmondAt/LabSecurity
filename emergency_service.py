#!/usr/bin/env python3
# emergency_service.py
# Layanan tombol emergency untuk selenoid

import RPi.GPIO as GPIO
import time
import signal
import sys
import logging
import os

# --- Konfigurasi ---
BUTTON_PIN = 17     # GPIO pin untuk tombol emergency
SELENOID_PIN = 18   # GPIO pin untuk selenoid
LED_PIN = 27        # GPIO pin untuk LED status (opsional)

# Durasi buka selenoid (dalam detik)
UNLOCK_DURATION = 5

# Setup logging
LOG_FILE = '/var/log/emergency_button.log'  # Ubah sesuai kebutuhan
LOG_LEVEL = logging.INFO

# --- Setup Logging ---
def setup_logging():
    """Setup logging ke file dan console"""
    log_dir = os.path.dirname(LOG_FILE)
    if not os.path.exists(log_dir) and log_dir:
        try:
            os.makedirs(log_dir)
        except:
            # Jika tidak bisa menulis ke /var/log, gunakan direktori saat ini
            global LOG_FILE
            LOG_FILE = 'emergency_button.log'
    
    logging.basicConfig(
        level=LOG_LEVEL,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )

# --- Fungsi GPIO ---
def setup_gpio():
    """Setup pin GPIO"""
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup pin
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(SELENOID_PIN, GPIO.OUT)
    GPIO.setup(LED_PIN, GPIO.OUT)
    
    # Status awal
    GPIO.output(SELENOID_PIN, GPIO.LOW)  # Selenoid terkunci
    GPIO.output(LED_PIN, GPIO.LOW)       # LED mati
    
    logging.info("GPIO initialized")

def blink_led(times=3, interval=0.2):
    """Mengedipkan LED beberapa kali"""
    for _ in range(times):
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(interval)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(interval)

def unlock_selenoid():
    """Membuka selenoid untuk durasi tertentu"""
    try:
        # Buka selenoid
        GPIO.output(SELENOID_PIN, GPIO.HIGH)
        GPIO.output(LED_PIN, GPIO.HIGH)  # LED menyala selama selenoid terbuka
        
        logging.warning(f"EMERGENCY: Selenoid unlocked for {UNLOCK_DURATION} seconds!")
        
        # Tunggu selama durasi yang ditentukan
        time.sleep(UNLOCK_DURATION)
        
        # Kunci kembali
        GPIO.output(SELENOID_PIN, GPIO.LOW)
        GPIO.output(LED_PIN, GPIO.LOW)
        
        logging.info("Selenoid locked again")
        
        # Kedipkan LED untuk indikasi selesai
        blink_led()
        
        return True
    except Exception as e:
        logging.error(f"Error unlocking selenoid: {e}")
        return False

def cleanup():
    """Cleanup GPIO saat program berakhir"""
    try:
        GPIO.output(SELENOID_PIN, GPIO.LOW)
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.cleanup()
        logging.info("GPIO cleaned up")
    except:
        pass

# --- Handler ---
def signal_handler(sig, frame):
    """Menangani sinyal untuk shutdown dengan bersih"""
    logging.info("Shutdown signal received, exiting...")
    cleanup()
    sys.exit(0)

def button_monitor():
    """Fungsi utama untuk memonitor tombol"""
    last_press_time = 0
    
    try:
        # Kedipkan LED saat startup untuk menunjukkan sistem siap
        blink_led(times=5, interval=0.1)
        
        logging.info("Emergency button system is running")
        
        while True:
            # Jika tombol ditekan (active low karena pull-up)
            if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                current_time = time.time()
                
                # Debouncing sederhana
                if current_time - last_press_time > 1:
                    logging.info("Emergency button pressed")
                    unlock_selenoid()
                    last_press_time = current_time
                    
                    # Tunggu sampai tombol dilepas
                    while GPIO.input(BUTTON_PIN) == GPIO.LOW:
                        time.sleep(0.1)
            
            # Mengurangi penggunaan CPU
            time.sleep(0.1)
    
    except Exception as e:
        logging.error(f"Error in button monitor: {e}")
    finally:
        cleanup()

# --- Main Program ---
if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Inisialisasi GPIO
        setup_gpio()
        
        # Mulai monitoring tombol
        button_monitor()
    
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        cleanup() 