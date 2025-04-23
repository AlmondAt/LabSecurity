import cv2
import numpy as np
import argparse
import os
import glob
from mtcnn_utils import detect_face_mtcnn
from arcface_utils import preprocess_face, extract_embedding, save_embeddings, load_embeddings
from head_pose import calculate_face_orientation, is_face_frontal

# Parsing argumen
parser = argparse.ArgumentParser(description='Menambahkan Wajah ke Database dari Foto')
parser.add_argument('--name', type=str, required=True, help='Nama orang yang akan ditambahkan')
parser.add_argument('--photos', type=str, required=True, help='Path ke folder foto atau wildcard (contoh: "foto/*.jpg")')
parser.add_argument('--embeddings', type=str, default='data/embeddings.pkl', help='Path file embedding')
parser.add_argument('--check_frontal', action='store_true', help='Hanya gunakan foto dengan wajah frontal')
parser.add_argument('--overwrite', action='store_true', help='Timpa data jika nama sudah ada')
parser.add_argument('--show_results', action='store_true', help='Tampilkan hasil deteksi')
args = parser.parse_args()

def main():
    # Periksa database embedding yang sudah ada
    embeddings_dict = load_embeddings(args.embeddings)
    
    # Jika nama sudah ada dan tidak ingin ditimpa
    if args.name in embeddings_dict and not args.overwrite:
        print(f"PERINGATAN: Nama '{args.name}' sudah ada dalam database.")
        print(f"Gunakan --overwrite jika ingin menimpa data '{args.name}'.")
        return
    
    # Cari semua foto yang sesuai dengan pattern
    photo_paths = glob.glob(args.photos)
    
    if len(photo_paths) == 0:
        print(f"ERROR: Tidak ditemukan foto yang sesuai dengan pattern '{args.photos}'")
        return
    
    print(f"Ditemukan {len(photo_paths)} foto untuk diproses")
    
    # Untuk menyimpan embedding dari semua foto yang valid
    embeddings = []
    valid_photos = 0
    
    # Proses setiap foto
    for i, photo_path in enumerate(photo_paths, 1):
        print(f"Memproses foto {i}/{len(photo_paths)}: {photo_path}")
        
        # Baca foto
        image = cv2.imread(photo_path)
        
        if image is None:
            print(f"  Gagal membaca foto: {photo_path}")
            continue
        
        # Deteksi wajah
        face_img, bbox = detect_face_mtcnn(image)
        
        if face_img is None or bbox is None:
            print(f"  Tidak ditemukan wajah dalam foto: {photo_path}")
            continue
        
        # Jika opsi check_frontal aktif, cek apakah wajah frontal
        if args.check_frontal:
            pitch, yaw, roll = calculate_face_orientation(bbox, image.shape)
            is_frontal = is_face_frontal(pitch, yaw, roll)
            
            if not is_frontal:
                print(f"  Wajah tidak frontal (pitch={pitch:.1f}, yaw={yaw:.1f}, roll={roll:.1f}), foto dilewati")
                
                # Tampilkan hasil jika diminta
                if args.show_results:
                    result = image.copy()
                    cv2.putText(result, "TIDAK FRONTAL", (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(result, f"Pitch={pitch:.1f}, Yaw={yaw:.1f}, Roll={roll:.1f}", (10, 60), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    
                    # Tampilkan bounding box
                    x, y, w, h = bbox
                    cv2.rectangle(result, (x, y), (x+w, y+h), (0, 0, 255), 2)
                    
                    cv2.imshow(f"Foto {i} - Tidak Frontal", result)
                    cv2.waitKey(1000)  # tampilkan selama 1 detik
                    cv2.destroyWindow(f"Foto {i} - Tidak Frontal")
                
                continue
            else:
                print(f"  Wajah frontal (pitch={pitch:.1f}, yaw={yaw:.1f}, roll={roll:.1f})")
        
        # Praproses wajah untuk ArcFace
        face_tensor = preprocess_face(face_img)
        
        if face_tensor is None:
            print(f"  Gagal memproses wajah dari foto: {photo_path}")
            continue
        
        # Ekstrak embedding
        embedding = extract_embedding(face_tensor)
        embeddings.append(embedding)
        valid_photos += 1
        
        print(f"  Embedding berhasil diekstrak dari foto {photo_path}")
        
        # Tampilkan hasil jika diminta
        if args.show_results:
            result = image.copy()
            
            # Bounding box dan label
            x, y, w, h = bbox
            cv2.rectangle(result, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(result, "VALID", (10, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            if args.check_frontal:
                cv2.putText(result, f"Pitch={pitch:.1f}, Yaw={yaw:.1f}, Roll={roll:.1f}", (10, 60), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imshow(f"Foto {i} - Valid", result)
            cv2.waitKey(1000)  # tampilkan selama 1 detik
            cv2.destroyWindow(f"Foto {i} - Valid")
    
    # Tutup semua jendela
    cv2.destroyAllWindows()
    
    # Jika tidak ada foto valid
    if valid_photos == 0:
        print("ERROR: Tidak ada foto valid untuk diproses.")
        print("Pastikan foto memiliki wajah yang terdeteksi dan memenuhi kriteria yang ditentukan.")
        return
    
    # Hitung rata-rata embedding
    avg_embedding = np.mean(np.array(embeddings), axis=0)
    
    # Simpan ke database
    embeddings_dict[args.name] = avg_embedding
    save_embeddings(embeddings_dict, args.embeddings)
    
    print(f"Berhasil menyimpan rata-rata embedding untuk '{args.name}' dari {valid_photos} foto")
    print(f"Gunakan 'python recognize_face.py' atau 'python recognize_from_photo.py' untuk pengenalan wajah")

if __name__ == "__main__":
    main() 