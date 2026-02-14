from django.shortcuts import render, redirect, get_object_or_404
from makale_sistemi.models import Makale, Kullanici, Hakem, Mesaj,Degerlendirme, AnonimleştirmeLog
import uuid
import os
from django.conf import settings
from makale_sistemi.utils import makale_konusu_belirle,yorum_ekle_kaydet
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.text import slugify
from .utilsd import anonymize_and_tag_pdf, blur_faces
from django.conf import settings
from .models import Makale
import os
from .utilsd import decrypt_aes, AnonimEtiket
from .utilsd import etiketsiz_pdf_olustur

def log_ekle(makale, editor_user, islem_metni):
    AnonimleştirmeLog.objects.create(
        makale=makale,
        editor=editor_user,
        yapilan_islem=islem_metni
    )

def giris_sayfasi(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        if email:
            # Kullanıcıyı bul veya oluştur
            kullanici, created = Kullanici.objects.get_or_create(email=email)
            request.session['email'] = kullanici.email
            return redirect('kullanici_sayfa')

    return render(request, 'makale_sistemi/giris.html')

def hakem_sayfasi(request, hakem_adi):
    hakem = get_object_or_404(Hakem, name = hakem_adi)
    makaleler = Makale.objects.filter(hakem=hakem).order_by("yuklenme_tarihi")

    
    return render(request, "makale_sistemi/hakem_sayfasi.html", {
        "hakem": hakem,
        "makaleler": makaleler
    })

def hakem_degerlendir(request, makale_id):
    if request.method == 'POST':
        try:
            makale = Makale.objects.get(id=makale_id)
        except Makale.DoesNotExist:
            return JsonResponse({'error': 'Makale bulunamadı'}, status=404)

        yorum = request.POST.get("yorum")
        #puan = request.POST.get("puan")
        hakem = makale.hakem  # atanmış hakemi kullan

        if yorum:
            Degerlendirme.objects.create(
                makale=makale,
                hakem=hakem,
                yorum=yorum,
            )
            makale.durum = "Değerlendirmede"
            makale.save()

            orijinal_pdf_path = os.path.join(settings.MEDIA_ROOT, str(makale.pdf_dosya))
            hakem_klasoru = os.path.join(settings.MEDIA_ROOT, "hakem_makaleler")
            os.makedirs(hakem_klasoru, exist_ok=True)

            yeni_pdf_path = os.path.join(hakem_klasoru, f"{makale.takip_numarasi}_degerlendirme.pdf")

            yorum_ekle_kaydet(orijinal_pdf_path, yorum, yeni_pdf_path)
            etiketsiz_klasor = os.path.join(settings.MEDIA_ROOT, "sonuc_makaleler")
            os.makedirs(etiketsiz_klasor, exist_ok=True)

            etiketsiz_pdf_yolu = os.path.join(etiketsiz_klasor, f"{makale.takip_numarasi}_tam.pdf")
            etiketsiz_pdf_olustur(makale, yeni_pdf_path, etiketsiz_pdf_yolu)

            editor = User.objects.filter(is_superuser=True).first()
            if editor:
                log_ekle(makale, editor, f"Hakem {hakem.name} değerlendirme yaptı ve yorum eklendi.")

            return redirect('hakem_sayfasi', hakem_adi=hakem)

def makale_sorgulama(request):
    mesaj=None
    makale=None

    if request.method == 'POST':
        email = request.POST.get("email")
        takip_numarasi = request.POST.get("takip_numarasi")

        if email and takip_numarasi:
            try:
                makale = Makale.objects.get(user__email = email, takip_numarasi=takip_numarasi)
            except:
                mesaj = "Girilen e-posta ve takip numarası ile eşleşen makale bulunamadı."
                
    return render(request, "makale_sistemi/makale_sorgulama.html", {"makale": makale, "mesaj": mesaj})


def kullanici_sayfa(request):
    return render(request, "makale_sistemi/kullanici_sayfa.html")


def takip_numarasi_olustur():
    return str(uuid.uuid4())[:8]

def makale_yukle(request):
    mesaj = None
    mesaj_tipi = "hata"

    email = request.session.get('email', None)
    if not email:
        return redirect('giris_sayfasi')

    try:
        kullanici = Kullanici.objects.get(email=email)
    except Kullanici.DoesNotExist:
        return redirect('giris_sayfasi')

    if request.method == 'POST':
        pdf_dosya = request.FILES.get('pdf_dosya')

        if not pdf_dosya:
            mesaj = "Lütfen bir PDF dosyası seçin."
        else:
            dosya_adi = pdf_dosya.name
            takip_numarasi = takip_numarasi_olustur()

            # Kullanıcıya ait klasörler
            kullanici_klasoru = os.path.join(settings.MEDIA_ROOT, f"makaleler/user_{kullanici.id}")
            anonim_klasoru = os.path.join(settings.MEDIA_ROOT, f"anonim_makaleler/user_{kullanici.id}")
            os.makedirs(kullanici_klasoru, exist_ok=True)
            os.makedirs(anonim_klasoru, exist_ok=True)

            pdf_yolu = os.path.join(kullanici_klasoru, dosya_adi)
            anonim_yolu = os.path.join(anonim_klasoru, dosya_adi)

            # ❗ Revize kontrolü: aynı dosya adına sahip ve değerlendirilmemiş eski makaleyi sil
            from .models import Makale  # emin olmak için burada da import edilebilir
            eski_makaleler = Makale.objects.filter(
                user=kullanici,
                pdf_dosya=f"makaleler/user_{kullanici.id}/{dosya_adi}",
                durum='Beklemede'
            )
            for eski in eski_makaleler:
                eski_pdf = os.path.join(settings.MEDIA_ROOT, str(eski.pdf_dosya))
                eski_anonim = os.path.join(settings.MEDIA_ROOT, str(eski.anonim_pdf_dosya))
                if os.path.exists(eski_pdf):
                    print('Eski makale bulundu siliniyor...')
                    os.remove(eski_pdf)
                if os.path.exists(eski_anonim):
                    print('Eski makale bulundu siliniyor...')
                    os.remove(eski_anonim)
                print('Eski makale etiketleri siliniyor...')    
                eski.anonim_etiketleri.all().delete()
                eski.delete()

            # Yeni dosyayı kaydet
            with open(pdf_yolu, "wb+") as destination:
                for chunk in pdf_dosya.chunks():
                    destination.write(chunk)

            # Yeni makale nesnesini oluştur
            makale = Makale.objects.create(
                user=kullanici,
                takip_numarasi=takip_numarasi,
                pdf_dosya=f"makaleler/user_{kullanici.id}/{dosya_adi}"
            )

            # Hakem ata
            konu_bilgisi = makale_konusu_belirle(pdf_yolu)
            hakem_adi = konu_bilgisi["konu"]
            try:
                hakem = Hakem.objects.get(name=hakem_adi)
                makale.hakem = hakem
                makale.save()
            except:
                pass

            print("[🔐] Anonimleştirme işlemi başlıyor...")
            try:
                anonymize_and_tag_pdf(pdf_yolu, anonim_yolu, makale)
                blur_faces(anonim_yolu, anonim_yolu)
                makale.anonim_pdf_dosya = f"anonim_makaleler/user_{kullanici.id}/{dosya_adi}"
                makale.save()

                editor = User.objects.filter(is_superuser=True).first()
                if editor:
                    log_ekle(makale, editor, f"Makale yüklendi ve anonimleştirildi. Hakem: {makale.hakem.name if makale.hakem else 'atanmadı'}")

                mesaj = f"Makaleyi başarıyla yüklediniz! Takip Numaranız: {takip_numarasi}"
                mesaj_tipi = "basarili"
            except Exception as e:
                mesaj = f"Anonimleştirme başarısız oldu: {str(e)}"
                mesaj_tipi = "hata"

    return render(request, 'makale_sistemi/makale_yukle.html', {
        'mesaj': mesaj,
        'mesaj_tipi': mesaj_tipi,
        'email': email
    })



#import logging

#logger = logging.getLogger(__name__)

def mesajlasma(request):
    return render(request, "makale_sistemi/mesajlasma.html")

def makale_goruntule(request):
    email = request.session.get("email")
    #logger.info(f"session email: {email}")
    if not email:
        return redirect('giris_sayfasi')
    try:
            kullanici = Kullanici.objects.get(email=email)
            makaleler = Makale.objects.filter(user=kullanici).order_by('yuklenme_tarihi')

            
            #logger.info(f"Kullanıcının {len(makaleler)} makalesi bulundu.")
    except Kullanici.DoesNotExist:
        return redirect('giris_sayfasi')
        
    return render(request, "makale_sistemi/makale_goruntule.html", {"makaleler":makaleler})

def ornek_sayfa3(request):
    email = request.session.get('email')
    if not email:
        return redirect('giris_sayfasi')

    makaleler = Makale.objects.filter(user__email=email, durum="Kabul Edildi")

    degerlendirme_dosyalar = []
    for makale in makaleler:
        # Etiketsiz PDF (deşifre edilmiş olan)
        dosya_adi = f"{makale.takip_numarasi}_tam.pdf"
        tam_yol = os.path.join(settings.MEDIA_ROOT, "sonuc_makaleler", dosya_adi)

        if os.path.exists(tam_yol):
            degerlendirme_dosyalar.append({
                "takip": makale.takip_numarasi,
                "tarih": makale.yuklenme_tarihi,
                "dosya_url": f"{settings.MEDIA_URL}sonuc_makaleler/{dosya_adi}"
            })

    return render(request, "makale_sistemi/ornek_sayfa3.html", {
        "degerlendirme_dosyalar": degerlendirme_dosyalar
    })


def mesajlari_getir(request):
    email = request.session.get('email')
    if not email:
        return JsonResponse({'error': 'Oturum bulunamadı'}, status=400)

    kullanici = Kullanici.objects.filter(email=email).first()
    editor = User.objects.filter(email=email, is_superuser=True).first()

    if not (kullanici or editor):
        return JsonResponse({'error': 'Geçerli kullanıcı/editor değil'}, status=400)

    if kullanici:
        mesajlar = Mesaj.objects.filter(
            Q(gonderen_kullanici=kullanici) | Q(alici_kullanici=kullanici)
        ).order_by('gonderim_tarihi')
    else:
        mesajlar = Mesaj.objects.filter(
            Q(gonderen_editor=editor) | Q(alici_editor=editor)
        ).order_by('gonderim_tarihi')

    mesaj_listesi = [
        {'gonderen': mesaj.gonderen_kullanici.email if mesaj.gonderen_kullanici else mesaj.gonderen_editor.email,
         'icerik': mesaj.icerik,
         'tarih': mesaj.gonderim_tarihi.strftime('%Y-%m-%d %H:%M:%S')}
        for mesaj in mesajlar
    ]

    return JsonResponse({'mesajlar': mesaj_listesi})





@csrf_exempt
def mesaj_gonder(request):
    if request.method == "POST":
        email = request.session.get('email')
        if not email:
            return JsonResponse({'error': 'Oturum bulunamadı'}, status=400)

        icerik = request.POST.get('icerik')
        if not icerik:
            return JsonResponse({'error': 'Mesaj içeriği boş olamaz'}, status=400)

        # Editör mü yoksa kullanıcı mı gönderiyor?
        gonderen_kullanici = Kullanici.objects.filter(email=email).first()
        gonderen_editor = User.objects.filter(email=email).first()

        editor = User.objects.filter(is_superuser=True).first()
        alici_editor = editor if gonderen_kullanici else None
        alici_kullanici = gonderen_kullanici if gonderen_editor else None

        if not (gonderen_kullanici or gonderen_editor):
            return JsonResponse({'error': 'Gönderici bulunamadı'}, status=400)

        mesaj = Mesaj.objects.create(
            gonderen_kullanici=gonderen_kullanici,
            gonderen_editor=gonderen_editor,
            alici_kullanici=alici_kullanici,
            alici_editor=alici_editor,
            konu="Genel",
            icerik=icerik
        )

        return JsonResponse({'success': 'Mesaj gönderildi'})

    return JsonResponse({'error': 'Geçersiz istek'}, status=400)




    
