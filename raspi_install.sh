#!/bin/bash

# Script instalasi sistem kontrol akses untuk Raspberry Pi
# Memerlukan: Raspberry Pi OS (minimal Buster)

# Fungsi untuk menampilkan pesan berwarna
print_color() {
    case $1 in
        "info") printf "\033[0;36m%s\033[0m\n" "$2" ;;  # Cyan
        "success") printf "\033[0;32m%s\033[0m\n" "$2" ;;  # Green
        "warning") printf "\033[0;33m%s\033[0m\n" "$2" ;;  # Yellow
        "error") printf "\033[0;31m%s\033[0m\n" "$2" ;;  # Red
    esac
}

# Verifikasi bahwa script dijalankan pada Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model; then
    print_color "warning" "Peringatan: Script ini didesain untuk Raspberry Pi."
    read -p "Lanjutkan instalasi? (y/n): " choice
    if [ "$choice" != "y" ]; then
        print_color "info" "Instalasi dibatalkan."
        exit 0
    fi
fi

# Direktori instalasi
INSTALL_DIR="$HOME/face_access_control"

# Memulai instalasi
print_color "info" "===== Instalasi Sistem Kontrol Akses Wajah & Sidik Jari ====="

# Buat direktori instalasi
print_color "info" "Membuat direktori instalasi..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Update sistem
print_color "info" "Memperbarui sistem..."
sudo apt update -y
sudo apt upgrade -y

# Instalasi dependensi
print_color "info" "Menginstal dependensi sistem..."
sudo apt install -y python3-pip python3-venv libjpeg-dev libatlas-base-dev \
    libopenjp2-7 libtiff5 libwebp-dev libffi-dev libssl-dev \
    i2c-tools python3-smbus libcap-dev

# Mengaktifkan I2C (untuk LCD)
print_color "info" "Mengaktifkan antarmuka I2C..."
if ! grep -q "i2c-dev" /etc/modules; then
    echo "i2c-dev" | sudo tee -a /etc/modules
    sudo raspi-config nonint do_i2c 0
fi

# Mengaktifkan Serial (untuk sensor sidik jari)
print_color "info" "Mengaktifkan antarmuka Serial..."
sudo raspi-config nonint do_serial 2 # Aktifkan serial tanpa login shell

# Mengatur izin untuk akses serial
sudo usermod -a -G dialout $USER
sudo chmod a+rw /dev/ttyAMA0
sudo chmod a+rw /dev/ttyS0

# Membuat virtual environment
print_color "info" "Membuat virtual environment Python..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Instalasi NumPy dan OpenCV
print_color "info" "Menginstal NumPy dan OpenCV (ini mungkin memerlukan waktu)..."
pip install numpy
pip install opencv-contrib-python==4.5.3.56

# Instalasi dependensi tambahan
print_color "info" "Menginstal dependensi Python lainnya..."
pip install smbus pyserial pillow scikit-image

# Instalasi PyTorch untuk ARM (versi ringan untuk Raspberry Pi)
print_color "info" "Menginstal PyTorch (ini akan memerlukan waktu)..."

# Deteksi arsitektur
ARCH=$(uname -m)
if [ "$ARCH" = "armv7l" ]; then
    # Raspberry Pi 3 dan sebelumnya
    pip install https://github.com/Kashu7100/pytorch-armv7l/raw/main/torch-1.7.0a0-cp37-cp37m-linux_armv7l.whl
    pip install https://github.com/Kashu7100/pytorch-armv7l/raw/main/torchvision-0.8.0a0+45f960c-cp37-cp37m-linux_armv7l.whl
elif [ "$ARCH" = "aarch64" ]; then
    # Raspberry Pi 4 dan 5 (64-bit)
    pip install torch==1.10.0 torchvision==0.11.1 -f https://torch.maku.ml/whl/stable.html
else
    print_color "warning" "Arsitektur tidak dikenali. Mencoba instalasi generic PyTorch..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# Instalasi MTCNN dan dependensi lain
print_color "info" "Menginstal MTCNN dan dependensi machine learning..."
pip install mtcnn facenet-pytorch==2.5.2 SQLAlchemy

# Meningkatkan Swap untuk performa lebih baik
print_color "info" "Meningkatkan ukuran swap untuk performa lebih baik..."
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Menyalin file konfigurasi untuk mode headless (opsional)
print_color "info" "Membuat file konfigurasi khusus Raspberry Pi..."
cat > raspi_config.py << 'EOF'
# Konfigurasi khusus untuk Raspberry Pi

# Set ke False jika berjalan dalam mode headless (tanpa display)
USE_DISPLAY = True

# Resolusi gambar yang lebih kecil untuk pemrosesan lebih cepat
IMAGE_RESIZE_WIDTH = 640  # Ukuran default 640x480
USE_THREADING = True  # Gunakan threading untuk UI lebih responsif

# Mengurangi resolusi gambar dari kamera untuk performa lebih baik
CAMERA_RESOLUTION = (640, 480)

# Konfigurasi GPIO
PIN_SELENOID = 18  # GPIO pin untuk selenoid
LCD_ADDRESS = 0x27  # Alamat I2C LCD (biasanya 0x27 atau 0x3F)

# Konfigurasi sensor sidik jari
FINGERPRINT_DEVICE = '/dev/ttyS0'  # Port serial untuk sensor sidik jari
FINGERPRINT_BAUDRATE = 57600  # Baud rate default untuk kebanyakan sensor
EOF

# Membuat script untuk menjalankan sistem saat startup
print_color "info" "Membuat script startup..."
cat > "$HOME/start_access_control.sh" << 'EOF'
#!/bin/bash
cd $HOME/face_access_control
source .venv/bin/activate
python access_control_system.py
EOF

chmod +x "$HOME/start_access_control.sh"

# Menambahkan ke crontab
print_color "info" "Mengatur sistem agar berjalan saat startup..."
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && $HOME/start_access_control.sh") | crontab -

# Selesai
print_color "success" "\n===== Instalasi Selesai ====="
print_color "info" "Langkah selanjutnya:"
print_color "info" "1. Salin semua file kode Python ke direktori $INSTALL_DIR"
print_color "info" "2. Jalankan setup awal dengan menjalankan: source .venv/bin/activate && python setup_database.py"
print_color "info" "3. Restart Raspberry Pi untuk menerapkan semua perubahan dengan: sudo reboot"
print_color "info" "4. Setelah restart, sistem akan berjalan secara otomatis, atau jalankan secara manual dengan: $HOME/start_access_control.sh"
print_color "success" "\nInstalasi selesai. Terima kasih!"

# Tanya restart
read -p "Restart Raspberry Pi sekarang? (y/n): " choice
if [ "$choice" = "y" ]; then
    print_color "info" "Restarting Raspberry Pi..."
    sudo reboot
fi 