import spacy
from pypdf import PdfReader,PdfWriter
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

# NLP modelini yükle
nlp = spacy.load("en_core_web_md")


HAKEM_ALANLARI = {
    "CihangirEmreEr": {"Deep Learning", "Natural Language Processing", "Computer Vision", "Generative AI"},
    "ElifEceEr": {"Brain-Computer Interfaces", "User Experience Design", "Augmented Reality", "Virtual Reality"},
    "TravisScott": {"Data Mining", "Data Visualization", "Big Data Processing", "Time Series Analysis"},
    "KanyeWest": {"Cryptography", "Secure Software", "Network Security", "Authentication Systems", "Digital Forensics"},
    "RobertPattinson": {"5G", "Cloud Computing", "Blockchain", "P2P", "Decentralized Systems"},
}

def pdf_metin_cikar(pdf_path):
    reader = PdfReader(pdf_path)
    text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    return text

def get_tfidf_keywords(text, top_n=10):
    """TF-IDF yöntemiyle metindeki en önemli kelimeleri belirler."""
    vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
    tfidf_matrix = vectorizer.fit_transform([text])
    feature_array = vectorizer.get_feature_names_out()
    tfidf_scores = tfidf_matrix.toarray().flatten()
    
    # En yüksek TF-IDF değerine sahip kelimeleri al
    tfidf_sorted = sorted(zip(feature_array, tfidf_scores), key=lambda x: x[1], reverse=True)
    return [word for word, score in tfidf_sorted[:top_n]]

def get_embedding(text):
    """Verilen metnin ortalama kelime vektörünü hesaplar."""
    doc = nlp(text)
    vectors = np.array([token.vector for token in doc if token.has_vector and not token.is_stop])
    return np.mean(vectors, axis=0) if len(vectors) > 0 else np.zeros((300,))

def makale_konusu_belirle(pdf_path):
    """Makale konusunu belirleyerek en uygun hakemi bulur."""
    text = pdf_metin_cikar(pdf_path)
    makale_keywords = get_tfidf_keywords(text)

    makale_vector = get_embedding(" ".join(makale_keywords))

    hakem_skorlari = {}
    for hakem, konular in HAKEM_ALANLARI.items():
        hakem_vector = get_embedding(" ".join(konular))
        skor = cosine_similarity([makale_vector], [hakem_vector])[0][0]
        hakem_skorlari[hakem] = skor

    # En uygun hakemi bul
    en_uygun_hakem = max(hakem_skorlari, key=hakem_skorlari.get)

    return {
        "keywords": makale_keywords,
        "konu": en_uygun_hakem,
        "eslesme_skoru": hakem_skorlari[en_uygun_hakem]
    }

def yorum_ekle_kaydet(pdf_path, text, new_pdf_path):
    yorum_sayfasi = io.BytesIO()

    c = canvas.Canvas(yorum_sayfasi,A4)

    c.setFont("Helvetica",12)
    c.drawString(100,800,"Hakem Degerlendirmesi:")

    y = 780
    for satir in text.split('\n'):
        c.drawString(100,y,satir)
        y -= 20
        if y < 50:
            c.showPage()
            y = 800

    c.save()
    yorum_sayfasi.seek(0)

    yorum_reader = PdfReader(yorum_sayfasi)
    yorum_page = yorum_reader.pages[0]

    original_reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in original_reader.pages:
        writer.add_page(page)

    writer.add_page(yorum_page)

    with open(new_pdf_path, "wb") as f:
        writer.write(f)

    return new_pdf_path
#Test için
#if __name__ == "__main__":
#    test_pdf_path = "ICSTASY_An_Integrated_Cybersecurity_Training_System_for_Military_Personnel.pdf"  # Örnek makalenin dosya yolu
#    sonuc = makale_konusu_belirle(test_pdf_path)
#    print(sonuc)

    
