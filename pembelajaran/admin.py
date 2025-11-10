# pembelajaran/admin.py
from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget

# 1. Impor model baru
from .models import (
    Bab, SubBab, StudiKasus, Kuis, Pertanyaan, Pilihan,
    GameDragDrop, ItemDragDrop 
)

# ... (Form StudiKasusInlineForm dan PertanyaanAdminForm tetap sama) ...
class StudiKasusInlineForm(forms.ModelForm):
    kasus = forms.CharField(widget=CKEditorWidget(), label="Kasus")
    pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Pertanyaan")
    pembahasan = forms.CharField(widget=CKEditorWidget(), label="Pembahasan")
    class Meta:
        model = StudiKasus
        fields = '__all__'

class PertanyaanAdminForm(forms.ModelForm):
    teks_pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Teks Pertanyaan")
    penjelasan_jawaban = forms.CharField(widget=CKEditorWidget(), label="Penjelasan Jawaban")
    class Meta:
        model = Pertanyaan
        fields = '__all__'

# --- Inlines untuk Kuis & Studi Kasus (Tetap sama) ---
class PilihanInline(admin.TabularInline):
    model = Pilihan
    extra = 1

class KuisInline(admin.StackedInline):
    model = Kuis
    extra = 1
    classes = ['collapse']
    verbose_name_plural = "Kuis Pemahaman"

class StudiKasusInline(admin.StackedInline):
    model = StudiKasus
    form = StudiKasusInlineForm
    extra = 1
    fields = ('judul', 'kasus', 'pertanyaan', 'pembahasan', 'urutan')
    verbose_name_plural = "Daftar Studi Kasus"
    classes = ['collapse']

# ----------------------------------------------------------
# 🚀 INLINE BARU UNTUK GAME DRAG & DROP
# ----------------------------------------------------------
class GameDragDropInline(admin.StackedInline):
    model = GameDragDrop
    extra = 1
    classes = ['collapse']
    verbose_name_plural = "Game Drag & Drop"

class ItemDragDropInline(admin.TabularInline):
    model = ItemDragDrop
    extra = 1
    fields = ('teks_item', 'gambar_item', 'is_kategori_benar')

# ----------------------------------------------------------
# KONFIGURASI HALAMAN SUB-BAB DI ADMIN (DIPERBARUI)
# ----------------------------------------------------------
class SubBabAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('judul',)}
    list_display = ('judul', 'bab', 'urutan')
    list_filter = ('bab',)
    search_fields = ['judul']
    # 2. Tambahkan GameDragDropInline di sini
    inlines = [StudiKasusInline, KuisInline, GameDragDropInline] 

# ... (BabAdmin tetap sama) ...
class BabAdmin(admin.ModelAdmin):
    list_display = ('judul', 'urutan')

# ----------------------------------------------------------
# KONFIGURASI HALAMAN PERTANYAAN (DIPERBARUI)
# ----------------------------------------------------------
class PertanyaanAdmin(admin.ModelAdmin):
    form = PertanyaanAdminForm  
    model = Pertanyaan
    inlines = [PilihanInline]
    list_display = ('teks_pertanyaan', 'kuis')
    list_filter = ('kuis__subbab__bab', 'kuis__subbab')
    search_fields = ['teks_pertanyaan']

# ----------------------------------------------------------
# 🚀 KONFIGURASI BARU UNTUK HALAMAN GAME
# ----------------------------------------------------------
# Ini adalah halaman admin terpisah untuk mengedit Game dan menambah Item-nya
class GameDragDropAdmin(admin.ModelAdmin):
    model = GameDragDrop
    inlines = [ItemDragDropInline]
    list_display = ('judul', 'subbab')
    list_filter = ('subbab__bab',)

# ----------------------------------------------------------
# PENDAFTARAN MODEL KE HALAMAN ADMIN
# ----------------------------------------------------------
admin.site.register(SubBab, SubBabAdmin) 
admin.site.register(Bab, BabAdmin)       
admin.site.register(Kuis)

# 3. Hapus dan daftar ulang Pertanyaan
try:
    admin.site.unregister(Pertanyaan)
except admin.sites.NotRegistered:
    pass
admin.site.register(Pertanyaan, PertanyaanAdmin)

# 4. Daftarkan model Game baru
admin.site.register(GameDragDrop, GameDragDropAdmin)