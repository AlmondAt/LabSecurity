import cv2
import numpy as np
import math

def calculate_face_orientation(bbox, frame_shape):
    """
    Menghitung orientasi wajah (pitch, yaw, roll) berdasarkan bounding box.
    
    Args:
        bbox: Bounding box wajah dalam format [x, y, w, h] atau [x1, y1, x2, y2]
        frame_shape: Ukuran frame (height, width)
    
    Returns:
        tuple: (pitch, yaw, roll) dalam derajat
    """
    try:
        # Validasi input
        if bbox is None or not isinstance(bbox, (list, tuple, np.ndarray)) or len(bbox) < 4:
            print("[!] Bounding box tidak valid")
            return 0, 0, 0
            
        if not isinstance(frame_shape, (list, tuple, np.ndarray)) or len(frame_shape) < 2:
            print("[!] Frame shape tidak valid")
            return 0, 0, 0
            
        # Konversi dari format [x1, y1, x2, y2] ke [x, y, w, h] jika perlu
        if len(bbox) == 4:
            x1, y1, x2, y2 = bbox
            x, y = x1, y1
            w, h = x2 - x1, y2 - y1
        else:
            x, y, w, h = bbox
            
        # Validasi width dan height
        if w <= 0 or h <= 0:
            print("[!] Width atau height tidak valid")
            return 0, 0, 0
            
        # Menghitung titik tengah wajah
        face_center_x = x + w/2
        face_center_y = y + h/2
        
        # Validasi frame shape
        frame_width = frame_shape[1] if len(frame_shape) >= 2 else 1
        frame_height = frame_shape[0] if len(frame_shape) >= 1 else 1
        
        if frame_width <= 0 or frame_height <= 0:
            print("[!] Dimensi frame tidak valid")
            return 0, 0, 0
        
        # Menghitung titik tengah frame
        frame_center_x = frame_width / 2
        frame_center_y = frame_height / 2
        
        # Menghitung pergeseran dari tengah (dengan pencegahan division by zero)
        x_displacement = (face_center_x - frame_center_x) / frame_center_x if frame_center_x > 0 else 0
        y_displacement = (face_center_y - frame_center_y) / frame_center_y if frame_center_y > 0 else 0
        
        # Rasio aspek wajah (dapat digunakan untuk estimasi roll)
        aspect_ratio = w / h if h > 0 else 1
        
        # Estimasi sudut berdasarkan pergeseran
        # Ini adalah estimasi sederhana, untuk estimasi yang lebih akurat 
        # diperlukan model 3D atau landmark wajah
        yaw = x_displacement * 45  # mengubah ke sudut (-45 hingga 45 derajat)
        pitch = y_displacement * 30  # mengubah ke sudut (-30 hingga 30 derajat)
        
        # Estimasi roll berdasarkan rasio aspek wajah
        # Asumsi: rasio aspek normal sekitar 0.75-0.85
        normal_ratio = 0.8
        roll_factor = (aspect_ratio - normal_ratio) * 45
        roll = max(min(roll_factor, 30), -30)  # membatasi ke rentang -30 hingga 30
        
        return pitch, yaw, roll
        
    except Exception as e:
        print(f"[!] Error dalam calculate_face_orientation: {e}")
        return 0, 0, 0

def draw_face_orientation(frame, bbox, pitch, yaw, roll, color=(0, 255, 0), thickness=2):
    """
    Menggambar visualisasi orientasi wajah pada frame.
    
    Args:
        frame: Frame video
        bbox: Bounding box wajah dalam format [x, y, w, h]
        pitch: Sudut pitch dalam derajat
        yaw: Sudut yaw dalam derajat
        roll: Sudut roll dalam derajat
        color: Warna garis (B, G, R)
        thickness: Ketebalan garis
    
    Returns:
        frame: Frame yang telah dimodifikasi
    """
    x, y, w, h = bbox
    
    # Menggambar bounding box
    cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
    
    # Titik tengah wajah
    face_center_x = int(x + w/2)
    face_center_y = int(y + h/2)
    
    # Panjang garis indikator
    line_length = int(w / 2)
    
    # Menghitung titik akhir garis berdasarkan sudut
    # Yaw (sumbu Y)
    yaw_end_x = face_center_x + int(line_length * math.sin(math.radians(yaw)))
    yaw_end_y = face_center_y
    
    # Pitch (sumbu X)
    pitch_end_x = face_center_x
    pitch_end_y = face_center_y - int(line_length * math.sin(math.radians(pitch)))
    
    # Menggambar garis orientasi
    cv2.line(frame, (face_center_x, face_center_y), (yaw_end_x, yaw_end_y), (0, 0, 255), thickness)
    cv2.line(frame, (face_center_x, face_center_y), (pitch_end_x, pitch_end_y), (255, 0, 0), thickness)
    
    # Menampilkan sudut dalam teks
    cv2.putText(frame, f"Pitch: {pitch:.1f}", (x, y-60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    cv2.putText(frame, f"Yaw: {yaw:.1f}", (x, y-40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    cv2.putText(frame, f"Roll: {roll:.1f}", (x, y-20), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    return frame

def get_orientation_category(pitch, yaw, roll):
    """
    Mengkategorikan orientasi wajah berdasarkan sudut.
    
    Args:
        pitch: Sudut pitch dalam derajat
        yaw: Sudut yaw dalam derajat
        roll: Sudut roll dalam derajat
    
    Returns:
        dict: Kategori orientasi wajah
    """
    categories = {
        'pitch': 'normal',
        'yaw': 'normal',
        'roll': 'normal',
        'overall': 'normal'
    }
    
    # Kategorikan pitch (mengangguk)
    if pitch < -15:
        categories['pitch'] = 'mendongak'
    elif pitch > 15:
        categories['pitch'] = 'menunduk'
    
    # Kategorikan yaw (menoleh ke samping)
    if yaw < -15:
        categories['yaw'] = 'kiri'
    elif yaw > 15:
        categories['yaw'] = 'kanan'
    
    # Kategorikan roll (memiringkan kepala)
    if roll < -15:
        categories['roll'] = 'miring kiri'
    elif roll > 15:
        categories['roll'] = 'miring kanan'
    
    # Kategorikan overall
    if categories['pitch'] != 'normal' or categories['yaw'] != 'normal' or categories['roll'] != 'normal':
        categories['overall'] = 'tidak frontal'
    
    return categories

def is_face_frontal(pitch, yaw, roll, threshold=10):
    """
    Memeriksa apakah wajah dalam posisi frontal.
    
    Args:
        pitch: Sudut pitch dalam derajat
        yaw: Sudut yaw dalam derajat
        roll: Sudut roll dalam derajat
        threshold: Ambang batas sudut untuk dianggap frontal
    
    Returns:
        bool: True jika wajah dalam posisi frontal
    """
    return (abs(pitch) <= threshold and 
            abs(yaw) <= threshold and 
            abs(roll) <= threshold) 