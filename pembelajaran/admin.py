# pembelajaran/admin.py

from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import (
    Bab, SubBab, StudiKasus, Kuis, Pertanyaan, Pilihan,
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress,
    Latihan, HasilLatihan, SoalLatihan, PilihanLatihan,
    SoalEvaluasi, PilihanJawaban # <-- Import Model Evaluasi Baru
)

# --- FORM CUSTOM (Agar menggunakan CKEditor) ---

class StudiKasusInlineForm(forms.ModelForm):
    kasus = forms.CharField(widget=CKEditorWidget(), label="Kasus")
    pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Pertanyaan")
    pembahasan = forms.CharField(widget=CKEditorWidget(), label="Pembahasan")
    class Meta:
        model = StudiKasus
        fields = '__all__'

class PertanyaanAdminForm(forms.ModelForm):
    teks_pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Teks Pertanyaan")
    class Meta:
        model = Pertanyaan
        fields = '__all__'

class LatihanAdminForm(forms.ModelForm):
    deskripsi = forms.CharField(widget=CKEditorWidget(), label="Instruksi Latihan")
    class Meta:
        model = Latihan
        fields = '__all__'

class SoalLatihanAdminForm(forms.ModelForm):
    teks_pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Teks Pertanyaan")
    penjelasan_jawaban = forms.CharField(widget=CKEditorWidget(), required=False, label="Penjelasan Jawaban")
    class Meta:
        model = SoalLatihan
        fields = '__all__'

# Form Baru untuk Evaluasi Akhir (Agar pertanyaan pakai CKEditor juga)
class SoalEvaluasiAdminForm(forms.ModelForm):
    pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Pertanyaan Evaluasi")
    class Meta:
        model = SoalEvaluasi
        fields = '__all__'

# --- INLINE MODELS (Tampilan bersarang) ---

class PilihanInline(admin.TabularInline):
    model = Pilihan
    extra = 1

# Inline Baru untuk Pilihan Ganda Latihan (A, B, C, D)
class PilihanLatihanInline(admin.TabularInline):
    model = PilihanLatihan
    extra = 4  # Menampilkan 4 baris kosong default
    verbose_name = "Pilihan Jawaban"
    verbose_name_plural = "Pilihan Ganda"

# Inline Baru untuk Pilihan Jawaban Evaluasi Akhir
class PilihanJawabanInline(admin.TabularInline):
    model = PilihanJawaban
    extra = 4
    verbose_name = "Opsi Jawaban"
    verbose_name_plural = "Pilihan Jawaban (A, B, C, D)"

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

class GameDragDropInline(admin.StackedInline):
    model = GameDragDrop
    extra = 1
    classes = ['collapse']
    verbose_name_plural = "Game Drag & Drop"

class ItemDragDropInline(admin.TabularInline):
    model = ItemDragDrop
    extra = 1
    fields = ('teks_item', 'gambar_item', 'is_kategori_benar')

# Inline agar Latihan bisa dibuat saat edit SubBab
class LatihanInline(admin.StackedInline):
    model = Latihan
    form = LatihanAdminForm
    extra = 1
    classes = ['collapse']
    verbose_name_plural = "Latihan / Tugas"

# --- ADMIN REGISTRATION ---

@admin.register(SubBab)
class SubBabAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('judul',)}
    list_display = ('judul', 'bab', 'urutan')
    list_filter = ('bab',)
    search_fields = ['judul']
    inlines = [StudiKasusInline, LatihanInline, KuisInline, GameDragDropInline] 

@admin.register(Bab)
class BabAdmin(admin.ModelAdmin):
    list_display = ('judul', 'urutan')

@admin.register(Pertanyaan)
class PertanyaanAdmin(admin.ModelAdmin):
    form = PertanyaanAdminForm  
    model = Pertanyaan
    inlines = [PilihanInline]
    list_display = ('__str__', 'kuis')
    list_filter = ('kuis__subbab__bab', 'kuis__subbab')
    search_fields = ['teks_pertanyaan']

@admin.register(GameDragDrop)
class GameDragDropAdmin(admin.ModelAdmin):
    model = GameDragDrop
    inlines = [ItemDragDropInline]
    list_display = ('judul', 'subbab')
    list_filter = ('subbab__bab',)

@admin.register(HasilKuis)
class HasilKuisAdmin(admin.ModelAdmin):
    list_display = ('user', 'kuis', 'skor', 'total_soal', 'tanggal_mengerjakan', 'persentase')
    list_filter = ('kuis__subbab__bab', 'user')
    search_fields = ('user__username', 'kuis__judul')

@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'subbab', 'completed_at')
    list_filter = ('user',)

# --- ADMIN UNTUK LATIHAN, SOAL & HASIL ---

@admin.register(Latihan)
class LatihanAdmin(admin.ModelAdmin):
    form = LatihanAdminForm 
    list_display = ('judul', 'sub_bab', 'created_at')
    search_fields = ('judul', 'deskripsi')
    list_filter = ('sub_bab',)

@admin.register(SoalLatihan)
class SoalLatihanAdmin(admin.ModelAdmin):
    form = SoalLatihanAdminForm      
    inlines = [PilihanLatihanInline] 
    list_display = ('__str__', 'latihan', 'urutan')
    list_filter = ('latihan',)
    search_fields = ('teks_pertanyaan',)

@admin.register(HasilLatihan)
class HasilLatihanAdmin(admin.ModelAdmin):
    list_display = ('user', 'latihan', 'nilai', 'tanggal_kumpul')
    list_filter = ('latihan', 'tanggal_kumpul')
    search_fields = ('user__username', 'latihan__judul')
    readonly_fields = ('tanggal_kumpul',)

# --- ADMIN BARU UNTUK EVALUASI AKHIR ---

@admin.register(SoalEvaluasi)
class SoalEvaluasiAdmin(admin.ModelAdmin):
    form = SoalEvaluasiAdminForm  # Menggunakan CKEditor
    inlines = [PilihanJawabanInline] # Pilihan Ganda di bawahnya
    list_display = ('pertanyaan_short', 'dibuat_pada')
    search_fields = ('pertanyaan',)

    # Helper untuk memendekkan tampilan pertanyaan di list admin
    def pertanyaan_short(self, obj):
        import html
        clean_text = html.unescape(obj.pertanyaan).replace('<p>', '').replace('</p>', '')
        return (clean_text[:75] + '...') if len(clean_text) > 75 else clean_text
    pertanyaan_short.short_description = "Pertanyaan"

admin.site.register(Kuis)