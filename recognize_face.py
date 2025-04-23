import cv2
import numpy as np
import argparse
import time
from mtcnn_utils import detect_face_mtcnn, draw_face_box
from arcface_utils import preprocess_face, extract_embedding, compute_similarity, load_embeddings
from head_pose import calculate_face_orientation, draw_face_orientation, is_face_frontal

# Parsing argumen
parser = argparse.ArgumentParser(description='Pengenalan Wajah dengan MTCNN dan ArcFace')
parser.add_argument('--camera', type=int, default=0, help='Indeks kamera (default: 0)')
parser.add_argument('--embeddings', type=str, default='data/embeddings.pkl', help='Path file embedding')
parser.add_argument('--threshold', type=float, default=0.6, help='Threshold cosine similarity (0-1, default: 0.6)')
parser.add_argument('--show_fps', action='store_true', help='Tampilkan FPS')
parser.add_argument('--show_angles', action='store_true', help='Tampilkan sudut orientasi wajah')
args = parser.parse_args()

def main():
    # Buka kamera
    cap = cv2.VideoCapture(args.camera)
    
    if not cap.isOpened():
        print(f"Gagal membuka kamera {args.camera}")
        return
    
    # Muat database embedding
    embeddings_dict = load_embeddings(args.embeddings)
    if not embeddings_dict:
        print("Database embedding kosong. Jalankan capture_face.py terlebih dahulu.")
        return
    
    print(f"Database berisi {len(embeddings_dict)} orang:")
    for name in embeddings_dict:
        print(f"  - {name}")
    
    print("\nPengenalan Wajah dengan MTCNN dan ArcFace")
    print(f"Threshold similarity: {args.threshold}")
    print("Tekan 'q' untuk keluar")
    print("Tekan 'a' untuk mengaktifkan/menonaktifkan penampilan sudut wajah")
    
    # Variabel untuk mengukur FPS
    prev_frame_time = 0
    
    # Pengaturan jendela
    cv2.namedWindow("Face Recognition", cv2.WINDOW_NORMAL)
    
    # Interval pengenalan untuk mengurangi beban CPU
    recognition_interval = 0.3  # detik
    last_recognition_time = 0
    
    # Status penampilan sudut wajah
    show_angles = args.show_angles  # Status awal berdasarkan argumen
    
    while True:
        # Hitung FPS
        current_frame_time = time.time()
        fps = 1 / (current_frame_time - prev_frame_time) if prev_frame_time > 0 else 0
        prev_frame_time = current_frame_time
        
        # Baca frame dari kamera
        ret, frame = cap.read()
        if not ret:
            print("Gagal membaca frame dari kamera!")
            break
        
        # Deteksi wajah dengan MTCNN
        face_img, bbox = detect_face_mtcnn(frame)
        
        # Jika wajah terdeteksi
        if face_img is not None and bbox is not None:
            # Hitung orientasi wajah
            pitch, yaw, roll = calculate_face_orientation(bbox, frame.shape)
            
            # Tampilkan sudut wajah jika diaktifkan
            if show_angles:
                frame = draw_face_orientation(frame, bbox, pitch, yaw, roll)
                
                # Tambahkan indikator posisi wajah frontal
                is_frontal = is_face_frontal(pitch, yaw, roll)
                frontal_status = "FRONTAL" if is_frontal else "TIDAK FRONTAL"
                frontal_color = (0, 255, 0) if is_frontal else (0, 0, 255)
                cv2.putText(frame, frontal_status, (frame.shape[1] - 150, 30), 
                         cv2.FONT_HERSHEY_SIMPLEX, 0.7, frontal_color, 2)
            else:
                # Gambar kotak wajah (tanpa nama dulu)
                frame = draw_face_box(frame, bbox)
            
            # Lakukan pengenalan setiap beberapa interval
            current_time = time.time()
            if current_time - last_recognition_time >= recognition_interval:
                last_recognition_time = current_time
                
                # Pra-pemrosesan wajah
                face_tensor = preprocess_face(face_img)
                
                if face_tensor is not None:
                    # Ekstrak embedding wajah
                    face_embedding = extract_embedding(face_tensor)
                    
                    # Bandingkan dengan embedding di database
                    best_match_name = None
                    best_match_similarity = 0
                    
                    for name, stored_embedding in embeddings_dict.items():
                        similarity = compute_similarity(face_embedding, stored_embedding)
                        if similarity > best_match_similarity:
                            best_match_similarity = similarity
                            best_match_name = name
                    
                    # Tampilkan hasil jika melewati threshold
                    if best_match_similarity >= args.threshold:
                        # Jika tidak menampilkan sudut wajah, gambar kotak dengan nama
                        if not show_angles:
                            frame = draw_face_box(frame, bbox, best_match_name, best_match_similarity)
                        else:
                            # Jika menampilkan sudut, tambahkan label nama di atas kotak
                            cv2.putText(frame, f"{best_match_name} ({best_match_similarity:.2f})", 
                                     (bbox[0], bbox[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        
                        # Tampilkan status pengenalan
                        status_text = f"Dikenali: {best_match_name} ({best_match_similarity:.2f})"
                        cv2.putText(frame, status_text, (10, frame.shape[0] - 40), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    else:
                        # Tampilkan status tidak dikenali
                        status_text = f"Tidak dikenali (similarity: {best_match_similarity:.2f})"
                        cv2.putText(frame, status_text, (10, frame.shape[0] - 40), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Tampilkan FPS jika diminta
        if args.show_fps:
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Tampilkan threshold
        cv2.putText(frame, f"Threshold: {args.threshold}", (10, frame.shape[0] - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Tampilkan frame
        cv2.imshow("Face Recognition", frame)
        
        # Tangani input keyboard
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('a'):  # Toggle penampilan sudut wajah
            show_angles = not show_angles
            status = "aktif" if show_angles else "nonaktif"
            print(f"Penampilan sudut wajah: {status}")
    
    # Bersihkan
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 