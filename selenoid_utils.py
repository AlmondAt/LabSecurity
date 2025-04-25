from gpiozero import OutputDevice
import time
import RPi.GPIO as GPIO  # Tetap import GPIO untuk kompatibilitas

# Konstanta GPIO untuk selenoid
DEFAULT_SELENOID_PIN = 18  # GPIO pin untuk selenoid

class Selenoid:
    def __init__(self, pin=DEFAULT_SELENOID_PIN):
        self.pin = pin
        self.initialized = False
        self.solenoid = None  # Akan diinisialisasi dengan OutputDevice
    
    def init(self):
        """Inisialisasi selenoid menggunakan gpiozero"""
        try:
            # Inisialisasi menggunakan gpiozero
            self.solenoid = OutputDevice(self.pin, active_high=True, initial_value=False)
            
            self.initialized = True
            print("Selenoid berhasil diinisialisasi menggunakan gpiozero")
            return True
        except Exception as e:
            print(f"Error saat menginisialisasi selenoid: {e}")
            # Coba metode GPIO jika gpiozero gagal
            try:
                # Gunakan mode BCM
                GPIO.setmode(GPIO.BCM)
                # Atur pin sebagai output
                GPIO.setup(self.pin, GPIO.OUT)
                # Pastikan selenoid terkunci saat inisialisasi
                GPIO.output(self.pin, GPIO.LOW)
                
                self.initialized = True
                print("Selenoid berhasil diinisialisasi menggunakan GPIO")
                return True
            except Exception as e2:
                print(f"Error fallback GPIO: {e2}")
                return False
    
    def unlock(self, duration=5):
        """Buka kunci selenoid selama durasi tertentu (dalam detik)"""
        if not self.initialized:
            if not self.init():
                return False
        
        try:
            # Aktifkan selenoid (buka kunci)
            if self.solenoid:
                # Menggunakan gpiozero
                self.solenoid.on()
                print(f"Selenoid dibuka selama {duration} detik")
                
                # Tunggu selama durasi yang ditentukan
                time.sleep(duration)
                
                # Nonaktifkan selenoid (kunci)
                self.solenoid.off()
                print("Selenoid dikunci kembali")
            else:
                # Fallback ke GPIO
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
            if self.solenoid:
                self.solenoid.off()
            else:
                GPIO.output(self.pin, GPIO.LOW)
                
            print("Selenoid dikunci")
            return True
        except Exception as e:
            print(f"Error saat mengunci selenoid: {e}")
            return False
    
    def cleanup(self):
        """Membersihkan sumber daya"""
        if self.initialized:
            try:
                # Pastikan selenoid terkunci
                if self.solenoid:
                    self.solenoid.off()
                    self.solenoid.close()  # Tutup perangkat gpiozero
                else:
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
        
        print("Program dimulai. Tekan CTRL+C untuk keluar.")
        print("Solenoid akan aktif dan non-aktif setiap 1 detik...")
        
        count = 0
        while count < 5:  # Demo 5 kali buka-tutup
            # Buka selenoid
            print("Selenoid AKTIF")
            if selenoid.solenoid:
                selenoid.solenoid.on()
            else:
                GPIO.output(selenoid.pin, GPIO.HIGH)
                
            # Tunggu 1 detik
            time.sleep(1)
            
            # Tutup selenoid
            print("Selenoid MATI")
            if selenoid.solenoid:
                selenoid.solenoid.off()
            else:
                GPIO.output(selenoid.pin, GPIO.LOW)
                
            # Tunggu 1 detik
            time.sleep(1)
            
            count += 1
        
        print("Demo selesai")
        
        print("Membuka kunci selama 3 detik...")
        selenoid.unlock(3)
        
        # Membuka kunci segera setelah dikunci
        print("Membuka kunci lagi selama 2 detik...")
        selenoid.unlock(2)
        
    except KeyboardInterrupt:
        print("\nProgram dihentikan oleh pengguna")
    finally:
        # Pastikan selalu membersihkan GPIO
        selenoid.cleanup()
        print("Program selesai.") 