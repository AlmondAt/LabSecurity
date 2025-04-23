import cv2
import numpy as np
import argparse
import os
import time
from mtcnn_utils import detect_face_mtcnn, draw_face_box
from arcface_utils import preprocess_face, extract_embedding, compute_similarity, load_embeddings
from head_pose import calculate_face_orientation, draw_face_orientation, is_face_frontal

# Parsing argumen
parser = argparse.ArgumentParser(description='Pengenalan Wajah dari Foto dengan MTCNN dan ArcFace')
parser.add_argument('--image', type=str, required=True, help='Path ke foto untuk pengenalan')
parser.add_argument('--embeddings', type=str, default='data/embeddings.pkl', help='Path file embedding')
parser.add_argument('--threshold', type=float, default=0.6, help='Threshold cosine similarity (0-1, default: 0.6)')
parser.add_argument('--show_angles', action='store_true', help='Tampilkan sudut orientasi wajah')
parser.add_argument('--output', type=str, help='Path untuk menyimpan hasil (opsional)')
args = parser.parse_args()

def main():
    # Periksa apakah file gambar ada
    if not os.path.exists(args.image):
        print(f"ERROR: File gambar '{args.image}' tidak ditemukan")
        return
    
    # Muat database embedding
    embeddings_dict = load_embeddings(args.embeddings)
    if not embeddings_dict:
        print("Database embedding kosong. Jalankan capture_face.py terlebih dahulu.")
        return
    
    print(f"Database berisi {len(embeddings_dict)} orang")
    
    # Baca gambar
    print(f"Membaca gambar dari: {args.image}")
    image = cv2.imread(args.image)
    
    if image is None:
        print(f"ERROR: Gagal membaca file gambar '{args.image}'")
        return
    
    # Ukuran asli gambar
    height, width = image.shape[:2]
    
    # Deteksi wajah dengan MTCNN
    start_time = time.time()
    face_img, bbox = detect_face_mtcnn(image)
    detection_time = time.time() - start_time
    
    # Hasil gambar untuk output (deep copy dari gambar asli)
    result_image = image.copy()
    
    # Jika tidak ada wajah terdeteksi
    if face_img is None or bbox is None:
        print("Tidak ada wajah terdeteksi dalam gambar")
        cv2.putText(result_image, "Tidak ada wajah terdeteksi", (10, 30), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    else:
        print(f"Wajah terdeteksi dalam {detection_time:.3f} detik")
        
        # Jika diaktifkan, hitung dan tampilkan orientasi wajah
        if args.show_angles:
            # Hitung orientasi wajah
            pitch, yaw, roll = calculate_face_orientation(bbox, image.shape)
            
            # Gambar visualisasi orientasi
            result_image = draw_face_orientation(result_image, bbox, pitch, yaw, roll)
            
            # Tambahkan indikator posisi wajah frontal
            is_frontal = is_face_frontal(pitch, yaw, roll)
            frontal_status = "FRONTAL" if is_frontal else "TIDAK FRONTAL"
            frontal_color = (0, 255, 0) if is_frontal else (0, 0, 255)
            cv2.putText(result_image, frontal_status, (width - 150, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, frontal_color, 2)
            
            print(f"Orientasi wajah - Pitch: {pitch:.1f}, Yaw: {yaw:.1f}, Roll: {roll:.1f}")
            print(f"Status wajah: {frontal_status}")
        else:
            # Gambar kotak wajah tanpa orientasi
            result_image = draw_face_box(result_image, bbox)
        
        # Pra-pemrosesan wajah untuk ArcFace
        start_time = time.time()
        face_tensor = preprocess_face(face_img)
        
        if face_tensor is not None:
            # Ekstrak embedding wajah
            face_embedding = extract_embedding(face_tensor)
            embedding_time = time.time() - start_time
            
            print(f"Embedding diekstrak dalam {embedding_time:.3f} detik")
            
            # Bandingkan dengan embedding di database
            best_match_name = None
            best_match_similarity = 0
            
            start_time = time.time()
            for name, stored_embedding in embeddings_dict.items():
                similarity = compute_similarity(face_embedding, stored_embedding)
                if similarity > best_match_similarity:
                    best_match_similarity = similarity
                    best_match_name = name
            
            matching_time = time.time() - start_time
            print(f"Pencocokan selesai dalam {matching_time:.3f} detik")
            
            # Tampilkan hasil
            if best_match_similarity >= args.threshold:
                result_text = f"Dikenali sebagai: {best_match_name}"
                similarity_text = f"Similarity: {best_match_similarity:.4f}"
                text_color = (0, 255, 0)  # hijau
                
                print(f"Wajah dikenali sebagai: {best_match_name}")
                print(f"Similarity: {best_match_similarity:.4f}")
                
                # Tambahkan label nama pada gambar hasil
                if not args.show_angles:
                    result_image = draw_face_box(result_image, bbox, best_match_name, best_match_similarity)
                else:
                    # Jika menampilkan sudut, tambahkan label nama secara manual
                    cv2.putText(result_image, f"{best_match_name} ({best_match_similarity:.2f})", 
                             (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            else:
                result_text = "Tidak dikenali"
                similarity_text = f"Similarity: {best_match_similarity:.4f}"
                text_color = (0, 0, 255)  # merah
                
                print("Wajah tidak dikenali")
                print(f"Similarity terbaik: {best_match_similarity:.4f} (di bawah threshold {args.threshold})")
            
            # Tambahkan informasi di bagian bawah gambar
            cv2.putText(result_image, result_text, (10, height - 40), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
            cv2.putText(result_image, similarity_text, (10, height - 10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
    
    # Tampilkan gambar hasil
    cv2.imshow("Hasil Pengenalan", result_image)
    print("Tekan sembarang tombol untuk menutup jendela gambar")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Simpan hasil jika diminta
    if args.output:
        cv2.imwrite(args.output, result_image)
        print(f"Hasil pengenalan wajah disimpan ke: {args.output}")

if __name__ == "__main__":
    main() 