from django.urls import path
from . import views
from makale_sistemi.views import makale_yukle,kullanici_sayfa,makale_sorgulama,mesajlasma,ornek_sayfa3,mesajlari_getir,mesaj_gonder,makale_goruntule,hakem_sayfasi,hakem_degerlendir

urlpatterns = [
    path('', views.giris_sayfasi, name='giris_sayfasi'),
    path('kullanici-sayfa/', kullanici_sayfa, name='kullanici_sayfa'),
    path('makale-yukle/', makale_yukle, name='makale_yukle'),
    path('makale_sorgulama/', makale_sorgulama, name='makale_sorgulama'),
     path('mesajlasma/', mesajlasma, name='mesajlasma'),
    path('ornek_sayfa3/', ornek_sayfa3, name='ornek_sayfa3'),
    path('makale-goruntule/', makale_goruntule, name='makale_goruntule'),
    path('mesajlari-getir/', mesajlari_getir, name='mesajlari_getir'),
    path('mesaj-gonder/', mesaj_gonder, name='mesaj_gonder'),
    path("hakem/<str:hakem_adi>/",hakem_sayfasi, name="hakem_sayfasi"),
    path("hakem-degerlendir/<int:makale_id>/", hakem_degerlendir, name="hakem_degerlendir"),
]