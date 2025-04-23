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

# Konstanta timing
E_PULSE = 0.0005
E_DELAY = 0.0005

class LCD:
    def __init__(self, address=LCD_ADDRESS, width=LCD_WIDTH, rows=LCD_ROWS):
        self.address = address
        self.width = width
        self.rows = rows
        self.bus = smbus.SMBus(1)  # Rev 2 Pi, 1 untuk bus I2C
        self.backlight_state = 0x08  # Backlight on
        self.initialized = False
    
    def init(self):
        """Inisialisasi display LCD"""
        try:
            self.send_byte(0x33, LCD_CMD)  # Inisialisasi
            self.send_byte(0x32, LCD_CMD)  # Inisialisasi
            self.send_byte(0x28, LCD_CMD)  # Mode 2 baris, 5x8 dot
            self.send_byte(0x0C, LCD_CMD)  # Display on, cursor off, blink off
            self.send_byte(0x06, LCD_CMD)  # Increment cursor, no shift
            self.send_byte(0x01, LCD_CMD)  # Clear display
            time.sleep(0.2)
            self.initialized = True
            return True
        except Exception as e:
            print(f"Error saat menginisialisasi LCD: {e}")
            return False
    
    def send_byte(self, bits, mode):
        """Mengirim byte ke LCD dalam mode yang ditentukan"""
        # Mode: 1 untuk karakter, 0 untuk perintah
        
        # Bits high
        bits_high = mode | (bits & 0xF0) | self.backlight_state
        self.bus.write_byte(self.address, bits_high)
        
        # E line high
        self.bus.write_byte(self.address, bits_high | 0x04)
        time.sleep(E_PULSE)
        
        # E line low
        self.bus.write_byte(self.address, bits_high & ~0x04)
        time.sleep(E_DELAY)
        
        # Bits low
        bits_low = mode | ((bits << 4) & 0xF0) | self.backlight_state
        self.bus.write_byte(self.address, bits_low)
        
        # E line high
        self.bus.write_byte(self.address, bits_low | 0x04)
        time.sleep(E_PULSE)
        
        # E line low
        self.bus.write_byte(self.address, bits_low & ~0x04)
        time.sleep(E_DELAY)
    
    def clear(self):
        """Membersihkan display LCD"""
        self.send_byte(0x01, LCD_CMD)
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
        
        # Kirim alamat baris
        self.send_byte(line_address, LCD_CMD)
        
        # Truncate teks jika terlalu panjang
        text = text[:self.width]
        
        # Pad teks dengan spasi jika terlalu pendek
        text = text.ljust(self.width, ' ')
        
        # Kirim karakter satu per satu
        for char in text:
            self.send_byte(ord(char), LCD_CHR)
        
        return True
    
    def backlight(self, state):
        """Atur backlight LCD (True = on, False = off)"""
        if state:
            self.backlight_state = 0x08
        else:
            self.backlight_state = 0x00
        
        self.bus.write_byte(self.address, self.backlight_state)
    
    def show_message(self, message, line1_prefix="", line2_prefix=""):
        """Menampilkan pesan di kedua baris dengan prefiks opsional"""
        lines = message.split('\n')
        
        if len(lines) >= 1:
            self.display(line1_prefix + lines[0], 1)
        
        if len(lines) >= 2:
            self.display(line2_prefix + lines[1], 2)
        elif line2_prefix:
            self.display(line2_prefix, 2)

# Contoh penggunaan
if __name__ == "__main__":
    lcd = LCD()
    if lcd.init():
        lcd.clear()
        lcd.display("ArcFace System", 1)
        lcd.display("Initialized", 2)
        time.sleep(2)
        
        lcd.clear()
        lcd.display("Tap Fingerprint", 1)
        lcd.display("to continue...", 2)
        
        time.sleep(5)
        lcd.backlight(False)
    else:
        print("Gagal menginisialisasi LCD") 