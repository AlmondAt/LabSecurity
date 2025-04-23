from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import json
from datetime import datetime
import sqlite3
import glob
import shutil

# Init app
app = Flask(__name__)
app.secret_key = 'aksescontrolsystem'

# Database setup
DATABASE = 'arcface.db'
PHOTOS_FOLDER = '../photos'
FACES_FOLDER = 'faces'

def init_db():
    """Inisialisasi database"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Buat tabel users jika belum ada
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        access_level INTEGER DEFAULT 1,
        finger_id INTEGER,
        has_face BOOLEAN DEFAULT 0,
        face_path TEXT,
        created_at TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Mendapatkan koneksi database"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Agar hasil query bisa diakses seperti dictionary
    return conn

def import_existing_faces():
    """Mengimpor wajah yang sudah ada di folder photos ke database"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Mencari semua nama unik dari file foto
    photo_files = glob.glob(os.path.join(PHOTOS_FOLDER, '*.jpg'))
    names = set()
    
    for photo_file in photo_files:
        # Ambil nama dari nama file (contoh: fariz_1.jpg -> fariz)
        basename = os.path.basename(photo_file)
        name = basename.split('_')[0].capitalize()
        names.add(name)
    
    # Buat folder faces jika belum ada
    os.makedirs(FACES_FOLDER, exist_ok=True)
    
    # Tambahkan pengguna untuk setiap nama yang ditemukan
    for name in names:
        # Cek apakah pengguna sudah ada di database
        cursor.execute('SELECT id FROM users WHERE name = ?', (name,))
        user = cursor.fetchone()
        
        if not user:
            # Jika pengguna belum ada, tambahkan ke database
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'INSERT INTO users (name, description, access_level, has_face, created_at) VALUES (?, ?, ?, ?, ?)',
                (name, f'Pengguna {name}', 1, 1, created_at)
            )
            conn.commit()
            user_id = cursor.lastrowid
            
            # Salin foto ke folder faces
            user_face_dir = os.path.join(FACES_FOLDER, str(user_id))
            os.makedirs(user_face_dir, exist_ok=True)
            
            # Salin foto pertama
            user_files = glob.glob(os.path.join(PHOTOS_FOLDER, f'{name.lower()}_*.jpg'))
            if user_files:
                face_file = user_files[0]
                target_file = os.path.join(user_face_dir, 'face.jpg')
                shutil.copy2(face_file, target_file)
                
                # Update database dengan path foto
                cursor.execute('UPDATE users SET face_path = ? WHERE id = ?', (target_file, user_id))
                conn.commit()
    
    conn.close()

# Inisialisasi database saat aplikasi pertama kali dijalankan
init_db()

# Import wajah yang sudah ada
import_existing_faces()

# Setup folder upload
UPLOAD_FOLDER = 'photos/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Routes
@app.route('/')
def index():
    """Halaman utama dashboard"""
    return render_template('index.html')

@app.route('/users')
def users():
    """Halaman daftar pengguna"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY id ASC')
    users_data = cursor.fetchall()
    conn.close()
    
    return render_template('users.html', users=users_data)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Halaman pendaftaran pengguna baru"""
    if request.method == 'POST':
        name = request.form.get('name', '')
        description = request.form.get('description', '')
        access_level = int(request.form.get('access_level', 1))
        
        # Cek nama duplikat
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE name = ?', (name,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            flash('Nama sudah terdaftar!', 'danger')
            return redirect(url_for('register'))
        
        # Buat user baru
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            'INSERT INTO users (name, description, access_level, created_at) VALUES (?, ?, ?, ?)',
            (name, description, access_level, created_at)
        )
        
        conn.commit()
        new_user_id = cursor.lastrowid
        conn.close()
        
        flash(f'Pengguna {name} berhasil ditambahkan', 'success')
        return redirect(url_for('enroll_fingerprint', user_id=new_user_id))
    
    return render_template('register.html')

@app.route('/enroll_fingerprint/<int:user_id>')
def enroll_fingerprint(user_id):
    """Halaman pendaftaran sidik jari"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        flash('Pengguna tidak ditemukan!', 'danger')
        return redirect(url_for('users'))
    
    return render_template('enroll_fingerprint.html', user=user)

@app.route('/api/enroll_fingerprint', methods=['POST'])
def api_enroll_fingerprint():
    """API untuk pendaftaran sidik jari"""
    data = request.json
    user_id = data.get('user_id')
    
    # Cari user dan update finger_id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Simulasi pendaftaran sidik jari
        # Generate dummy ID berdasarkan jumlah user
        cursor.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]
        finger_id = count + 1
        
        # Update user
        cursor.execute('UPDATE users SET finger_id = ? WHERE id = ?', (finger_id, user_id))
        conn.commit()
        
        # Cek apakah user sudah punya data wajah
        if user['has_face']:
            next_url = url_for('users')
            message = f'Sidik jari berhasil didaftarkan dengan ID: {finger_id}. Pengguna sudah memiliki data wajah.'
        else:
            next_url = url_for('enroll_face', user_id=user_id)
            message = f'Sidik jari berhasil didaftarkan dengan ID: {finger_id}'
        
        conn.close()
        return jsonify({
            'success': True,
            'message': message,
            'next_url': next_url
        })
    
    conn.close()
    return jsonify({
        'success': False,
        'message': 'Pengguna tidak ditemukan'
    })

@app.route('/enroll_face/<int:user_id>')
def enroll_face(user_id):
    """Halaman pendaftaran wajah"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        flash('Pengguna tidak ditemukan!', 'danger')
        return redirect(url_for('users'))
    
    return render_template('enroll_face.html', user=user)

@app.route('/api/capture_face', methods=['POST'])
def api_capture_face():
    """API untuk pengambilan wajah dari webcam"""
    user_id = int(request.form.get('user_id', 0))
    
    # Update user dengan data wajah
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Simpan foto wajah
        user_face_dir = os.path.join(FACES_FOLDER, str(user_id))
        os.makedirs(user_face_dir, exist_ok=True)
        
        # Simpan data gambar dari form
        image_data = request.form.get('image')
        if image_data and image_data.startswith('data:image'):
            import base64
            # Ambil data base64 dari data URI
            image_data = image_data.split(',')[1]
            
            # Simpan ke file
            face_path = os.path.join(user_face_dir, 'face.jpg')
            with open(face_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            
            # Update database
            cursor.execute('UPDATE users SET has_face = 1, face_path = ? WHERE id = ?', (face_path, user_id))
            conn.commit()
        
        user_name = user['name']
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Data wajah untuk {user_name} berhasil disimpan',
            'next_url': url_for('users')
        })
    
    conn.close()
    return jsonify({
        'success': False,
        'message': 'Pengguna tidak ditemukan'
    })

@app.route('/api/upload_face', methods=['POST'])
def api_upload_face():
    """API untuk upload foto wajah"""
    user_id = int(request.form.get('user_id', 0))
    
    # Update user dengan data wajah
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Simpan foto yang diupload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename:
                # Buat direktori untuk user jika belum ada
                user_face_dir = os.path.join(FACES_FOLDER, str(user_id))
                os.makedirs(user_face_dir, exist_ok=True)
                
                # Simpan file
                face_path = os.path.join(user_face_dir, 'face.jpg')
                file.save(face_path)
                
                # Update database
                cursor.execute('UPDATE users SET has_face = 1, face_path = ? WHERE id = ?', (face_path, user_id))
                conn.commit()
        
        user_name = user['name']
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Data wajah untuk {user_name} berhasil disimpan',
            'next_url': url_for('users')
        })
    
    conn.close()
    return jsonify({
        'success': False,
        'message': 'Pengguna tidak ditemukan'
    })

@app.route('/api/delete_user/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """API untuk menghapus pengguna"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Cari dan hapus user
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        
        # Hapus folder wajah jika ada
        user_face_dir = os.path.join(FACES_FOLDER, str(user_id))
        if os.path.exists(user_face_dir):
            shutil.rmtree(user_face_dir)
        
        return jsonify({
            'success': True,
            'message': 'Pengguna berhasil dihapus'
        })
    
    conn.close()
    return jsonify({
        'success': False,
        'message': 'Pengguna tidak ditemukan'
    })

@app.route('/add_fingerprint/<int:user_id>', methods=['GET', 'POST'])
def add_fingerprint(user_id):
    """Halaman untuk menambahkan sidik jari pada pengguna yang sudah ada"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        flash('Pengguna tidak ditemukan!', 'danger')
        return redirect(url_for('users'))
    
    # Redirect ke halaman pendaftaran sidik jari
    return redirect(url_for('enroll_fingerprint', user_id=user_id))

@app.route('/add_face/<int:user_id>', methods=['GET', 'POST'])
def add_face(user_id):
    """Halaman untuk menambahkan wajah pada pengguna yang sudah ada"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        flash('Pengguna tidak ditemukan!', 'danger')
        return redirect(url_for('users'))
    
    # Redirect ke halaman pendaftaran wajah
    return redirect(url_for('enroll_face', user_id=user_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)