import RPi.GPIO as GPIO
import time

# Konstanta GPIO untuk selenoid
DEFAULT_SELENOID_PIN = 18  # GPIO pin untuk selenoid, sesuaikan dengan wiring

class Selenoid:
    def __init__(self, pin=DEFAULT_SELENOID_PIN):
        self.pin = pin
        self.initialized = False
    
    def init(self):
        """Inisialisasi selenoid"""
        try:
            # Gunakan mode BCM
            GPIO.setmode(GPIO.BCM)
            # Atur pin sebagai output
            GPIO.setup(self.pin, GPIO.OUT)
            # Pastikan selenoid terkunci saat inisialisasi
            GPIO.output(self.pin, GPIO.LOW)
            
            self.initialized = True
            return True
        except Exception as e:
            print(f"Error saat menginisialisasi selenoid: {e}")
            return False
    
    def unlock(self, duration=5):
        """Buka kunci selenoid selama durasi tertentu (dalam detik)"""
        if not self.initialized:
            if not self.init():
                return False
        
        try:
            # Aktifkan selenoid (buka kunci)
            GPIO.output(self.pin, GPIO.HIGH)
            print(f"Selenoid dibuka selama {duration} detik")
            
            # Tunggu selama durasi yang ditentukan
            time.sleep(duration)
            
            # Nonaktifkan selenoid (kunci)
            GPIO.output(self.pin, GPIO.LOW)
            print("Selenoid dikunci kembali")
            
            return True
        except Exception as e:
            print(f"Error saat mengoperasikan selenoid: {e}")
            return False
    
    def lock(self):
        """Mengunci kembali selenoid"""
        if not self.initialized:
            if not self.init():
                return False
        
        try:
            # Nonaktifkan selenoid (kunci)
            GPIO.output(self.pin, GPIO.LOW)
            print("Selenoid dikunci")
            return True
        except Exception as e:
            print(f"Error saat mengunci selenoid: {e}")
            return False
    
    def cleanup(self):
        """Membersihkan sumber daya GPIO"""
        if self.initialized:
            try:
                # Pastikan selenoid terkunci
                GPIO.output(self.pin, GPIO.LOW)
                # Cleanup GPIO
                GPIO.cleanup(self.pin)
                self.initialized = False
                print("Cleanup selenoid pin berhasil")
                return True
            except Exception as e:
                print(f"Error saat cleanup selenoid: {e}")
                return False

# Contoh penggunaan
if __name__ == "__main__":
    try:
        selenoid = Selenoid()
        selenoid.init()
        
        print("Membuka kunci selama 3 detik...")
        selenoid.unlock(3)
        
        # Membuka kunci segera setelah dikunci
        print("Membuka kunci lagi selama 2 detik...")
        selenoid.unlock(2)
        
    finally:
        # Pastikan selalu membersihkan GPIO
        selenoid.cleanup() 