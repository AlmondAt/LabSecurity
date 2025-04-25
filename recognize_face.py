import cv2
import numpy as np
import argparse
import time
from mtcnn_utils import detect_face_mtcnn, draw_face_box
from arcface_utils import preprocess_face, extract_embedding, compute_similarity, load_embeddings
from head_pose import calculate_face_orientation, draw_face_orientation, is_face_frontal

# Parsing argumen
parser = argparse.ArgumentParser(description='Pengenalan Wajah dengan MTCNN dan ArcFace')
parser.add_argument('--camera', type=str, default='/dev/video1', help='Perangkat kamera (default: /dev/video1)')
parser.add_argument('--camera_alt', type=str, default='/dev/video2', help='Perangkat kamera alternatif (default: /dev/video2)')
parser.add_argument('--camera_idx', type=int, default=0, help='Indeks kamera fallback (default: 0)')
parser.add_argument('--embeddings', type=str, default='data/embeddings.pkl', help='Path file embedding')
parser.add_argument('--threshold', type=float, default=0.6, help='Threshold cosine similarity (0-1, default: 0.6)')
parser.add_argument('--show_fps', action='store_true', help='Tampilkan FPS')
parser.add_argument('--show_angles', action='store_true', help='Tampilkan sudut orientasi wajah')
args = parser.parse_args()

def initialize_camera():
    """Inisialisasi kamera untuk pengenalan wajah dengan mencoba beberapa perangkat"""
    devices_to_try = [args.camera, args.camera_alt, args.camera_idx]
    
    for device in devices_to_try:
        try:
            print(f"Mencoba membuka kamera: {device}")
            cap = cv2.VideoCapture(device)
            if cap.isOpened():
                print(f"Berhasil membuka kamera: {device}")
                return cap
            else:
                print(f"Gagal membuka kamera: {device}")
                cap.release()
        except Exception as e:
            print(f"Error saat membuka kamera {device}: {e}")
    
    print("GAGAL: Tidak dapat membuka kamera manapun")
    return None

def main():
    # Muat embedding dari file
    embeddings_dict = load_embeddings(args.embeddings)
    
    if not embeddings_dict:
        print("Error: File embedding tidak ditemukan atau kosong.")
        return
    
    print(f"Memuat {len(embeddings_dict)} embedding dari {args.embeddings}")
    
    # Inisialisasi kamera
    cap = initialize_camera()
    if not cap:
        print("Tidak dapat membuka kamera. Program dihentikan.")
        return
    
    # Setup tampilan jendela
    cv2.namedWindow('Pengenalan Wajah', cv2.WINDOW_NORMAL)
    
    # FPS counter
    fps_counter = 0
    fps_start_time = time.time()
    fps = 0
    
    print("Program pengenalan wajah berjalan...")
    print("Tekan 'q' untuk keluar.")
    
    while True:
        # Baca frame dari kamera
        ret, frame = cap.read()
        if not ret:
            print("Gagal membaca frame dari kamera!")
            break
        
        # Update FPS counter
        fps_counter += 1
        if time.time() - fps_start_time >= 1:
            fps = fps_counter
            fps_counter = 0
            fps_start_time = time.time()
        
        # Deteksi wajah dengan MTCNN
        face_img, bbox = detect_face_mtcnn(frame)
        
        if bbox is not None:
            # Hitung orientasi wajah
            pitch, yaw, roll = calculate_face_orientation(bbox, frame.shape)
            
            # Gambar kotak wajah dan orientasi
            if args.show_angles:
                frame = draw_face_orientation(frame, bbox, pitch, yaw, roll)
            else:
                frame = draw_face_box(frame, bbox)
            
            # Cek apakah wajah frontal
            frontal = is_face_frontal(pitch, yaw, roll)
            
            # Tampilkan status frontal
            frontal_text = "FRONTAL" if frontal else "TIDAK FRONTAL"
            frontal_color = (0, 255, 0) if frontal else (0, 0, 255)
            cv2.putText(frame, frontal_text, (frame.shape[1] - 150, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, frontal_color, 2)
            
            # Jika wajah frontal, lakukan pengenalan
            if frontal:
                # Pra-pemrosesan wajah
                face_tensor = preprocess_face(face_img)
                
                if face_tensor is not None:
                    # Ekstrak embedding
                    embedding = extract_embedding(face_tensor)
                    
                    # Cari kecocokan terbaik
                    best_match_name = None
                    best_match_score = 0
                    
                    for name, embeddings_list in embeddings_dict.items():
                        for ref_embedding in embeddings_list:
                            similarity = compute_similarity(embedding, ref_embedding)
                            
                            if similarity > best_match_score:
                                best_match_score = similarity
                                best_match_name = name
                    
                    # Tampilkan hasil
                    if best_match_score >= args.threshold:
                        result_text = f"{best_match_name}: {best_match_score:.4f}"
                        result_color = (0, 255, 0)  # Hijau untuk kecocokan
                    else:
                        result_text = f"Unknown: {best_match_score:.4f}"
                        result_color = (0, 0, 255)  # Merah untuk tidak dikenal
                    
                    cv2.putText(frame, result_text, (10, 30), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.7, result_color, 2)
        
        # Tampilkan FPS jika diaktifkan
        if args.show_fps:
            cv2.putText(frame, f"FPS: {fps}", (10, frame.shape[0] - 10), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        # Tampilkan frame
        cv2.imshow('Pengenalan Wajah', frame)
        
        # Tunggu tombol 'q' untuk keluar
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Bersihkan
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main() 