import cv2
import numpy as np
import argparse
import os
import time
from mtcnn_utils import detect_face_mtcnn, draw_face_box
from arcface_utils import preprocess_face, extract_embedding, save_embeddings, load_embeddings
from head_pose import calculate_face_orientation, draw_face_orientation, is_face_frontal

# Parsing argumen
parser = argparse.ArgumentParser(description='Pengambilan Foto dan Ekstraksi Embedding')
parser.add_argument('--name', type=str, default='fariz', help='Nama orang (default: fariz)')
parser.add_argument('--camera', type=str, default='/dev/video1', help='Perangkat kamera (default: /dev/video1)')
parser.add_argument('--camera_alt', type=str, default='/dev/video2', help='Perangkat kamera alternatif (default: /dev/video2)')
parser.add_argument('--camera_idx', type=int, default=0, help='Indeks kamera fallback (default: 0)')
parser.add_argument('--embeddings', type=str, default='data/embeddings.pkl', help='Path file embedding')
parser.add_argument('--show_list', action='store_true', help='Tampilkan daftar orang dalam database')
parser.add_argument('--show_angles', action='store_true', help='Tampilkan sudut orientasi wajah')
args = parser.parse_args()

def show_database_entries(embeddings_path):
    """Menampilkan daftar orang dalam database"""
    embeddings_dict = load_embeddings(embeddings_path)
    
    if not embeddings_dict:
        print("Database kosong.")
        return
    
    print(f"\n=== ORANG DALAM DATABASE ===")
    print(f"Total: {len(embeddings_dict)} orang")
    for i, name in enumerate(embeddings_dict.keys(), 1):
        print(f"{i}. {name}")
    print("="*25)

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
    # Jika user hanya ingin melihat daftar
    if args.show_list:
        show_database_entries(args.embeddings)
        return
    
    # Periksa apakah nama sudah ada dalam database
    embeddings_dict = load_embeddings(args.embeddings)
    if args.name in embeddings_dict:
        print(f"PERINGATAN: Nama '{args.name}' sudah ada dalam database.")
        response = input(f"Apakah anda ingin menimpa data '{args.name}'? (y/n): ")
        if response.lower() != 'y':
            print("Pembatalan pengambilan foto.")
            return
        print(f"Data untuk '{args.name}' akan ditimpa.")
    
    # Tampilkan daftar nama yang sudah ada
    show_database_entries(args.embeddings)
    
    # Buka kamera
    cap = initialize_camera()
    
    if not cap:
        print("Pembatalan pengambilan foto karena kamera tidak tersedia.")
        return
    
    # Buat direktori untuk menyimpan foto
    photo_dir = 'photos'
    os.makedirs(photo_dir, exist_ok=True)
    
    print(f"Pengambilan foto untuk: {args.name}")
    print("Ambil 5 foto dengan pose berbeda:")
    print("1. Wajah frontal")
    print("2. Wajah miring ke kiri")
    print("3. Wajah miring ke kanan")
    print("4. Ekspresi tersenyum")
    print("5. Ekspresi lain (bebas)")
    print("\nTekan SPASI untuk mengambil foto (5 foto diperlukan)")
    print("Tekan 'a' untuk mengaktifkan/menonaktifkan penampilan sudut wajah")
    print("Tekan ESC untuk keluar")
    
    embeddings = []
    photos_captured = 0
    required_photos = 5
    instruction_text = "Wajah frontal"
    show_angles = args.show_angles  # Status awal berdasarkan argumen
    
    while photos_captured < required_photos:
        ret, frame = cap.read()
        if not ret:
            print("Gagal membaca frame dari kamera!")
            break
        
        # Deteksi wajah dengan MTCNN
        face_img, bbox = detect_face_mtcnn(frame)
        
        # Tampilkan frame dengan kotak wajah dan orientasi wajah jika diaktifkan
        if bbox is not None:
            # Hitung orientasi wajah
            pitch, yaw, roll = calculate_face_orientation(bbox, frame.shape)
            
            # Tampilkan kotak wajah dan sudut jika diaktifkan
            if show_angles:
                frame = draw_face_orientation(frame, bbox, pitch, yaw, roll)
            else:
                frame = draw_face_box(frame, bbox)
            
            # Tambahkan indikator posisi wajah frontal
            is_frontal = is_face_frontal(pitch, yaw, roll)
            frontal_status = "FRONTAL" if is_frontal else "TIDAK FRONTAL"
            frontal_color = (0, 255, 0) if is_frontal else (0, 0, 255)
            cv2.putText(frame, frontal_status, (frame.shape[1] - 150, 30), 
                      cv2.FONT_HERSHEY_SIMPLEX, 0.7, frontal_color, 2)
        
        # Tampilkan instruksi dan jumlah foto
        cv2.putText(frame, f"Foto {photos_captured+1}/5: {instruction_text}", 
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Orang: {args.name}", 
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, "Tekan SPASI untuk mengambil foto", 
                    (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Tampilkan frame
        cv2.imshow("Pengambilan Foto", frame)
        
        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break
        elif key == 97:  # 'a' untuk toggle sudut
            show_angles = not show_angles
            status = "aktif" if show_angles else "nonaktif"
            print(f"Penampilan sudut wajah: {status}")
        elif key == 32 and bbox is not None:  # SPASI
            # Pra-pemrosesan wajah
            face_tensor = preprocess_face(face_img)
            
            if face_tensor is not None:
                # Simpan foto
                photo_path = os.path.join(photo_dir, f"{args.name}_{photos_captured+1}.jpg")
                cv2.imwrite(photo_path, face_img)
                
                # Ekstrak embedding
                embedding = extract_embedding(face_tensor)
                embeddings.append(embedding)
                
                photos_captured += 1
                print(f"Foto {photos_captured}/5 diambil dan disimpan ke {photo_path}")
                
                # Update instruksi untuk foto berikutnya
                if photos_captured == 1:
                    instruction_text = "Wajah miring ke kiri"
                elif photos_captured == 2:
                    instruction_text = "Wajah miring ke kanan"
                elif photos_captured == 3:
                    instruction_text = "Ekspresi tersenyum"
                elif photos_captured == 4:
                    instruction_text = "Ekspresi lain (bebas)"
                
                # Berikan jeda untuk perubahan pose
                time.sleep(1)
    
    cap.release()
    cv2.destroyAllWindows()
    
    if photos_captured > 0:
        # Hitung rata-rata embedding
        avg_embedding = np.mean(np.array(embeddings), axis=0)
        
        # Muat embedding yang sudah ada (jika ada)
        embeddings_dict = load_embeddings(args.embeddings)
        
        # Simpan embedding baru
        embeddings_dict[args.name] = avg_embedding
        save_embeddings(embeddings_dict, args.embeddings)
        
        print(f"Berhasil menyimpan rata-rata embedding untuk {args.name} dari {photos_captured} foto")
        print(f"Gunakan 'python recognize_face.py' untuk melakukan pengenalan wajah")
    else:
        print("Tidak ada foto yang diambil.")

if __name__ == "__main__":
    main() 