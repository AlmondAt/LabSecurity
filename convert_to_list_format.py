#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pickle
import os
import numpy as np
import argparse
import shutil

def main():
    # Parse argumen
    parser = argparse.ArgumentParser(description='Konversi format embedding ke format list')
    parser.add_argument('--input', type=str, default='embeddings.pkl',
                      help='Path file embedding input (default: embeddings.pkl)')
    parser.add_argument('--output', type=str, default='embeddings_list_format.pkl',
                      help='Path file embedding output (default: embeddings_list_format.pkl)')
    parser.add_argument('--backup', action='store_true',
                      help='Buat backup file original sebelum konversi')
    args = parser.parse_args()
    
    input_path = args.input
    output_path = args.output
    
    if not os.path.exists(input_path):
        print(f"File {input_path} tidak ditemukan.")
        return
    
    # Buat backup jika diminta
    if args.backup:
        backup_path = f"{input_path}.backup"
        print(f"Membuat backup ke: {backup_path}")
        shutil.copy2(input_path, backup_path)
    
    try:
        # Baca data embedding
        with open(input_path, 'rb') as f:
            data = pickle.load(f)
        
        # Cek format data
        all_list = all(isinstance(emb, list) for emb in data.values())
        all_single = all(not isinstance(emb, list) for emb in data.values())
        
        if all_list:
            print("Semua data sudah dalam format list. Tidak perlu konversi.")
            return
        
        if not all_single:
            print("PERINGATAN: Format embedding tidak konsisten (campuran list dan array tunggal)")
            print("Melanjutkan konversi semua data ke format list...")
        
        # Konversi ke format list
        converted_data = {}
        for name, embedding in data.items():
            if isinstance(embedding, list):
                # Sudah dalam format list, simpan apa adanya
                converted_data[name] = embedding
            else:
                # Konversi ke list berisi satu embedding
                converted_data[name] = [embedding]
        
        # Simpan data yang sudah dikonversi
        with open(output_path, 'wb') as f:
            pickle.dump(converted_data, f)
        
        print(f"\n=== HASIL KONVERSI ===")
        print(f"File input: {input_path}")
        print(f"File output: {output_path}")
        print(f"Jumlah orang: {len(converted_data)}")
        
        # Hitung total embedding
        total_embeddings = sum(len(embeddings) for embeddings in converted_data.values())
        print(f"Total embedding: {total_embeddings}")
        
        print("\n=== DETAIL KONVERSI ===")
        for name, embeddings in converted_data.items():
            print(f"Nama: '{name}' - {len(embeddings)} embedding")
        
        print("\nKonversi berhasil!")
        print(f"Untuk menggunakan file baru, jalankan program dengan parameter:")
        print(f"python face_recognition_test_percobaan.py --embeddings {output_path}")
        
    except Exception as e:
        print(f"Error saat konversi file: {e}")

if __name__ == "__main__":
    main() 