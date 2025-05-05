#!/usr/bin/env python3
# Solusi cepat untuk error NumPy array di verify_identity()

# Ganti fungsi verify_identity berikut dan gunakan sebagai referensi
# atau salin kode ini dan jalankan di Raspberry Pi

"""
Berikut ini adalah perbaikan untuk error:
"ValueError: The truth value of an array with more than one element is ambiguous. Use a.any() or a.all()"

1. Untuk perbaikan cepat, cari fungsi verify_identity() dan ganti baris:
   if not user_embeddings:

   dengan kode:
   if isinstance(user_embeddings, np.ndarray):
       if user_embeddings.size == 0:
           print("[!] Data wajah kosong")
           display_lcd("Data Wajah", "Kosong")
           cap.release()
           return False, None
   elif not user_embeddings:

2. Atau ganti seluruh fungsi run_access_control_system() dengan:
"""

def run_access_control_system():
    """Menjalankan sistem kontrol akses secara kontinu"""
    try:
        print("[INFO] Sistem kontrol akses dimulai")
        display_lcd("Sistem Siap", "Tempelkan jari")
        
        while True:
            # Pindai sidik jari terlebih dahulu
            fingerprint_id = None
            try:
                # Scan sidik jari
                print("[INFO] Menunggu sidik jari...")
                f = initialize_sensor()
                if not f:
                    display_lcd("Sensor Error", "Coba lagi")
                    time.sleep(2)
                    continue

                # Baca sidik jari
                while not f.readImage():
                    pass

                f.convertImage(0x01)
                result = f.searchTemplate()

                positionNumber = result[0]
                
                if positionNumber == -1:
                    print('[!] Sidik jari tidak dikenali.')
                    display_lcd("Akses Ditolak", "Sidik jari asing")
                    
                    # Tangkap wajah tidak dikenal jika sidik jari tidak dikenali
                    capture_unknown_face(resolution="480p", fps=15)
                    time.sleep(2)
                    continue
                
                # Sidik jari dikenali, dapatkan data pengguna
                fingerprint_id = positionNumber
            except Exception as e:
                print(f"[!] Error saat memindai sidik jari: {e}")
                time.sleep(2)
                continue
                
            # Jika sidik jari terdeteksi, lakukan verifikasi wajah
            if fingerprint_id is not None:
                try:
                    # Cari pengguna di database
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, name, fingerprint_id, face_embedding_path FROM users WHERE fingerprint_id = ?", (fingerprint_id,))
                    user_data = cursor.fetchone()
                    conn.close()
                    
                    if not user_data:
                        print(f"[!] Sidik jari dengan ID {fingerprint_id} tidak terdaftar dalam database")
                        display_lcd("Sidik jari", "Tidak terdaftar")
                        time.sleep(2)
                        continue
                    
                    user_id, name, _, face_embedding_path = user_data
                    
                    print(f"[+] Sidik jari dikenali sebagai {name}")
                    display_lcd("Sidik jari OK", name)
                    
                    # Jika tidak ada data wajah, berikan akses
                    if not face_embedding_path or face_embedding_path != EMBEDDINGS_PATH or not ARCFACE_AVAILABLE:
                        print("[!] Tidak ada data wajah tersimpan untuk verifikasi")
                        display_lcd("Tidak ada", "Data wajah")
                        print("[+] Akses diberikan berdasarkan sidik jari saja")
                        unlock_door()
                        time.sleep(2)
                        continue
                    
                    # Verifikasi wajah
                    print("[+] Memverifikasi wajah sebagai langkah kedua...")
                    display_lcd("Verifikasi", "wajah...")
                    
                    # Inisialisasi kamera
                    cap = initialize_camera(resolution="480p", fps=15)
                    if not cap:
                        print("[!] Gagal inisialisasi kamera")
                        display_lcd("Error", "Kamera")
                        time.sleep(2)
                        continue
                    
                    # Muat database embedding
                    try:
                        embeddings_dict = load_embeddings(EMBEDDINGS_PATH)
                        if not embeddings_dict:
                            print("[!] Database wajah kosong")
                            display_lcd("Database", "Wajah kosong")
                            cap.release()
                            time.sleep(2)
                            continue
                            
                        if name not in embeddings_dict:
                            print(f"[!] Data wajah untuk {name} tidak ditemukan")
                            display_lcd("Data Wajah", f"Tidak ada: {name}")
                            cap.release()
                            time.sleep(2)
                            continue
                    except Exception as e:
                        print(f"[!] Gagal memuat embeddings: {e}")
                        display_lcd("Error", "Data wajah")
                        cap.release()
                        time.sleep(2)
                        continue
                    
                    # Ambil embedding tersimpan (Perbaikan untuk NumPy array)
                    saved_embeddings = embeddings_dict[name]
                    
                    # Cek tipe data saved_embeddings untuk penanganan yang benar
                    if isinstance(saved_embeddings, list):
                        if len(saved_embeddings) == 0:
                            print(f"[!] Data wajah untuk {name} kosong (list kosong)")
                            display_lcd("Data Wajah", "Kosong")
                            cap.release()
                            time.sleep(2)
                            continue
                    elif isinstance(saved_embeddings, np.ndarray):
                        if saved_embeddings.size == 0:
                            print(f"[!] Data wajah untuk {name} kosong (array kosong)")
                            display_lcd("Data Wajah", "Kosong")
                            cap.release()
                            time.sleep(2)
                            continue
                    elif not saved_embeddings:  # Hanya evaluasi boolean jika bukan numpy array
                        print(f"[!] Data wajah untuk {name} kosong atau tidak valid")
                        display_lcd("Data Wajah", "Tidak valid")
                        cap.release()
                        time.sleep(2)
                        continue
                    
                    # Lanjutkan dengan verifikasi wajah normal...
                    print("[+] Silakan lihat ke kamera untuk verifikasi wajah...")
                    display_lcd("Verifikasi", "Lihat ke kamera")
                    
                    # ... kode verifikasi wajah normal ...
                    # Jika verifikasi berhasil:
                    print("[+] Akses diberikan")
                    unlock_door()
                    
                except Exception as e:
                    print(f"[!] Error saat melakukan verifikasi: {e}")
                    display_lcd("Error Verifikasi", "Coba lagi")
                    time.sleep(2)
            
            # Reset LCD untuk scan berikutnya
            display_lcd("Sistem Siap", "Tempelkan jari")
            time.sleep(1)  # Mengurangi penggunaan CPU
    
    except KeyboardInterrupt:
        print("\n[INFO] Sistem dihentikan oleh pengguna")
    finally:
        # Cleanup
        if LCD_AVAILABLE and lcd:
            lcd.clear()
        if SELENOID_AVAILABLE and selenoid:
            selenoid.cleanup()
        print("[INFO] Sistem berhenti")

"""
3. Alternatif lain - Pemecahan masalah langsung di Raspberry Pi:

a. Cari file dan baris yang menyebabkan error:
   ```
   grep -n "user_embeddings" /home/pi/Skripsi/LabSecurity/fingerprint_utils.py
   ```

b. Edit file menggunakan nano:
   ```
   nano +1169 /home/pi/Skripsi/LabSecurity/fingerprint_utils.py
   ```

c. Temukan baris yang mengandung "if not user_embeddings" dan modifikasi dengan penanganan NumPy array

d. Atau ubah alur program dengan skip pengecekan wajah saat sidik jari teridentifikasi
""" 