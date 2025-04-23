import argparse
import os
import numpy as np
from arcface_utils import load_embeddings, save_embeddings

# Parsing argumen
parser = argparse.ArgumentParser(description='Mengelola Database Wajah')
parser.add_argument('--action', type=str, required=True, choices=['list', 'delete', 'info'],
                    help='Aksi: list (tampilkan semua), delete (hapus), info (detail)')
parser.add_argument('--name', type=str, help='Nama orang (untuk delete)')
parser.add_argument('--embeddings', type=str, default='data/embeddings.pkl', help='Path file embedding')
args = parser.parse_args()

def list_faces(embeddings_dict):
    """Menampilkan semua wajah dalam database"""
    if not embeddings_dict:
        print("Database kosong. Gunakan 'capture_face.py' untuk menambahkan wajah.")
        return
    
    print(f"\n=== DATABASE WAJAH ===")
    print(f"Total: {len(embeddings_dict)} orang")
    print("="*20)
    
    for i, name in enumerate(embeddings_dict.keys(), 1):
        if isinstance(embeddings_dict[name], list):
            samples = len(embeddings_dict[name])
        else:
            samples = 1
        print(f"{i}. {name} ({samples} sampel)")
    
    print("="*20)
    print("Gunakan 'python manage_faces.py --action info' untuk melihat detail")

def delete_face(embeddings_dict, name):
    """Menghapus wajah dari database"""
    if not embeddings_dict:
        print("Database kosong.")
        return
    
    if name in embeddings_dict:
        # Hapus dari dictionary
        embeddings_dict.pop(name)
        # Simpan perubahan
        save_embeddings(embeddings_dict, args.embeddings)
        print(f"Berhasil menghapus '{name}' dari database.")
    else:
        print(f"Nama '{name}' tidak ditemukan dalam database.")
        available_names = list(embeddings_dict.keys())
        if available_names:
            print(f"Nama yang tersedia: {', '.join(available_names)}")

def show_info(embeddings_dict):
    """Menampilkan informasi detail tentang database"""
    if not embeddings_dict:
        print("Database kosong. Gunakan 'capture_face.py' untuk menambahkan wajah.")
        return
    
    total_samples = 0
    
    print(f"\n=== DETAIL DATABASE WAJAH ===")
    for name, embedding in embeddings_dict.items():
        if isinstance(embedding, list):
            n_samples = len(embedding)
            embedding_size = len(embedding[0])
        else:
            n_samples = 1
            embedding_size = len(embedding)
        
        total_samples += n_samples
        print(f"- {name}: {n_samples} sampel, dimensi embedding: {embedding_size}")
    
    print(f"\nTotal orang: {len(embeddings_dict)}")
    print(f"Total sampel: {total_samples}")
    print(f"Path database: {args.embeddings}")
    print("\nGunakan perintah berikut untuk menambah sampel:")
    print("  python capture_face.py --name NAMA_ORANG --camera 1")
    print("\nGunakan perintah berikut untuk menghapus sampel:")
    print("  python manage_faces.py --action delete --name NAMA_ORANG")

def main():
    # Muat database embedding
    embeddings_dict = load_embeddings(args.embeddings)
    
    # Eksekusi aksi yang diminta
    if args.action == 'list':
        list_faces(embeddings_dict)
    elif args.action == 'delete':
        if args.name:
            delete_face(embeddings_dict, args.name)
        else:
            print("ERROR: Parameter --name diperlukan untuk aksi delete.")
            print("Gunakan: python manage_faces.py --action delete --name NAMA_ORANG")
    elif args.action == 'info':
        show_info(embeddings_dict)

if __name__ == "__main__":
    main() 