# Tombol Emergency untuk Selenoid

Sistem ini memungkinkan membuka selenoid secara darurat menggunakan tombol fisik yang terhubung ke Raspberry Pi. Berguna sebagai backup jika sistem kontrol akses utama tidak berfungsi.

## Persyaratan Hardware

- Raspberry Pi (model apapun dengan pin GPIO)
- 1x Push button (tombol emergency)
- 1x LED indikator (opsional)
- 1x Selenoid door lock (12V)
- 1x Relay module untuk mengontrol selenoid
- Resistor pull-up 10k ohm (opsional, karena kita menggunakan internal pull-up)
- Kabel jumper

## Wiring

### Tombol
- Satu pin tombol -> GPIO 17 (PIN_BUTTON)
- Pin lainnya -> GND

### Selenoid (via relay)
- Input relay -> GPIO 18 (PIN_SELENOID)
- VCC relay -> 5V Raspberry Pi
- GND relay -> GND Raspberry Pi
- Selenoid terhubung ke power supply 12V dan relay (COM & NO)

### LED Indikator (opsional)
- Positif LED (via resistor 220 ohm) -> GPIO 27 (PIN_LED)
- Negatif LED -> GND

## Versi Tersedia

Ada beberapa versi program yang tersedia:

1. **emergency_button.py**: Versi lengkap dengan LED indikator, event-based
2. **simple_emergency_button.py**: Versi sederhana tanpa LED dan hanya polling
3. **emergency_service.py**: Versi untuk dijalankan sebagai layanan sistemd dengan logging

## Instalasi

1. Salin semua file ke Raspberry Pi Anda, misalnya ke folder `/home/pi/ArcFace/`

2. Pastikan file-file dapat dieksekusi:
   ```
   chmod +x emergency_button.py simple_emergency_button.py emergency_service.py
   ```

3. Tes program dengan menjalankan versi sederhana:
   ```
   sudo python3 simple_emergency_button.py
   ```
   Tekan tombol emergency untuk membuka selenoid selama beberapa detik.

4. Untuk menginstal sebagai layanan sistemd (auto-start saat boot):
   ```
   sudo cp emergency-button.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable emergency-button.service
   sudo systemctl start emergency-button.service
   ```

5. Cek status layanan:
   ```
   sudo systemctl status emergency-button.service
   ```

## Penggunaan

- Tekan tombol emergency untuk segera membuka selenoid.
- Selenoid akan terbuka selama durasi yang ditentukan (default: 5 detik).
- Setelah itu, selenoid akan mengunci kembali secara otomatis.

## Kustomisasi

Anda dapat menyesuaikan pengaturan dengan mengedit file program:

- **PIN_BUTTON**: GPIO pin untuk tombol emergency (default: 17)
- **PIN_SELENOID**: GPIO pin untuk selenoid (default: 18)
- **PIN_LED**: GPIO pin untuk LED indikator (default: 27)
- **UNLOCK_DURATION**: Durasi membuka selenoid dalam detik (default: 5)

## Troubleshooting

- **Selenoid tidak terbuka**: Periksa wiring dan pastikan relay menerima sinyal dari Raspberry Pi.
- **Program error**: Periksa log dengan `sudo journalctl -u emergency-button.service` jika menggunakan mode layanan.
- **Tombol tidak responsif**: Periksa koneksi tombol dan pastikan pull-up resistor terpasang (internal atau eksternal).

## Peringatan

Sistem ini sebaiknya hanya digunakan sebagai backup dan bukan sebagai mekanisme keamanan utama. Selalu pastikan ada cara lain untuk mendapatkan akses jika terjadi kegagalan daya atau masalah hardware. 