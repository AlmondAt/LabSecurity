# Panduan Setup Data untuk Raspberry Pi

File-file berikut telah dikecualikan dari git karena ukurannya yang besar:
- `embeddings.pkl` dan `converted_embeddings.pkl`
- Folder `photos/`, `faces/`, `unknown_faces/`, dan `data/`

Namun, file-file tersebut tetap diperlukan untuk menjalankan sistem.

## Solusi untuk Menyiapkan Data

### 1. Menggunakan Script Otomatis

Script `raspi_setup_data.py` dibuat untuk memudahkan proses penyiapan data di Raspberry Pi.

```bash
# Jalankan script setup tanpa parameter (akan membuat direktori dan file kosong)
python raspi_setup_data.py

# Jalankan dengan parameter backup jika Anda memiliki salinan data
python raspi_setup_data.py --backup /path/ke/backup

# Jalankan dengan parameter server jika data tersedia di server
python raspi_setup_data.py --server http://alamat-server/data
```

### 2. Backup Data Secara Manual

Sebelum push ke git:
1. Salin folder `photos/`, `faces/`, `unknown_faces/`, dan `data/` ke lokasi backup
2. Salin file `embeddings.pkl` dan `converted_embeddings.pkl` ke lokasi backup

Saat mengimpor ke Raspberry Pi:
1. Clone repositori git seperti biasa
2. Salin kembali folder dan file dari backup ke proyek

### 3. Menggunakan Cloud Storage

Jika Anda memiliki akses ke cloud storage (seperti Google Drive, Dropbox, dll):
1. Unggah data ke cloud storage
2. Saat setup di Raspberry Pi, gunakan script untuk mengunduh dari cloud

## Memasukkan raspi_setup_data.py ke Installation Script

Tambahkan langkah berikut ke script `raspi_install.sh` Anda:

```bash
# Setup data yang dibutuhkan
python raspi_setup_data.py --backup /path/ke/backup
```

Dengan cara ini, data penting Anda akan tetap ada saat diimpor ke Raspberry Pi meskipun file tersebut dikecualikan dari git. 