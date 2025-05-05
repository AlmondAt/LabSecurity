#!/usr/bin/env python3
# fix_numpy_error.py - Script untuk memperbaiki error numpy di fingerprint_utils.py

import os
import re
import sys
import shutil

def main():
    """
    Mencari dan memperbaiki error numpy array di fingerprint_utils.py.
    """
    file_path = 'fingerprint_utils.py'
    if not os.path.exists(file_path):
        print(f"[ERROR] File {file_path} tidak ditemukan")
        print("Script ini harus dijalankan di direktori yang sama dengan fingerprint_utils.py")
        return 1
    
    # Buat backup
    backup_path = f"{file_path}.backup"
    print(f"[INFO] Membuat backup file ke {backup_path}")
    shutil.copy2(file_path, backup_path)
    
    # Baca file
    print(f"[INFO] Membaca file {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Baca file baris per baris untuk analisis
    lines = content.splitlines()
    
    # Cari baris 1169 yang disebutkan di error
    target_line_number = 1169
    if len(lines) >= target_line_number:
        target_line = lines[target_line_number - 1]
        print(f"[INFO] Baris {target_line_number}: {target_line}")
        
        # Cek apakah baris tersebut mengandung "user_embeddings"
        if "user_embeddings" in target_line and "if not" in target_line:
            print(f"[INFO] Menemukan baris dengan 'user_embeddings' yang perlu diperbaiki")
            
            # Perbaikan untuk error numpy array
            fixed_lines = lines.copy()
            
            # Ganti baris yang bermasalah dengan kode yang lebih aman
            fixed_lines[target_line_number - 1] = "    # Handle numpy array properly to avoid ValueError"
            fixed_lines.insert(target_line_number, "    if isinstance(user_embeddings, np.ndarray):")
            fixed_lines.insert(target_line_number + 1, "        if user_embeddings.size == 0:")
            fixed_lines.insert(target_line_number + 2, "            print(f\"[!] Data wajah kosong\")")
            fixed_lines.insert(target_line_number + 3, "            display_lcd(\"Data Wajah\", \"Kosong\")")
            fixed_lines.insert(target_line_number + 4, "            cap.release()")
            fixed_lines.insert(target_line_number + 5, "            return False, None")
            fixed_lines.insert(target_line_number + 6, "    elif not user_embeddings:")
            
            # Tulis kembali file
            print(f"[INFO] Menulis perbaikan ke {file_path}")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))
            
            print(f"[SUCCESS] File berhasil diperbaiki")
        else:
            # Cari semua baris dengan "user_embeddings"
            user_embeddings_lines = []
            for i, line in enumerate(lines):
                if "user_embeddings" in line:
                    user_embeddings_lines.append((i+1, line))
            
            if user_embeddings_lines:
                print(f"[INFO] Menemukan {len(user_embeddings_lines)} baris dengan 'user_embeddings':")
                for line_num, line in user_embeddings_lines:
                    print(f"  Baris {line_num}: {line}")
                
                # Perbaiki semua baris dengan 'if not user_embeddings'
                fixed_lines = lines.copy()
                modified = False
                
                for i, (line_num, line) in enumerate(user_embeddings_lines):
                    if "if not user_embeddings" in line:
                        # Ganti baris yang bermasalah dengan kode yang lebih aman
                        fixed_lines[line_num - 1] = "    # Handle numpy array properly to avoid ValueError"
                        fixed_lines.insert(line_num, "    if isinstance(user_embeddings, np.ndarray):")
                        fixed_lines.insert(line_num + 1, "        if user_embeddings.size == 0:")
                        fixed_lines.insert(line_num + 2, "            print(f\"[!] Data wajah kosong\")")
                        fixed_lines.insert(line_num + 3, "            display_lcd(\"Data Wajah\", \"Kosong\")")
                        fixed_lines.insert(line_num + 4, "            cap.release()")
                        fixed_lines.insert(line_num + 5, "            return False, None")
                        fixed_lines.insert(line_num + 6, "    elif not user_embeddings:")
                        modified = True
                        
                        # Setelah modifikasi, perbarui line_num untuk item berikutnya
                        for j in range(i+1, len(user_embeddings_lines)):
                            user_embeddings_lines[j] = (user_embeddings_lines[j][0] + 7, user_embeddings_lines[j][1])
                
                if modified:
                    # Tulis kembali file
                    print(f"[INFO] Menulis perbaikan ke {file_path}")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(fixed_lines))
                    
                    print(f"[SUCCESS] File berhasil diperbaiki")
                else:
                    print(f"[WARNING] Tidak menemukan baris dengan 'if not user_embeddings' untuk diperbaiki")
            else:
                print(f"[WARNING] Tidak menemukan baris dengan 'user_embeddings'")
    else:
        print(f"[ERROR] File tidak memiliki baris {target_line_number}")
    
    print("\n[INFO] Setelah menjalankan script ini, jalankan fingerprint_utils.py")
    print("[INFO] Jika masih error, kembalikan dari backup dengan perintah:")
    print(f"  cp {backup_path} {file_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 