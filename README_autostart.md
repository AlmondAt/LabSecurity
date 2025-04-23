# Panduan Autostart Sistem Biometrik di Raspberry Pi

Dokumen ini menjelaskan cara mengatur sistem biometrik agar otomatis berjalan saat Raspberry Pi boot.

## Cara Instalasi

### 1. Pastikan script autostart memiliki izin eksekusi:

```bash
sudo chmod +x /home/pi/ArcFace/biometric_autostart.sh
```

### 2. Salin file service ke folder systemd:

```bash
sudo cp /home/pi/ArcFace/biometric_service.service /etc/systemd/system/
```

### 3. Aktifkan service:

```bash
sudo systemctl enable biometric_service.service
```

### 4. Mulai service:

```bash
sudo systemctl start biometric_service.service
```

### 5. Cek status service:

```bash
sudo systemctl status biometric_service.service
```

## Pengaturan Tambahan

### Melihat log:

```bash
sudo journalctl -u biometric_service.service
```

### Menghentikan service:

```bash
sudo systemctl stop biometric_service.service
```

### Restart service:

```bash
sudo systemctl restart biometric_service.service
```

### Menonaktifkan autostart:

```bash
sudo systemctl disable biometric_service.service
```

## Pemecahan Masalah

Jika sistem tidak berjalan dengan baik, periksa:

1. Path di file biometric_autostart.sh sesuai dengan lokasi folder ArcFace Anda
2. User di biometric_service.service sesuai dengan pengguna Raspberry Pi Anda (default: pi)
3. Periksa log untuk error: `sudo journalctl -u biometric_service.service -e`

## Catatan

- Sistem akan otomatis restart jika berhenti karena error
- Jika Anda mengedit file service, jalankan `sudo systemctl daemon-reload` sebelum me-restart service 