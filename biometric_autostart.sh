#!/bin/bash

# Menunggu sistem selesai boot (opsional, tapi memastikan semua layanan sudah siap)
sleep 30

# Pindah ke direktori proyek
cd /home/pi/ArcFace

# Aktifkan virtual environment (jika menggunakan)
# source venv/bin/activate

# Jalankan program dengan opsi 8 (Jalankan Sistem Kontrol Akses)
echo "8" | python fingerprint_utils.py

# Jika program keluar, restart (opsional)
# Hapus tanda # di bawah jika ingin program restart otomatis jika berhenti
# exec $0 