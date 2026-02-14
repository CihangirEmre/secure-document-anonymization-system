from django.contrib import admin
from .models import Kullanici, Hakem, Makale, Degerlendirme, Mesaj, AnonimleştirmeLog,AnonimEtiket
from django.utils.html import format_html
from .utilsd import decrypt_aes  # decrypt fonksiyonunu çağır


admin.site.register(Kullanici)
admin.site.register(Hakem)
#admin.site.register(Makale)
admin.site.register(Degerlendirme)
admin.site.register(Mesaj)
admin.site.register(AnonimleştirmeLog)



@admin.register(AnonimEtiket)
class AnonimEtiketAdmin(admin.ModelAdmin):
    list_display = ("makale", "tag", "category", "cozulmus_veri", "created_at")
    list_filter = ("category", "makale")
    search_fields = ("tag", "encrypted")

    def cozulmus_veri(self, obj):
        try:
            return decrypt_aes(obj.encrypted)
        except Exception:
            return format_html("<span style='color:red;'>Çözülemedi</span>")

    cozulmus_veri.short_description = "Çözümlenmiş Bilgi"

@admin.register(Makale)
class MakaleAdmin(admin.ModelAdmin):
    list_display = ("takip_numarasi", "user", "hakem")
    readonly_fields = ("pdf_onizleme", "anonim_etiketler", "log_gecmisi")

    def pdf_onizleme(self, obj):
        if obj.anonim_pdf_dosya:
            return format_html(
                f'<iframe src="{obj.anonim_pdf_dosya.url}" width="250%" height="600px"></iframe>'
            )
        return "PDF bulunamadı"
    pdf_onizleme.short_description = "PDF Önizleme"

    def anonim_etiketler(self, obj):
        etiketler = AnonimEtiket.objects.filter(makale=obj).order_by("category")
        if not etiketler.exists():
            return "Bu makale için anonimleştirilmiş veri yok."
        
        html = ""
        for kategori in ["ISIM", "EMAIL", "KURUM"]:
            html += f"<h4>{kategori} Bilgileri:</h4><ul>"
            for etiket in etiketler.filter(category=kategori):
                try:
                    cozulmus = decrypt_aes(etiket.encrypted)
                except:
                    cozulmus = "<span style='color:red;'>Çözülemiyor</span>"
                html += f"<li>{etiket.tag} → <b>{cozulmus}</b></li>"
            html += "</ul>"
        return format_html(html)
    anonim_etiketler.short_description = "Anonimleştirilmiş Bilgiler"

    def log_gecmisi(self, obj):
        loglar = obj.anonimlestirme_loglari.all().order_by('-islem_tarihi')
        if not loglar.exists():
            return "Bu makale için işlem geçmişi bulunamadı."

        html = "<ul>"
        for log in loglar:
            html += f"<li>{log.islem_tarihi.strftime('%Y-%m-%d %H:%M')} - <b>{log.editor.username}</b>: {log.yapilan_islem}</li>"
        html += "</ul>"
        return format_html(html)

    log_gecmisi.short_description = "İşlem Geçmişi"

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.contrib.auth.models import User
from .models import Mesaj, Kullanici


class MesajAdmin(admin.ModelAdmin):
    list_display = ("gonderen", "alici", "konu", "gonderim_tarihi")
    readonly_fields = ("gonderen", "alici", "konu", "icerik", "gonderim_tarihi")
    fields = ("gonderen", "alici", "konu", "icerik", "gonderim_tarihi")
    change_form_template = "admin/mesaj_cevapla.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<int:mesaj_id>/cevapla/", self.admin_site.admin_view(self.cevapla_view), name="mesaj_cevapla")
        ]
        return custom_urls + urls
    
    def gonderen(self, obj):
        if obj.gonderen_kullanici:
            return obj.gonderen_kullanici.email
        elif obj.gonderen_editor:
            return obj.gonderen_editor.email
        return "(Gönderen yok)"

    def alici(self, obj):
        if obj.alici_kullanici:
            return obj.alici_kullanici.email
        elif obj.alici_editor:
            return obj.alici_editor.email
        return "(Alıcı yok)"



    def cevapla_view(self, request, mesaj_id):
        mesaj = Mesaj.objects.get(id=mesaj_id)

        if request.method == "POST":
            icerik = request.POST.get("icerik")
            if icerik:
                editor = request.user

            # Hedef kullanıcıyı belirle
                hedef_kullanici = mesaj.gonderen_kullanici or mesaj.alici_kullanici

                if not hedef_kullanici:
                    self.message_user(request, "Cevaplanacak kullanıcı bulunamadı.", level="error")
                    return HttpResponseRedirect("../../")

                if not isinstance(editor, User):
                    self.message_user(request, "Geçersiz editör kullanıcısı!", level="error")
                    return HttpResponseRedirect("../../")

            # Mesaj oluştur (doğru alanları belirt)
                Mesaj.objects.create(
                    gonderen_editor=editor,                 # editör bu mesajı gönderiyor
                    alici_kullanici=hedef_kullanici,        # hedef kullanıcıya gönderiliyor
                    gonderen_kullanici=None,                # explicitly null
                    alici_editor=None,                      # explicitly null
                    konu=f"Cevap: {mesaj.konu or 'Genel'}",
                    icerik=icerik
                )

                self.message_user(request, "Cevap başarıyla gönderildi.")
                return HttpResponseRedirect("../../")

        context = dict(
            self.admin_site.each_context(request),
            mesaj=mesaj,
            orijinal_konu=mesaj.konu or "Genel",
        )
        return TemplateResponse(request, "admin/mesaj_cevapla.html", context)






admin.site.unregister(Mesaj)
admin.site.register(Mesaj, MesajAdmin)




