import re
import spacy
import base64
import fitz  # PyMuPDF
import os
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from pdf2image import convert_from_path
from PIL import Image
import cv2
import numpy as np
from .models import AnonimEtiket
from django.conf import settings
from io import BytesIO

# --- AES Yardımcıları ---


def pad(text):
    byte_text = text.encode('utf-8')
    pad_len = 16 - len(byte_text) % 16
    return byte_text + bytes([pad_len] * pad_len)

def unpad(padded_bytes):
    pad_len = padded_bytes[-1]
    return padded_bytes[:-pad_len].decode('utf-8')

def encrypt_aes(text, key=None):
    key = key or settings.AES_SECRET_KEY
    cipher = AES.new(key, AES.MODE_ECB)
    padded = pad(text)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode("utf-8")

def decrypt_aes(cipher_text, key=None):
    key = key or settings.AES_SECRET_KEY
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = cipher.decrypt(base64.b64decode(cipher_text))
    return unpad(decrypted)

# --- NLP Modeli ---
nlp = spacy.load("en_core_web_trf")

# --- Tespit Fonksiyonları ---
def detect_sensitive_info(text):
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    kurumlar = re.findall(r"\b(University|Institute|Faculty|Department|College)\b.*", text, re.IGNORECASE)
    doc = nlp(text)
    names = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]
    return list(set(names)), list(set(emails)), list(set(kurumlar))

# --- Yüz bulanıklaştırma ---
def blur_faces(pdf_path, output_path, poppler_path=r"C:\poppler-24.08.0\bin"):
    images = convert_from_path(pdf_path, poppler_path=poppler_path)
    cascade_path = r"C:\opencv_models\haarcascade_frontalface_default.xml"

    face_cascade = cv2.CascadeClassifier(cascade_path)
    if face_cascade.empty():
        print(f"Haarcascade yüklenemedi: {cascade_path}")
        return False
    else:
        print(f"Haarcascade başarıyla yüklendi: {cascade_path}")

    face_found = False
    processed_images = []

    for img in images:
        img_cv = np.array(img.convert("RGB"))
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        if len(faces) > 0:
            face_found = True

        for (x, y, w, h) in faces:
            face_region = img_cv[y:y+h, x:x+w]
            blurred = cv2.GaussianBlur(face_region, (99, 99), 30)
            img_cv[y:y+h, x:x+w] = blurred

        processed_images.append(Image.fromarray(img_cv))

    if face_found:
        processed_images[0].save(output_path, save_all=True, append_images=processed_images[1:])
        return True
    return False


# --- Etiketli anonimleştirme ve şifreleme ---
def anonymize_and_tag_pdf(pdf_path, output_path,makale):
    doc = fitz.open(pdf_path)
    encrypted_data = {}
    tag_counters = {"ISIM": 0, "EMAIL": 0, "KURUM": 0}

    for page in doc:
        text = page.get_text()
        isimler, mailler, kurumlar = detect_sensitive_info(text)

        for kategori, kelimeler in [("ISIM", isimler), ("EMAIL", mailler), ("KURUM", kurumlar)]:
            for kelime in kelimeler:
                tag_counters[kategori] += 1
                tag = f"[ANONIM:{kategori}#{tag_counters[kategori]}]"
                try:
                    encrypted = encrypt_aes(kelime)
                    encrypted_data[tag] = encrypted
                    #Veritabanına kayıt etme
                    AnonimEtiket.objects.create(
                        makale=makale,
                        tag=tag,
                        encrypted=encrypted,
                        category=kategori
                    )

                except Exception as e:
                    print(f"[!] Şifreleme hatası: {kelime} → {e}")
                    continue

                areas = page.search_for(kelime)
                for rect in areas:
                    page.add_redact_annot(rect, text=tag, fill=(1,1,1), fontsize=14)

        page.apply_redactions()

    doc.save(output_path)
    return encrypted_data

def etiketsiz_pdf_olustur(makale, girdi_pdf_yolu, cikti_pdf_yolu):
    doc = fitz.open(girdi_pdf_yolu)
    etiketler = AnonimEtiket.objects.filter(makale=makale)

    tag_to_text = {}
    for e in etiketler:
        try:
            orijinal = decrypt_aes(e.encrypted)
            tag_to_text[e.tag] = orijinal
        except Exception as err:
            print(f"[!] Etiket çözümleme hatası: {e.tag} → {err}")

    for page in doc:
        blocks = page.get_text("blocks")
        for b in blocks:
            block_text = b[4]
            for tag, orijinal in tag_to_text.items():
                if tag in block_text:
                    rects = page.search_for(tag)
                    for rect in rects:
                        page.add_redact_annot(rect, text=orijinal, fill=(1, 1, 1), fontsize=12)

        page.apply_redactions()

    doc.save(cikti_pdf_yolu)
    return cikti_pdf_yolu



# --- Ana Test ---
#if __name__ == "__main__":
#    pdf_input = "örnek_makale1.pdf"
#    pdf_output_text = "anonim_text_1.pdf"
#    pdf_output_faces = "anonim_faces_1.pdf"

#    print("[🔐] Metinsel anonimleştirme başlatılıyor...")
#    encrypted_map = anonymize_and_tag_pdf(pdf_input, pdf_output_text)

#    print("\n[🔎] Yüz taraması başlatılıyor...")
#    if blur_faces_preserve_text(pdf_input, pdf_output_faces):
#        print("[✔️] Yüz bulanıklaştırması tamamlandı:", pdf_output_faces)
#    else:
#        print("[ℹ️] PDF'de yüz bulunamadı, işlem atlandı.")


#    print("\n[🔒] Şifrelenmiş bilgiler:")
#    for tag, cipher in encrypted_map.items():
#        print(f"{tag} -> {cipher}")
