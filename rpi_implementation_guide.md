# Panduan Implementasi di Raspberry Pi

Berikut adalah langkah-langkah untuk mengimplementasikan perubahan yang sama pada kode di Raspberry Pi:

## 1. File yang Perlu Diperbarui

- `mtcnn_utils.py` - Fungsi deteksi wajah yang ditingkatkan
- `arcface_utils.py` - Fungsi ekstraksi embedding yang diperbarui
- `head_pose.py` - Fungsi perhitungan orientasi wajah yang ditingkatkan
- `face_recognition_test_percobaan.py` - Kode utama pengenalan wajah 
- `fingerprint_utils.py` - Modul integrasi sidik jari dan wajah
- (Baru) `check_embedding_format.py` - Alat diagnostik format embedding
- (Baru) `convert_to_list_format.py` - Konversi embedding ke format list

## 2. Perubahan Kamera

Raspberry Pi mungkin memerlukan pengaturan kamera yang berbeda:

- Untuk kamera USB: MJPEG format, resolusi 480p (640x480), 15 FPS
- Untuk Raspberry Pi Camera Module: Gunakan picamera library

```python
# Di Raspberry Pi dengan Pi Camera Module, modifikasi initialize_camera():
def initialize_camera_picamera(resolution="480p", fps=15):
    try:
        # Jika picamera tersedia, gunakan itu
        import picamera
        import picamera.array
        
        # Pilih resolusi
        if resolution == "720p":
            width, height = 1280, 720
        else:  # 480p default
            width, height = 640, 480
            
        # Buat objek PiCamera
        camera = picamera.PiCamera()
        camera.resolution = (width, height)
        camera.framerate = fps
        
        # Buat objek array untuk menyimpan frame
        raw_capture = picamera.array.PiRGBArray(camera, size=(width, height))
        
        # Tunggu kamera stabil
        time.sleep(0.5)
        
        print(f"[INFO] Pi Camera siap: {width}x{height} @ {fps} FPS")
        return camera, raw_capture
    except ImportError:
        print("[INFO] PiCamera tidak tersedia, menggunakan USB camera")
        # Gunakan USB camera sebagai fallback
        return initialize_camera(resolution, fps)
```

## 3. Pengoptimalan Performa

Raspberry Pi memiliki daya komputasi lebih rendah, sehingga perlu pengoptimalan:

- Kurangi resolusi ke 320x240 untuk performa lebih baik (Raspberry Pi 3)
- Kurangi FPS ke 10 jika pengenalan wajah terlalu lambat
- Matikan tampilan debug jika tidak diperlukan

## 4. Konversi Format Embedding

File embedding perlu dikonversi ke format list (jika belum) untuk mendukung multiple embedding per orang:

```bash
# Konversi file embedding dengan membuat backup
python convert_to_list_format.py --input embeddings.pkl --output embeddings_list_format.pkl --backup
```

## 5. Perintah untuk Menjalankan

Gunakan parameter baris perintah untuk mengatur program:

```bash
# Jalankan pengenalan wajah dengan threshold yang diubah
python face_recognition_test_percobaan.py --threshold 0.55 --resolution 480p --fps 15 --embeddings embeddings_list_format.pkl

# Untuk performa lebih baik (Pi 3)
python face_recognition_test_percobaan.py --threshold 0.55 --resolution 480p --fps 10 --embeddings embeddings_list_format.pkl

# Jika menggunakan Pi Camera Module, modifikasi program untuk menggunakan mode picamera
```

## 6. Troubleshooting

Jika mengalami masalah:

1. **Error kamera**: 
   - Periksa path device kamera di Raspberry Pi (biasanya `/dev/video0`)
   - Coba gunakan Pi Camera Module dengan picamera library

2. **Performa lambat**:
   - Kurangi resolusi dan FPS
   - Nonaktifkan visualisasi yang tidak penting 
   - Pertimbangkan untuk menggunakan model yang lebih ringan (MobileFaceNet)

3. **Kesalahan format embedding**:
   - Jalankan `python check_embedding_format.py` untuk memeriksa format
   - Konversi ke format list jika perlu dengan `convert_to_list_format.py`

4. **GPIO untuk selenoid**:
   - Pastikan koneksi GPIO pada Raspberry Pi sesuai dengan konfigurasi
   - Sesuaikan pin selenoid di kode jika perlu

## 7. Optimalisasi Lanjutan

Untuk Raspberry Pi dengan RAM terbatas:

- Gunakan model yang dioptimalkan untuk edge devices
- Pertimbangkan untuk menggunakan Coral USB Accelerator
- Kurangi ukuran embedding database dengan memilih orang-orang yang relevan

## 8. Tambahan untuk Implementasi di Raspberry Pi

- Pastikan semua library yang diperlukan sudah diinstal
- Perhatikan versi OpenCV (minimal 4.5.x) dan PyTorch
- Sesuaikan path file dan direktori dengan struktur di Raspberry Pi 