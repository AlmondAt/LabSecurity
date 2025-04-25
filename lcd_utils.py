import RPi.GPIO as GPIO
import time
import smbus

# Konfigurasi untuk LCD 16x2 I2C
LCD_ADDRESS = 0x27  # Alamat I2C LCD (biasanya 0x27 atau 0x3F)
LCD_WIDTH = 16      # Jumlah karakter per baris
LCD_ROWS = 2        # Jumlah baris

# Konfigurasi LCD commands
LCD_CHR = 1  # Mode karakter
LCD_CMD = 0  # Mode perintah

LCD_LINE_1 = 0x80  # Alamat DDRAM untuk baris 1
LCD_LINE_2 = 0xC0  # Alamat DDRAM untuk baris 2

# Constants untuk backlight
LCD_BACKLIGHT = 0x08  # On
# LCD_BACKLIGHT = 0x00  # Off

# Enable bit
ENABLE = 0b00000100  # Enable bit

# Konstanta timing
E_PULSE = 0.0005
E_DELAY = 0.0005

class LCD:
    def __init__(self, address=LCD_ADDRESS, width=LCD_WIDTH, rows=LCD_ROWS):
        self.address = address
        self.width = width
        self.rows = rows
        self.bus = smbus.SMBus(1)  # Rev 2 Pi, 1 untuk bus I2C
        self.backlight_state = LCD_BACKLIGHT  # Backlight on
        self.initialized = False
    
    def init(self):
        """Inisialisasi display LCD"""
        try:
            self.lcd_byte(0x33, LCD_CMD)  # Inisialisasi
            self.lcd_byte(0x32, LCD_CMD)  # Inisialisasi
            self.lcd_byte(0x06, LCD_CMD)  # Cursor move direction
            self.lcd_byte(0x0C, LCD_CMD)  # Display On, Cursor Off, Blink Off
            self.lcd_byte(0x28, LCD_CMD)  # Mode 2 baris, 5x8 dot
            self.lcd_byte(0x01, LCD_CMD)  # Clear display
            time.sleep(E_DELAY)
            self.initialized = True
            return True
        except Exception as e:
            print(f"Error saat menginisialisasi LCD: {e}")
            return False
    
    def lcd_byte(self, bits, mode):
        """Mengirim byte ke LCD dalam mode yang ditentukan"""
        # Mode: 1 untuk karakter, 0 untuk perintah
        
        bits_high = mode | (bits & 0xF0) | self.backlight_state
        bits_low = mode | ((bits << 4) & 0xF0) | self.backlight_state

        # High bits
        self.bus.write_byte(self.address, bits_high)
        self.lcd_toggle_enable(bits_high)

        # Low bits
        self.bus.write_byte(self.address, bits_low)
        self.lcd_toggle_enable(bits_low)
    
    def lcd_toggle_enable(self, bits):
        """Toggle enable bit"""
        time.sleep(E_DELAY)
        self.bus.write_byte(self.address, (bits | ENABLE))
        time.sleep(E_PULSE)
        self.bus.write_byte(self.address, (bits & ~ENABLE))
        time.sleep(E_DELAY)
    
    # Alias untuk kompatibilitas
    send_byte = lcd_byte
    
    def clear(self):
        """Membersihkan display LCD"""
        self.lcd_byte(0x01, LCD_CMD)
        time.sleep(0.1)
    
    def display(self, text, line=1):
        """Menampilkan teks di baris yang ditentukan"""
        if not self.initialized:
            if not self.init():
                return False
        
        # Tentukan alamat baris
        if line == 1:
            line_address = LCD_LINE_1
        elif line == 2:
            line_address = LCD_LINE_2
        else:
            # Baris tidak valid
            return False
        
        # Format dan tampilkan string
        self.lcd_string(text, line_address)
        
        return True
    
    def lcd_string(self, message, line):
        """Mengirim string ke display"""
        # Truncate teks jika terlalu panjang
        message = message[:self.width]
        
        # Pad teks dengan spasi jika terlalu pendek
        message = message.ljust(self.width, ' ')
        
        # Kirim alamat baris
        self.lcd_byte(line, LCD_CMD)
        
        # Kirim karakter satu per satu
        for i in range(self.width):
            self.lcd_byte(ord(message[i]), LCD_CHR)
    
    def backlight(self, state):
        """Atur backlight LCD (True = on, False = off)"""
        if state:
            self.backlight_state = LCD_BACKLIGHT
        else:
            self.backlight_state = 0x00
        
        self.bus.write_byte(self.address, self.backlight_state)
    
    def display_message(self, line1="", line2=""):
        """Menampilkan pesan di kedua baris"""
        self.display(line1, 1)
        if line2:
            self.display(line2, 2)
    
    # Alias untuk show_message untuk kompatibilitas
    show_message = display_message

# Contoh penggunaan
if __name__ == "__main__":
    try:
        lcd = LCD()
        if lcd.init():
            lcd.clear()
            lcd.display("ArcFace System", 1)
            lcd.display("Initialized", 2)
            time.sleep(2)
            
            lcd.clear()
            lcd.display("Tap Fingerprint", 1)
            lcd.display("to continue...", 2)
            
            # Demo tampilan jam dan tanggal
            time.sleep(2)
            lcd.clear()
            lcd.display("Waktu:", 1)
            lcd.display(time.strftime("%H:%M:%S"), 2)
            time.sleep(2)
            
            lcd.clear()
            lcd.display("Tanggal:", 1)
            lcd.display(time.strftime("%d/%m/%Y"), 2)
            time.sleep(2)
            
            lcd.clear()
            lcd.display("Sampai jumpa!", 1)
            time.sleep(1)
            lcd.backlight(False)
        else:
            print("Gagal menginisialisasi LCD")
    except KeyboardInterrupt:
        print("Program dihentikan")
    finally:
        print("Program selesai") 