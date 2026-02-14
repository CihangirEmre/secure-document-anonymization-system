from django.db import models
from django.contrib.auth.models import User
import uuid
from django.utils.text import slugify
import os

def takip_numarasi_olustur():
    return str(uuid.uuid4())[:8]

class Kullanici(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.email

class Hakem(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    uzmanlik_alani = models.CharField(max_length=200)

    def __str__(self):
        return self.name

def makale_dosya_yolu(instance, filename):
    kullanici_id = instance.user.id
    filename = slugify(filename)

    return f"makaleler/user_{kullanici_id}/{filename}"

def anonim_dosya_yolu(instance, filename):
    kullanici_id = instance.user.id
    filename = slugify(filename)
    return f"anonim_makaleler/user_{kullanici_id}/{filename}"



class Makale(models.Model):
    DURUM_SECIMLERI = [
        ('Beklemede', 'Beklemede'),
        ('Değerlendirmede', 'Değerlendirmede'),
        ('Kabul Edildi', 'Kabul Edildi'),
        ('Reddedildi', 'Reddedildi'),
    ]

    user = models.ForeignKey(Kullanici, on_delete=models.CASCADE, related_name='makaleler')
    takip_numarasi = models.CharField(max_length=20, unique=True, default = takip_numarasi_olustur)
    pdf_dosya = models.FileField(upload_to=makale_dosya_yolu)
    yuklenme_tarihi = models.DateTimeField(auto_now_add=True)
    durum = models.CharField(max_length=50, choices=DURUM_SECIMLERI, default='Beklemede')
    anonimlestirildi_mi = models.BooleanField(default=False)
    anonim_pdf_dosya = models.FileField(upload_to=anonim_dosya_yolu)
    hakem = models.ForeignKey("Hakem",on_delete=models.SET_NULL, null=True, blank=True, related_name='atanan_makaleler')

    def __str__(self):
        return self.takip_numarasi

class Degerlendirme(models.Model):
    makale = models.ForeignKey(Makale, on_delete=models.CASCADE, related_name='degerlendirmeler')
    hakem = models.ForeignKey(Hakem, on_delete=models.CASCADE, related_name='degerlendirmeler')
    yorum = models.TextField()
    degerlendirme_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.makale.takip_numarasi} - {self.hakem.name}"

class Mesaj(models.Model):
    gonderen_kullanici = models.ForeignKey(Kullanici, on_delete=models.CASCADE, null=True, blank=True, related_name='gonderilen_mesajlar')
    gonderen_editor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='editor_gonderilen_mesajlar')

    alici_kullanici = models.ForeignKey(Kullanici, on_delete=models.CASCADE, null=True, blank=True, related_name='alinan_mesajlar')
    alici_editor = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='editor_alinan_mesajlar')

    konu = models.CharField(max_length=200)
    icerik = models.TextField()
    gonderim_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.konu} - {self.gonderim_tarihi}"

class AnonimleştirmeLog(models.Model):
    makale = models.ForeignKey(Makale, on_delete=models.CASCADE, related_name='anonimlestirme_loglari')
    editor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='anonimlestirme_loglari')  # Yönetici Django'nun User modeli
    islem_tarihi = models.DateTimeField(auto_now_add=True)
    yapilan_islem = models.TextField()

    def __str__(self):
        return f"{self.makale.takip_numarasi} - {self.editor.username}"
    
class AnonimEtiket(models.Model):
    makale = models.ForeignKey(Makale, on_delete=models.CASCADE, related_name='anonim_etiketleri',null=True)
    tag = models.CharField(max_length=100)
    encrypted = models.TextField()
    category = models.CharField(max_length=20, choices=[
        ("ISIM", "Yazar Adi"),
        ("EMAIL", "Email"),
        ("KURUM", "Kurum")
    ])

    class Meta:
        unique_together = ('makale', 'tag')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.tag}"