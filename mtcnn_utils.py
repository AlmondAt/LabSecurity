import cv2
import numpy as np
from facenet_pytorch import MTCNN
import torch

# Inisialisasi MTCNN detector
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
mtcnn = MTCNN(
    select_largest=True,  # Pilih wajah terbesar dalam frame
    min_face_size=20,     # Ukuran minimal wajah yang terdeteksi
    thresholds=[0.6, 0.7, 0.7],  # Threshold untuk setiap tahap deteksi
    factor=0.709,         # Scale factor
    post_process=True,    # Normalisasi output
    device=device         # GPU/CPU
)

def detect_face_mtcnn(frame):
    """
    Mendeteksi wajah dalam frame menggunakan MTCNN
    
    Args:
        frame (numpy.ndarray): Frame gambar
        
    Returns:
        tuple: (cropped_face, bounding_box)
    """
    # Validasi input frame
    if frame is None or not isinstance(frame, np.ndarray):
        print("[!] Frame tidak valid (None atau bukan numpy array)")
        return None, None
    
    # Cek apakah frame memiliki dimensi yang valid
    if len(frame.shape) < 3 or frame.shape[0] <= 0 or frame.shape[1] <= 0:
        print(f"[!] Dimensi frame tidak valid: {frame.shape}")
        return None, None
    
    try:
        # Konversi ke RGB jika frame dalam BGR (OpenCV)
        if frame.shape[2] == 3:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            rgb_frame = frame
            
        # Deteksi wajah dengan MTCNN
        boxes, probs = mtcnn.detect(rgb_frame)
        
        if boxes is None or len(boxes) == 0:
            return None, None
        
        # Ambil wajah dengan probabilitas tertinggi
        box = boxes[0]
        x1, y1, x2, y2 = [int(coord) for coord in box]
        
        # Validasi bounding box (pastikan koordinat valid)
        height, width = frame.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(width, x2)
        y2 = min(height, y2)
        
        # Cek apakah box valid (lebar dan tinggi > 0)
        if x2 <= x1 or y2 <= y1:
            print("[!] Bounding box tidak valid")
            return None, None
        
        # Crop wajah
        cropped_face = frame[y1:y2, x1:x2]
        
        # Format bounding box [x1, y1, x2, y2]
        bbox = [x1, y1, x2, y2]
        
        return cropped_face, bbox
    
    except Exception as e:
        print(f"[!] Error dalam deteksi wajah MTCNN: {e}")
        return None, None

def draw_face_box(frame, bbox, name=None, similarity=None):
    """
    Menggambar kotak dan informasi pada wajah yang terdeteksi
    
    Args:
        frame (numpy.ndarray): Frame gambar
        bbox (list): Koordinat bounding box [x1, y1, x2, y2]
        name (str, optional): Nama orang yang terdeteksi
        similarity (float, optional): Nilai kesamaan (0-1)
        
    Returns:
        numpy.ndarray: Frame dengan bounding box
    """
    if bbox is None:
        return frame
    
    x1, y1, x2, y2 = bbox
    
    # Gambar kotak wajah
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Tampilkan informasi jika tersedia
    if name is not None:
        info_text = f"{name}"
        if similarity is not None:
            info_text += f" ({similarity:.2f})"
        
        cv2.putText(frame, info_text, (x1, y1 - 10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    
    return frame 