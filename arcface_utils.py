import cv2
import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1
import pickle
import os

# Inisialisasi model ArcFace (InceptionResnetV1 dengan pretrained weights 'vggface2')
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
arcface_model = InceptionResnetV1(pretrained='vggface2').eval().to(device)

def preprocess_face(face_img, target_size=(160, 160)):
    """
    Pra-pemrosesan wajah untuk model ArcFace
    
    Args:
        face_img (numpy.ndarray): Gambar wajah
        target_size (tuple): Ukuran target untuk model
        
    Returns:
        torch.Tensor: Tensor wajah yang telah diproses
    """
    if face_img is None:
        return None
        
    # Resize gambar
    face_img = cv2.resize(face_img, target_size)
    
    # Konversi BGR ke RGB
    face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
    
    # Normalisasi (0-255 -> 0-1)
    face_img = face_img / 255.0
    
    # Konversi ke tensor
    face_tensor = torch.from_numpy(face_img.transpose((2, 0, 1))).float()
    
    # Tambahkan dimensi batch
    face_tensor = face_tensor.unsqueeze(0)
    
    return face_tensor

def extract_embedding(face_tensor):
    """
    Ekstrak embedding dari wajah menggunakan ArcFace
    
    Args:
        face_tensor (torch.Tensor): Tensor wajah yang telah diproses
        
    Returns:
        numpy.ndarray: Vektor embedding
    """
    if face_tensor is None:
        return None
        
    with torch.no_grad():
        face_tensor = face_tensor.to(device)
        embedding = arcface_model(face_tensor).cpu().numpy()
        
    return embedding[0]  # Hilangkan dimensi batch

def compute_similarity(embedding1, embedding2):
    """
    Menghitung cosine similarity antara dua embedding
    
    Args:
        embedding1 (numpy.ndarray): Embedding pertama
        embedding2 (numpy.ndarray): Embedding kedua
        
    Returns:
        float: Cosine similarity (0-1)
    """
    dot_product = np.dot(embedding1, embedding2)
    norm1 = np.linalg.norm(embedding1)
    norm2 = np.linalg.norm(embedding2)
    
    if norm1 == 0 or norm2 == 0:
        return 0
        
    return dot_product / (norm1 * norm2)

def save_embeddings(embeddings_dict, file_path):
    """
    Menyimpan embeddings ke file
    
    Args:
        embeddings_dict (dict): Dictionary nama -> embedding
        file_path (str): Path file tujuan
    """
    # Buat direktori jika belum ada
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'wb') as f:
        pickle.dump(embeddings_dict, f)
        
def load_embeddings(file_path):
    """
    Memuat embeddings dari file
    
    Args:
        file_path (str): Path file sumber
        
    Returns:
        dict: Dictionary nama -> embedding
    """
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except (FileNotFoundError, EOFError):
        print(f"File embedding tidak ditemukan di {file_path}")
        return {} 