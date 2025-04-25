from pyfingerprint.pyfingerprint import PyFingerprint

PORT = 'COM5'   # Ubah kalau port-nya beda
BAUDRATE = 57600

def initialize_sensor():
    try:
        f = PyFingerprint(PORT, BAUDRATE, 0xFFFFFFFF, 0x00000000)
        if not f.verifyPassword():
            raise ValueError('Password sensor salah.')
        return f
    except Exception as e:
        print('[!] Gagal inisialisasi sensor:', e)
        return None


def scan_fingerprint():
    f = initialize_sensor()
    if not f:
        return None

    print('[INFO] Menunggu scan sidik jari...')
    try:
        while not f.readImage():
            pass

        f.convertImage(0x01)
        result = f.searchTemplate()

        positionNumber = result[0]
        accuracyScore = result[1]

        if positionNumber == -1:
            print('[!] Sidik jari tidak dikenali.')
            return None
        else:
            print(f'[+] Dikenali! ID: {positionNumber}, Akurasi: {accuracyScore}')
            return positionNumber

    except Exception as e:
        print('[!] Gagal saat scan:', e)
        return None


def enroll_fingerprint():
    f = initialize_sensor()
    if not f:
        return None

    try:
        print('[INFO] Mencari slot kosong untuk menyimpan sidik jari...')
        count = f.getTemplateCount()
        if count >= f.getStorageCapacity():
            print('[!] Penyimpanan penuh.')
            return None

        print('[INFO] Tempelkan jari Anda...')
        while not f.readImage():
            pass

        f.convertImage(0x01)

        print('[INFO] Angkat jari dan tempelkan kembali...')
        while f.readImage():
            pass
        while not f.readImage():
            pass

        f.convertImage(0x02)

        if f.compareCharacteristics() == 0:
            print('[!] Jari tidak cocok, coba lagi.')
            return None

        f.createTemplate()
        positionNumber = f.storeTemplate()
        print(f'[+] Sidik jari berhasil disimpan di ID: {positionNumber}')
        return positionNumber

    except Exception as e:
        print('[!] Gagal mendaftar sidik jari:', e)
        return None


def delete_fingerprint(template_id):
    f = initialize_sensor()
    if not f:
        return False

    try:
        if f.deleteTemplate(template_id):
            print(f'[+] Sidik jari di ID {template_id} berhasil dihapus.')
            return True
        else:
            print('[!] Gagal menghapus template.')
            return False
    except Exception as e:
        print('[!] Gagal menghapus template:', e)
        return False


# Fungsi test opsional jika dijalankan langsung
if __name__ == "__main__":
    print("1. Enroll Fingerprint")
    print("2. Delete Fingerprint")
    print("3. Scan Fingerprint")
    choice = input("Pilih menu: ")

    if choice == "1":
        enroll_fingerprint()
    elif choice == "2":
        template_id = int(input("Masukkan ID yang ingin dihapus: "))
        delete_fingerprint(template_id)
    elif choice == "3":
        scan_fingerprint() 