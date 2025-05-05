# Panduan Perbaikan Error ValueError Langsung di Raspberry Pi

## Error yang Terjadi
```
Traceback (most recent call last):
  File "/home/pi/Skripsi/LabSecurity/fingerprint_utils.py", line 1652, in <module>
    run_access_control_system()
  File "/home/pi/Skripsi/LabSecurity/fingerprint_utils.py", line 1520, in run_access_control_system
    if verify_identity():
       ^^^^^^^^^^^^^^^^^
  File "/home/pi/Skripsi/LabSecurity/fingerprint_utils.py", line 1169, in verify_identity
    if not user_embeddings:
ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()
```

## Langkah-langkah Perbaikan

### 1. Cara Cepat - Langsung di Raspberry Pi:

```bash
# Buka terminal di Raspberry Pi
cd /home/pi/Skripsi/LabSecurity

# Buat backup file
cp fingerprint_utils.py fingerprint_utils.py.backup

# Edit file
nano +1169 fingerprint_utils.py
```

### 2. Temukan baris yang bermasalah (sekitar baris 1169)

```python
if not user_embeddings:
```

### 3. Ganti baris tersebut dengan kode yang aman untuk NumPy array:

```python
if isinstance(user_embeddings, np.ndarray):
    if user_embeddings.size == 0:
        print("[!] Data wajah kosong")
        display_lcd("Data Wajah", "Kosong")
        cap.release()
        return False, None
elif not user_embeddings:
```

### 4. Simpan file (Ctrl+O, Enter, Ctrl+X)

### 5. Jalankan kembali program:

```bash
python fingerprint_utils.py
```

## Solusi Alternatif

Jika perbaikan di atas tidak berhasil, ada beberapa solusi alternatif:

### 1. Gunakan fungsi run_access_control_system() baru:

Buka file dengan `nano fingerprint_utils.py`, cari fungsi `run_access_control_system()` dan ganti seluruh fungsi dengan implementasi yang ada di file `verify_identity_fix.py`.

### 2. Skip verifikasi wajah sementara:

Modifikasi fungsi `run_access_control_system()` untuk menjalankan verifikasi sidik jari saja:

```python
def run_access_control_system():
    """Menjalankan sistem kontrol akses secara kontinu"""
    try:
        print("[INFO] Sistem kontrol akses dimulai")
        display_lcd("Sistem Siap", "Tempelkan jari")
        
        while True:
            # Pindai sidik jari
            fingerprint_id = scan_fingerprint()
            if fingerprint_id is not None:
                # Terima akses hanya berdasarkan sidik jari
                print("[+] Akses diberikan berdasarkan sidik jari")
                unlock_door()
                time.sleep(3)
            else:
                print("[!] Akses ditolak")
                time.sleep(2)
            
            # Reset LCD
            display_lcd("Sistem Siap", "Tempelkan jari")
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[INFO] Sistem dihentikan oleh pengguna")
    finally:
        if LCD_AVAILABLE and lcd:
            lcd.clear()
        if SELENOID_AVAILABLE and selenoid:
            selenoid.cleanup()
        print("[INFO] Sistem berhenti")
```

### 3. Hapus file embeddings.pkl dan buat yang baru:

Jika error terjadi karena format embeddings yang tidak konsisten, hapus dan buat kembali:

```bash
# Backup file embeddings lama
cp embeddings.pkl embeddings.pkl.backup

# Hapus file embeddings
rm embeddings.pkl

# Buat embeddings kosong baru
python -c "import pickle; pickle.dump({}, open('embeddings.pkl', 'wb'))"
```

Setelah itu, daftarkan wajah baru dengan sidik jari yang ada:

```bash
python fingerprint_utils.py
# Pilih menu 2: Daftar Pengguna dengan Embedding Wajah yang Sudah Ada
``` 