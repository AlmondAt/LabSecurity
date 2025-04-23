import os
import pickle
import sqlite3
from datetime import datetime

# Konstanta untuk database
DEFAULT_DB_PATH = 'data/access_control.db'
DEFAULT_EMBEDDINGS_PATH = 'data/embeddings.pkl'
UNKNOWN_DIR = 'data/unknown'

class AccessDatabase:
    def __init__(self, db_path=DEFAULT_DB_PATH, embeddings_path=DEFAULT_EMBEDDINGS_PATH):
        self.db_path = db_path
        self.embeddings_path = embeddings_path
        self.conn = None
        self.embeddings = {}
        self.unknown_dir = UNKNOWN_DIR
        
        # Buat direktori jika belum ada
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs(self.unknown_dir, exist_ok=True)
    
    def connect(self):
        """Menghubungkan ke database SQLite"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.create_tables()
            self.load_embeddings()
            return True
        except Exception as e:
            print(f"Error saat menghubungkan ke database: {e}")
            return False
    
    def close(self):
        """Menutup koneksi database"""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Membuat tabel dalam database jika belum ada"""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        
        # Tabel pengguna
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            finger_id INTEGER UNIQUE,
            access_level INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_access TIMESTAMP
        )
        ''')
        
        # Tabel log akses
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            access_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL,
            message TEXT,
            image_path TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Tabel pengguna tidak dikenal
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS unknown_access (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            image_path TEXT,
            fingerprint_data BLOB,
            message TEXT
        )
        ''')
        
        self.conn.commit()
        return True
    
    def load_embeddings(self):
        """Memuat embedding wajah dari file pickle"""
        try:
            if os.path.exists(self.embeddings_path):
                with open(self.embeddings_path, 'rb') as f:
                    self.embeddings = pickle.load(f)
                print(f"Berhasil memuat {len(self.embeddings)} embedding wajah")
            else:
                print("File embedding tidak ditemukan, membuat baru")
                self.embeddings = {}
                self.save_embeddings()
            return True
        except Exception as e:
            print(f"Error saat memuat embedding: {e}")
            self.embeddings = {}
            return False
    
    def save_embeddings(self):
        """Menyimpan embedding wajah ke file pickle"""
        try:
            with open(self.embeddings_path, 'wb') as f:
                pickle.dump(self.embeddings, f)
            return True
        except Exception as e:
            print(f"Error saat menyimpan embedding: {e}")
            return False
    
    def add_user(self, name, finger_id=None, access_level=1):
        """Menambahkan pengguna baru ke database"""
        if not self.conn:
            return {"success": False, "message": "Database tidak terhubung"}
        
        cursor = self.conn.cursor()
        try:
            # Periksa apakah finger_id sudah ada
            if finger_id is not None:
                cursor.execute("SELECT id FROM users WHERE finger_id = ?", (finger_id,))
                if cursor.fetchone():
                    return {"success": False, "message": f"ID sidik jari {finger_id} sudah terdaftar"}
            
            # Tambahkan pengguna baru
            cursor.execute(
                "INSERT INTO users (name, finger_id, access_level) VALUES (?, ?, ?)",
                (name, finger_id, access_level)
            )
            self.conn.commit()
            user_id = cursor.lastrowid
            
            return {"success": True, "user_id": user_id, "message": f"Pengguna {name} berhasil ditambahkan"}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": f"Gagal menambahkan pengguna: {e}"}
    
    def get_user_by_finger_id(self, finger_id):
        """Mencari pengguna berdasarkan ID sidik jari"""
        if not self.conn:
            return {"success": False, "message": "Database tidak terhubung"}
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id, name, access_level FROM users WHERE finger_id = ?", (finger_id,))
            user = cursor.fetchone()
            
            if user:
                # Update last_access
                cursor.execute("UPDATE users SET last_access = CURRENT_TIMESTAMP WHERE id = ?", (user[0],))
                self.conn.commit()
                
                return {
                    "success": True,
                    "user_id": user[0],
                    "name": user[1],
                    "access_level": user[2]
                }
            else:
                return {"success": False, "message": "Pengguna tidak ditemukan"}
        except Exception as e:
            return {"success": False, "message": f"Error saat mencari pengguna: {e}"}
    
    def get_user_by_name(self, name):
        """Mencari pengguna berdasarkan nama"""
        if not self.conn:
            return {"success": False, "message": "Database tidak terhubung"}
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id, name, finger_id, access_level FROM users WHERE name = ?", (name,))
            user = cursor.fetchone()
            
            if user:
                return {
                    "success": True,
                    "user_id": user[0],
                    "name": user[1],
                    "finger_id": user[2],
                    "access_level": user[3]
                }
            else:
                return {"success": False, "message": "Pengguna tidak ditemukan"}
        except Exception as e:
            return {"success": False, "message": f"Error saat mencari pengguna: {e}"}
    
    def log_access(self, user_id, access_type, success, message="", image_path=None):
        """Mencatat akses ke dalam log"""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO access_logs (user_id, access_type, success, message, image_path) VALUES (?, ?, ?, ?, ?)",
                (user_id, access_type, success, message, image_path)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saat mencatat akses: {e}")
            self.conn.rollback()
            return False
    
    def log_unknown_access(self, image_path, fingerprint_data=None, message="Akses tidak dikenal"):
        """Mencatat akses dari orang yang tidak dikenal"""
        if not self.conn:
            return False
        
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO unknown_access (image_path, fingerprint_data, message) VALUES (?, ?, ?)",
                (image_path, fingerprint_data, message)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error saat mencatat akses tidak dikenal: {e}")
            self.conn.rollback()
            return False
    
    def save_unknown_face(self, frame):
        """Menyimpan gambar wajah tidak dikenal"""
        try:
            # Buat nama file unik berdasarkan timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"unknown_{timestamp}.jpg"
            filepath = os.path.join(self.unknown_dir, filename)
            
            # Simpan gambar
            import cv2
            cv2.imwrite(filepath, frame)
            
            return filepath
        except Exception as e:
            print(f"Error saat menyimpan wajah tidak dikenal: {e}")
            return None
    
    def link_face_to_finger(self, name, finger_id, embedding):
        """Menghubungkan data wajah dengan ID sidik jari pengguna"""
        if not self.conn:
            return {"success": False, "message": "Database tidak terhubung"}
        
        # Cari pengguna berdasarkan ID sidik jari
        user_result = self.get_user_by_finger_id(finger_id)
        
        if not user_result["success"]:
            # Tambahkan pengguna baru jika belum ada
            user_result = self.add_user(name, finger_id)
            if not user_result["success"]:
                return user_result
        
        # Simpan embedding wajah
        self.embeddings[name] = embedding
        if self.save_embeddings():
            return {"success": True, "message": f"Wajah untuk {name} berhasil ditambahkan"}
        else:
            return {"success": False, "message": "Gagal menyimpan embedding wajah"}
    
    def get_all_users(self):
        """Mendapatkan semua pengguna dari database"""
        if not self.conn:
            return {"success": False, "message": "Database tidak terhubung"}
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id, name, finger_id, access_level, created_at, last_access FROM users")
            users = cursor.fetchall()
            
            result = []
            for user in users:
                result.append({
                    "id": user[0],
                    "name": user[1],
                    "finger_id": user[2],
                    "access_level": user[3],
                    "created_at": user[4],
                    "last_access": user[5],
                    "has_face": user[1] in self.embeddings
                })
            
            return {"success": True, "users": result}
        except Exception as e:
            return {"success": False, "message": f"Error saat mengambil data pengguna: {e}"}
    
    def delete_user(self, user_id):
        """Menghapus pengguna dari database"""
        if not self.conn:
            return {"success": False, "message": "Database tidak terhubung"}
        
        cursor = self.conn.cursor()
        try:
            # Cari nama pengguna untuk menghapus embedding
            cursor.execute("SELECT name FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return {"success": False, "message": "Pengguna tidak ditemukan"}
            
            name = user[0]
            
            # Hapus dari database
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            
            # Hapus embedding jika ada
            if name in self.embeddings:
                del self.embeddings[name]
                self.save_embeddings()
            
            return {"success": True, "message": f"Pengguna {name} berhasil dihapus"}
        except Exception as e:
            self.conn.rollback()
            return {"success": False, "message": f"Gagal menghapus pengguna: {e}"}

# Contoh penggunaan
if __name__ == "__main__":
    db = AccessDatabase()
    if db.connect():
        print("Terhubung ke database berhasil")
        
        # Contoh menambahkan pengguna
        result = db.add_user("Admin", finger_id=1, access_level=2)
        print(result)
        
        # Contoh mencari pengguna
        result = db.get_user_by_finger_id(1)
        print(result)
        
        # Contoh mencatat akses
        if result["success"]:
            db.log_access(result["user_id"], "fingerprint", True, "Akses berhasil")
        
        # Contoh mendapatkan semua pengguna
        result = db.get_all_users()
        print(result)
        
        db.close()
    else:
        print("Gagal terhubung ke database") 