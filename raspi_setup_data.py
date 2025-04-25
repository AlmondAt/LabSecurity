import os
import shutil
import pickle
import requests
import argparse
from pathlib import Path

def setup_directories():
    """Membuat direktori yang diperlukan jika belum ada."""
    dirs = ['photos', 'faces', 'unknown_faces', 'data']
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"Direktori {dir_name} berhasil dibuat.")

def download_from_server(server_url, local_path):
    """Download file dari server ke lokal jika tidak ada."""
    if not os.path.exists(local_path):
        try:
            response = requests.get(server_url)
            response.raise_for_status()
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"File {local_path} berhasil didownload.")
            return True
        except Exception as e:
            print(f"Gagal mengunduh {local_path}: {e}")
            return False
    return True

def setup_embeddings(server_url=None, backup_path=None):
    """Setup file embeddings jika tidak ada."""
    embedding_files = ['embeddings.pkl', 'converted_embeddings.pkl']
    
    for emb_file in embedding_files:
        if not os.path.exists(emb_file):
            # Coba download dari server
            if server_url and download_from_server(f"{server_url}/{emb_file}", emb_file):
                continue
                
            # Coba salin dari backup jika ada
            if backup_path and os.path.exists(os.path.join(backup_path, emb_file)):
                shutil.copy(os.path.join(backup_path, emb_file), emb_file)
                print(f"File {emb_file} berhasil disalin dari backup.")
                continue
                
            # Jika tidak ada, buat file kosong
            with open(emb_file, 'wb') as f:
                pickle.dump({}, f)
            print(f"File {emb_file} kosong dibuat.")

def copy_sample_photos(backup_path):
    """Salin foto sampel jika direktori photos kosong."""
    if os.path.exists('photos') and not os.listdir('photos') and backup_path:
        backup_photos = os.path.join(backup_path, 'photos')
        if os.path.exists(backup_photos):
            for item in os.listdir(backup_photos):
                src = os.path.join(backup_photos, item)
                dst = os.path.join('photos', item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            print("Foto sampel berhasil disalin.")

def main():
    parser = argparse.ArgumentParser(description='Setup data untuk Raspberry Pi')
    parser.add_argument('--server', help='URL server untuk mengunduh data')
    parser.add_argument('--backup', help='Path ke backup lokal')
    args = parser.parse_args()
    
    setup_directories()
    setup_embeddings(args.server, args.backup)
    if args.backup:
        copy_sample_photos(args.backup)
    print("Setup data selesai!")

if __name__ == "__main__":
    main() 