# Sistem Biometrik Sidik Jari dan Wajah dengan ArcFace

Sistem ini mengintegrasikan pengenalan sidik jari dan pengenalan wajah berbasis ArcFace untuk identifikasi biometrik dua faktor yang kuat. Dirancang untuk akses kontrol fisik menggunakan Raspberry Pi.

## Fitur

- **Identifikasi Dua Faktor** - Verifikasi sidik jari + wajah untuk keamanan tinggi
- **Pengenalan Wajah Berbasis ArcFace** - Mengenali wajah dari berbagai sudut dan ekspresi
- **Deteksi Wajah MTCNN** - Deteksi wajah yang akurat dan robust
- **Visualisasi Pose Wajah** - Bantuan visual untuk pengambilan foto berkualitas
- **Kontrol Selenoid** - Membuka kunci selenoid pintu otomatis
- **Tampilan LCD** - Instruksi real-time bagi pengguna
- **Database SQLite** - Penyimpanan data pengguna dan log
- **Perekaman Wajah Tidak Dikenal** - Menangkap foto wajah jika sidik jari tidak dikenali
- **Autostart Saat Boot** - Menjalankan sistem otomatis saat Raspberry Pi menyala

## Persyaratan Hardware

- Raspberry Pi (direkomendasikan: Pi 4 atau Pi 5)
- Sensor Sidik Jari (R305/R307 atau kompatibel)
- Kamera USB/Raspberry Pi Camera
- LCD I2C (opsional untuk tampilan status)
- Relay untuk mengontrol selenoid
- Selenoid untuk penguncian fisik

## Persyaratan Software

- Python 3.7+
- OpenCV
- TensorFlow / TensorFlow Lite
- MTCNN
- Numpy, SciPy, dan pustaka pendukung lainnya

## Instalasi

### Persiapan Raspberry Pi

```bash
# Update sistem
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv git libatlas-base-dev libopenjp2-7 libtiff5 libhdf5-dev

# Beri akses port serial
sudo usermod -a -G dialout pi
sudo chmod a+rw /dev/ttyUSB0  # Sesuaikan dengan port yang digunakan
```

### Instalasi Paket Python

```bash
# Buat virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package yang diperlukan
pip install -r requirements.txt
```

### Setup File Konfigurasi

Pastikan untuk menyesuaikan:

1. `PORT` di `fingerprint_utils.py` untuk port sensor sidik jari
2. `CAMERA_ID` untuk ID kamera yang digunakan
3. `SELENOID_PIN` untuk pin GPIO yang terhubung ke relay

## Menggunakan Sistem

### Menjalankan Aplikasi

```bash
python fingerprint_utils.py
```

### Menu Utama

Sistem menyediakan 9 pilihan menu:

1. **Daftar Pengguna Baru** - Mendaftarkan pengguna dengan sidik jari dan wajah
2. **Daftar Pengguna dengan Embedding Wajah yang Sudah Ada** - Menambahkan sidik jari untuk wajah yang sudah terdaftar
3. **Verifikasi Identitas** - Memverifikasi pengguna dengan sidik jari dan wajah
4. **Hapus Data Sidik Jari** - Menghapus sidik jari dari sensor dan database
5. **Lihat Semua Pengguna** - Menampilkan daftar pengguna terdaftar
6. **Tampilkan Informasi File Embedding** - Melihat detail embedding wajah
7. **Lihat Daftar File di Folder** - Menjelajahi file dalam direktori sistem
8. **Jalankan Sistem Kontrol Akses** - Mode operasional terus-menerus
9. **Lihat Wajah Tidak Dikenal** - Melihat log wajah yang tidak dikenali

### Alur Pendaftaran Pengguna

1. Pilih menu 1 untuk pendaftaran pengguna baru
2. Masukkan nama pengguna (misalnya "Fariz")
3. Ikuti petunjuk untuk scan sidik jari (tempelkan jari, angkat, tempelkan lagi)
4. Pilih metode pendaftaran wajah:
   - **Metode 1**: Ambil 5 foto dengan pose berbeda (rekomendasi)
   - **Metode 2**: Ambil 1 foto sederhana
   - **Metode 3**: Gunakan embedding yang sudah ada

#### Pengambilan 5 Foto (ArcFace)

1. Posisikan wajah depan kamera
2. Ikuti instruksi untuk 5 pose berbeda:
   - Wajah frontal
   - Wajah miring ke kiri
   - Wajah miring ke kanan
   - Ekspresi tersenyum
   - Ekspresi lain (bebas)
3. Tekan SPASI untuk mengambil foto pada setiap pose
4. Tekan 'a' untuk mengaktifkan/menonaktifkan tampilan sudut wajah

### Alur Verifikasi

1. Pilih menu 3 untuk verifikasi atau menu 8 untuk mode kontrol akses
2. Tempelkan jari pada sensor
3. Jika sidik jari dikenali, sistem akan meminta verifikasi wajah
4. Posisikan wajah di depan kamera
5. Sistem menampilkan skor kecocokan dan hasil verifikasi
6. Jika dua faktor terverifikasi, selenoid akan terbuka

### Skenario Penggunaan

#### Verifikasi Berhasil
- Sidik jari dikenali dan wajah terverifikasi
- LCD menampilkan "Selamat Datang, [Nama]"
- Selenoid dibuka selama 5 detik

#### Verifikasi Gagal - Wajah Tidak Cocok
- Sidik jari dikenali tapi wajah tidak cocok
- LCD menampilkan "Akses Ditolak, Wajah tidak cocok"
- Selenoid tetap terkunci

#### Verifikasi Gagal - Sidik Jari Tidak Dikenali
- Sidik jari tidak dikenali
- Kamera mengambil gambar wajah sebagai "Unknown"
- Gambar disimpan di folder "unknown_faces"
- LCD menampilkan "Akses Ditolak, Sidik jari asing"

## Menjalankan Saat Boot

Untuk menjalankan sistem biometrik otomatis saat Raspberry Pi menyala:

```bash
# Berikan izin eksekusi pada script autostart
sudo chmod +x /home/pi/ArcFace/biometric_autostart.sh

# Salin file service ke folder systemd
sudo cp /home/pi/ArcFace/biometric_service.service /etc/systemd/system/

# Aktifkan service
sudo systemctl enable biometric_service.service

# Mulai service
sudo systemctl start biometric_service.service
```

## Struktur Sistem

- `fingerprint_utils.py` - Modul utama dengan fungsi sensor dan alur verifikasi
- `mtcnn_utils.py` - Utility deteksi wajah dengan MTCNN
- `arcface_utils.py` - Fungsi ekstraksi embedding dan verifikasi wajah ArcFace
- `head_pose.py` - Estimasi pose kepala untuk pengambilan foto berkualitas
- `selenoid_utils.py` - Kontrol selenoid melalui GPIO
- `lcd_utils.py` - Antarmuka LCD untuk feedback pengguna
- `biometrics.db` - Database SQLite untuk data pengguna
- `embeddings.pkl` - File penyimpanan embeddings wajah
- `/photos` - Folder untuk foto wajah terdaftar
- `/unknown_faces` - Folder untuk wajah tidak dikenali

## Catatan Teknis

- Database SQLite disimpan di file `biometrics.db`
- Embeddings wajah disimpan di `embeddings.pkl`
- Foto disimpan di folder `photos/` dengan format `[nama]_[nomor].jpg`
- Wajah tidak dikenali disimpan di `unknown_faces/` dengan timestamp
- Threshold untuk kecocokan wajah: 0.6 (dapat disesuaikan di fungsi `verify_identity()`)

## Penyesuaian

### Mengubah Port Sensor Sidik Jari
```python
PORT = 'COM5'  # Windows (default)
PORT = '/dev/ttyUSB0'  # Linux/Raspberry Pi
```

### Mengubah ID Kamera
```python
CAMERA_ID = 0  # Ubah ke ID kamera yang sesuai
```

### Mengubah Pin Selenoid
```python
SELENOID_PIN = 18  # Ubah ke GPIO pin yang terhubung ke relay
```

### Mengubah Waktu Buka Selenoid
```python
UNLOCK_DURATION = 5  # Durasi dalam detik
```

## Troubleshooting

- **Sensor Sidik Jari Tidak Terbaca**: Periksa koneksi kabel dan port
- **Kamera Tidak Berfungsi**: Periksa ID kamera dan instalasi driver
- **ArcFace Tidak Berfungsi**: Pastikan TensorFlow terpasang dengan benar
- **Selenoid Tidak Terbuka**: Periksa koneksi GPIO dan relay
- **LCD Tidak Menampilkan**: Periksa koneksi I2C dan alamat LCD

## Lisensi

Proyek ini didistribusikan di bawah lisensi MIT. Lihat file `LICENSE` untuk informasi lebih lanjut.

## Kontribusi

Silakan berkontribusi dengan membuat issue atau pull request ke repository ini. 