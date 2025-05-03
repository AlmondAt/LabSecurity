#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import os
import numpy as np
import argparse

def main():
    # Parse argumen
    parser = argparse.ArgumentParser(description='Periksa format file embedding')
    parser.add_argument('--embeddings', type=str, default='embeddings.pkl',
                      help='Path file embedding (default: embeddings.pkl)')
    args = parser.parse_args()
    
    file_path = args.embeddings
    
    if not os.path.exists(file_path):
        print(f"File {file_path} tidak ditemukan.")
        return
    
    try:
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        if not data:
            print(f"File {file_path} kosong atau tidak berisi data embeddings.")
            return
        
        print(f"\n=== DETAIL FILE EMBEDDINGS ===")
        print(f"Path file: {os.path.abspath(file_path)}")
        print(f"Ukuran file: {os.path.getsize(file_path) / 1024:.2f} KB")
        print(f"Tipe data: {type(data)}")
        print(f"Jumlah orang: {len(data)}")
        
        # Hitung total embedding
        total_embeddings = 0
        for name, embeddings in data.items():
            if isinstance(embeddings, list):
                total_embeddings += len(embeddings)
            else:
                total_embeddings += 1
        
        print(f"Total embedding: {total_embeddings}")
        print("\n=== DAFTAR ORANG ===")
        
        for i, (name, embeddings) in enumerate(data.items(), 1):
            if isinstance(embeddings, list):
                embedding_count = len(embeddings)
                print(f"{i}. Nama: '{name}' - {embedding_count} embedding")
            else:
                print(f"{i}. Nama: '{name}' - 1 embedding (format tunggal)")
        
        print("\n=== DETAIL STRUKTUR ===")
        for name, embeddings in data.items():
            print(f"Nama: '{name}'")
            
            if isinstance(embeddings, list):
                print(f"  Format: List dari {len(embeddings)} embedding")
                for i, emb in enumerate(embeddings, 1):
                    print(f"  Embedding {i}: shape={emb.shape}, type={type(emb)}")
                    print(f"    Nilai min: {np.min(emb):.4f}, max: {np.max(emb):.4f}, mean: {np.mean(emb):.4f}")
            else:
                print(f"  Format: Embedding tunggal")
                print(f"  Shape: {embeddings.shape}, type: {type(embeddings)}")
                print(f"  Nilai min: {np.min(embeddings):.4f}, max: {np.max(embeddings):.4f}, mean: {np.mean(embeddings):.4f}")
            
            print("---")
        
        print("\n=== REKOMENDASI ===")
        if any(isinstance(emb, list) for emb in data.values()) and \
           any(not isinstance(emb, list) for emb in data.values()):
            print("PERINGATAN: Format embedding tidak konsisten (campuran list dan array tunggal)")
            print("Sebaiknya konversi semua embedding ke format yang sama.")
        elif all(isinstance(emb, list) for emb in data.values()):
            print("Format embedding: List (multiple embeddings per orang)")
            print("Ini adalah format yang diharapkan oleh capture_face.py")
        else:
            print("Format embedding: Array tunggal (satu embedding per orang)")
            print("Saat menggunakan format ini, threshold mungkin perlu disesuaikan.")
            print("Untuk hasil terbaik, pertimbangkan untuk menggunakan multiple embeddings per orang.")
        
    except Exception as e:
        print(f"Error saat membuka file: {e}")

if __name__ == "__main__":
    main() 