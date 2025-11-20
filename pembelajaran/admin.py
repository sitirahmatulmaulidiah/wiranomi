from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget
from .models import (
    Bab, SubBab, StudiKasus, Kuis, Pertanyaan, Pilihan,
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress
)

class StudiKasusInlineForm(forms.ModelForm):
    kasus = forms.CharField(widget=CKEditorWidget(), label="Kasus")
    pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Pertanyaan")
    pembahasan = forms.CharField(widget=CKEditorWidget(), label="Pembahasan")
    class Meta:
        model = StudiKasus
        fields = '__all__'

class PertanyaanAdminForm(forms.ModelForm):
    teks_pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Teks Pertanyaan")
    penjelasan_jawaban = forms.CharField(widget=CKEditorWidget(), required=False, label="Penjelasan Jawaban")
    class Meta:
        model = Pertanyaan
        fields = '__all__'

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

class GameDragDropInline(admin.StackedInline):
    model = GameDragDrop
    extra = 1
    classes = ['collapse']
    verbose_name_plural = "Game Drag & Drop"

class ItemDragDropInline(admin.TabularInline):
    model = ItemDragDrop
    extra = 1
    fields = ('teks_item', 'gambar_item', 'is_kategori_benar')

@admin.register(SubBab)
class SubBabAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('judul',)}
    list_display = ('judul', 'bab', 'urutan')
    list_filter = ('bab',)
    search_fields = ['judul']
    inlines = [StudiKasusInline, KuisInline, GameDragDropInline] 

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

admin.site.register(Kuis)