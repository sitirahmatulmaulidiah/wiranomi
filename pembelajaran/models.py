from django.db import models
from django.urls import reverse
from ckeditor.fields import RichTextField
from django.contrib.auth.models import User 
from django.utils import timezone 

class Bab(models.Model):
    judul = models.CharField(max_length=200)
    urutan = models.PositiveIntegerField(default=0, help_text="Nomor urut untuk sorting")

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        return self.judul


class SubBab(models.Model):
    bab = models.ForeignKey(Bab, related_name='subbab_list', on_delete=models.CASCADE)
    judul = models.CharField(max_length=200)
    slug = models.SlugField(
        unique=True,
        help_text="Teks unik untuk URL, misalnya 'perhitungan-harga-jual'"
    )
    konten = RichTextField(help_text="Isi materi di sini") 
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        return self.judul

    def get_absolute_url(self):
        return reverse('detail_materi', kwargs={'slug': self.slug})


class StudiKasus(models.Model):
    subbab = models.ForeignKey(SubBab, related_name='studi_kasus', on_delete=models.CASCADE)
    judul = models.CharField(max_length=255, default="Studi Kasus")
    kasus = RichTextField(help_text="Jelaskan situasi atau masalah dalam studi kasus.")
    pertanyaan = RichTextField(help_text="Tuliskan pertanyaan yang harus dijawab oleh pengguna.")
    pembahasan = RichTextField(help_text="Jelaskan pembahasan atau jawaban dari studi kasus.")
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['urutan']
        verbose_name_plural = "Studi Kasus"

    def __str__(self):
        return f"{self.judul} - {self.subbab.judul}"
    

class Kuis(models.Model):
    subbab = models.OneToOneField(SubBab, on_delete=models.CASCADE, related_name="kuis")
    judul = models.CharField(max_length=255, default="Kuis Pemahaman")
    
    class Meta:
        verbose_name_plural = "Kuis"

    def __str__(self):
        return f"Kuis untuk {self.subbab.judul}"

class Pertanyaan(models.Model):
    kuis = models.ForeignKey(Kuis, on_delete=models.CASCADE, related_name="pertanyaan_set")
    
    teks_pertanyaan = RichTextField(help_text="Tulis teks pertanyaan di sini.")
    penjelasan_jawaban = RichTextField(blank=True, help_text="Penjelasan detail mengapa jawaban ini benar/salah.")

    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        plain_text = self.teks_pertanyaan.replace('<p>', '').replace('</p>', '').replace('<br>', ' ')
        return (plain_text[:75] + '...') if len(plain_text) > 75 else plain_text

class Pilihan(models.Model):
    pertanyaan = models.ForeignKey(Pertanyaan, on_delete=models.CASCADE, related_name="pilihan_set")
    teks_pilihan = models.CharField(max_length=500)
    is_jawaban_benar = models.BooleanField(default=False)

    def __str__(self):
        return self.teks_pilihan

class GameDragDrop(models.Model):
    """Model ini merepresentasikan satu game interaktif per SubBab."""
    subbab = models.OneToOneField(SubBab, on_delete=models.CASCADE, related_name="game_drag_drop")
    judul = models.CharField(max_length=255, default="Game Interaktif: Sortir Biaya")
    instruksi = models.TextField(default="Tarik dan lepas setiap item ke kategori yang benar.")
    nama_kategori_benar = models.CharField(max_length=100, default="Biaya Tetap")
    nama_kategori_salah = models.CharField(max_length=100, default="Bukan Biaya Tetap")

    class Meta:
        verbose_name_plural = "Game Drag & Drop"

    def __str__(self):
        return self.judul

class ItemDragDrop(models.Model):
    """Model ini merepresentasikan satu item yang bisa di-drag."""
    game = models.ForeignKey(GameDragDrop, on_delete=models.CASCADE, related_name="item_set")
    teks_item = models.CharField(max_length=100)
    gambar_item = models.ImageField(upload_to='game_items/', blank=True, null=True, 
                                    help_text="Opsional. Gambar untuk item (misal: foto tepung).")
    is_kategori_benar = models.BooleanField(default=True, 
                                            help_text="Centang jika ini termasuk 'Kategori Benar' (misal: Biaya Tetap)")
    
    class Meta:
        ordering = ['teks_item']

    def __str__(self):
        return self.teks_item

class UserProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subbab = models.ForeignKey(SubBab, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'subbab') 

    def __str__(self):
        return f"{self.user.username} - {self.subbab.judul}"

class HasilKuis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hasil_kuis")
    kuis = models.ForeignKey(Kuis, on_delete=models.CASCADE, related_name="hasil_user")
    skor = models.PositiveIntegerField(default=0)
    total_soal = models.PositiveIntegerField(default=0)
    tanggal_mengerjakan = models.DateTimeField(default=timezone.now) 

    class Meta:
        verbose_name_plural = "Hasil Kuis"
        ordering = ['-tanggal_mengerjakan']
        unique_together = ('user', 'kuis') 

    def __str__(self):
        return f"Hasil {self.user.username} - {self.kuis.judul}"

    @property
    def persentase(self):
        if self.total_soal > 0:
            return (self.skor / self.total_soal) * 100
        return 0