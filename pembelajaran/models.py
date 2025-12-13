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
    durasi = models.IntegerField(default=10, help_text="Durasi kuis dalam menit")
    
    class Meta:
        verbose_name_plural = "Kuis"

    def __str__(self):
        return f"Kuis untuk {self.subbab.judul}"

class Pertanyaan(models.Model):
    kuis = models.ForeignKey(Kuis, on_delete=models.CASCADE, related_name="pertanyaan_set")
    
    teks_pertanyaan = RichTextField(help_text="Tulis teks pertanyaan di sini.")

    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['urutan']

    def __str__(self):
        plain_text = str(self.teks_pertanyaan).replace('<p>', '').replace('</p>', '').replace('<br>', ' ')
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
    gambar_sampul = models.ImageField(
        upload_to='game_covers/', 
        blank=True, 
        null=True, 
        help_text="Upload foto ilustrasi atau cover untuk game ini."
    )
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
    lama_pengerjaan = models.IntegerField(default=0, help_text="Lama pengerjaan dalam detik")

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

    # Helper baru untuk menampilkan format "X menit Y detik" di template/admin
    @property
    def durasi_formatted(self):
        menit = self.lama_pengerjaan // 60
        detik = self.lama_pengerjaan % 60
        if menit > 0:
            return f"{menit} menit {detik} detik"
        return f"{detik} detik"

class Latihan(models.Model):
    sub_bab = models.ForeignKey(SubBab, on_delete=models.CASCADE, related_name='list_latihan') 
    judul = models.CharField(max_length=200, verbose_name="Judul Latihan")
    deskripsi = RichTextField(help_text="Instruksi pengerjaan latihan")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.judul

    class Meta:
        verbose_name = "Latihan"
        verbose_name_plural = "Latihan"

class SoalLatihan(models.Model):
    latihan = models.ForeignKey(Latihan, on_delete=models.CASCADE, related_name='daftar_soal')
    teks_pertanyaan = RichTextField(help_text="Tulis pertanyaan latihan di sini.")
    penjelasan_jawaban = RichTextField(blank=True, help_text="Penjelasan detail jawaban.")
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Soal Latihan"
        verbose_name_plural = "Soal Latihan"
        ordering = ['urutan']

    def __str__(self):
        plain_text = str(self.teks_pertanyaan).replace('<p>', '').replace('</p>', '').replace('<br>', ' ')
        return f"{self.latihan.judul} - {plain_text[:50]}..."

class PilihanLatihan(models.Model):
    soal_latihan = models.ForeignKey(SoalLatihan, on_delete=models.CASCADE, related_name="pilihan_latihan_set")
    teks_pilihan = models.CharField(max_length=500)
    is_jawaban_benar = models.BooleanField(default=False, verbose_name="Is Jawaban Benar")

    def __str__(self):
        return self.teks_pilihan

class HasilLatihan(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hasil_latihan')
    latihan = models.ForeignKey(Latihan, on_delete=models.CASCADE, related_name='jawaban_siswa')

    file_jawaban = models.FileField(upload_to='uploads/latihan/', blank=True, null=True, verbose_name="File Jawaban")
    text_jawaban = models.TextField(blank=True, null=True, verbose_name="Jawaban Teks")
    
    nilai = models.IntegerField(default=0, verbose_name="Nilai (0-100)")
    feedback_guru = models.TextField(blank=True, null=True, verbose_name="Komentar Guru")
    tanggal_kumpul = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.latihan.judul}"

    class Meta:
        verbose_name = "Hasil Latihan"
        verbose_name_plural = "Hasil Latihan"

class SoalEvaluasi(models.Model):
    pertanyaan = models.TextField(help_text="Pertanyaan evaluasi akhir.")
    urutan = models.PositiveIntegerField(default=0, help_text="Nomor urut soal") 
    dibuat_pada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Soal Evaluasi"
        ordering = ['urutan'] 

    def __str__(self):
        return self.pertanyaan

class PilihanJawaban(models.Model):
    soal = models.ForeignKey(SoalEvaluasi, related_name='pilihan', on_delete=models.CASCADE)
    teks_pilihan = models.CharField(max_length=255)
    apakah_benar = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Pilihan Jawaban"

    def __str__(self):
        return self.teks_pilihan
    
# Model ini ada di kode kamu, tapi tidak ada di temanmu. Tetap kita pertahankan.
class HasilEvaluasi(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hasil_evaluasi')
    skor = models.IntegerField(default=0)
    total_soal = models.IntegerField(default=0)
    tanggal_mengerjakan = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Hasil Evaluasi Akhir"

    def __str__(self):
        return f"Evaluasi {self.user.username} - Skor: {self.skor}"

class PengaturanGuru(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pengaturan_guru')
    kkm_latihan = models.IntegerField(default=70, verbose_name="KKM Latihan")
    kkm_kuis = models.IntegerField(default=75, verbose_name="KKM Kuis")
    kkm_evaluasi = models.IntegerField(default=80, verbose_name="KKM Evaluasi")

    class Meta:
        verbose_name = "Pengaturan Guru"
        verbose_name_plural = "Pengaturan Guru"

    def __str__(self):
        return f"Pengaturan Guru: {self.user.username}"