import pickle
import numpy as np
import os

print("Current working directory:", os.getcwd())

# === 1. Load embeddings.pkl ===
try:
    with open("embeddings.pkl", "rb") as f:
        data = pickle.load(f)
    print("Original file loaded successfully!\n")
except FileNotFoundError:
    print("File 'embeddings.pkl' not found. Pastikan ada di direktori kerja.")
    exit()

# === 2. Tampilkan semua nama dan sebagian embedding ===
print("Preview isi file:")
for name, embedding in data.items():
    print(f"Name: {name}")
    print(f"Embedding (first 5 values): {np.array(embedding)[:5]}")
    print("-" * 50)

# === 3. Konversi ke format baru ===
names = list(data.keys())
embeddings = list(data.values())

converted_data = {
    "names": names,
    "embeddings": embeddings
}

# === 4. Simpan file hasil konversi ===
with open("converted_embeddings.pkl", "wb") as f:
    pickle.dump(converted_data, f)

print(f"\nFile berhasil dikonversi dan disimpan sebagai 'converted_embeddings.pkl'")
