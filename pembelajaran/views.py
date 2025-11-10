# pembelajaran/views.py

from django.shortcuts import render, get_object_or_404, redirect
# Impor model sudah lengkap
from .models import (
    Bab, SubBab, Kuis, Pertanyaan, Pilihan, 
    GameDragDrop, ItemDragDrop
)
from .forms import RegisterForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def get_sidebar_context():
    # Fungsi ini tetap diperlukan untuk detail_materi dan kalkulator
    return {'semua_bab': Bab.objects.prefetch_related('subbab_list').all()}

# ----------------------------------------
# VIEW PUBLIK (DASHBOARD & REGISTRASI)
# ----------------------------------------

def halaman_dashboard(request):
    konteks = {'active_page': 'dashboard'}
    return render(request, 'pembelajaran/dashboard.html', konteks)

def halaman_register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registrasi berhasil! Selamat datang.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Data tidak valid. Silakan periksa kembali isian Anda.')
    else:
        form = RegisterForm()
    
    konteks = {'form': form}
    return render(request, 'pembelajaran/register.html', konteks)

# ----------------------------------------
# VIEW YANG DILINDUNGI (PERLU LOGIN)
# ----------------------------------------

@login_required
def halaman_materi(request):
    materi_pertama = SubBab.objects.order_by('bab__urutan', 'urutan').first()
    if materi_pertama:
        return redirect('detail_materi', slug=materi_pertama.slug)

    konteks = get_sidebar_context()
    konteks['judul'] = "Materi Belum Tersedia"
    return render(request, 'pembelajaran/materi_kosong.html', konteks)

@login_required
def detail_materi(request, slug):
    """
    View ini sudah benar dan memuat data game.
    """
    konteks = get_sidebar_context()
    subbab_aktif = get_object_or_404(
        SubBab.objects.prefetch_related(
            'studi_kasus', 
            'kuis', 
            'game_drag_drop__item_set'
        ), 
        slug=slug
    )
    
    semua_subbab_list = list(SubBab.objects.order_by('bab__urutan', 'urutan'))
    try:
        current_index = semua_subbab_list.index(subbab_aktif)
        prev_subbab = semua_subbab_list[current_index - 1] if current_index > 0 else None
        next_subbab = semua_subbab_list[current_index + 1] if current_index < len(semua_subbab_list) - 1 else None
    except ValueError:
        prev_subbab = None
        next_subbab = None

    konteks.update({
        'subbab': subbab_aktif,
        'active_slug': slug,
        'prev_subbab': prev_subbab,
        'next_subbab': next_subbab,
    })
    return render(request, 'pembelajaran/detail_materi.html', konteks)

@login_required
def kalkulator_harga_jual(request):
    """
    View ini sudah benar.
    """
    konteks = get_sidebar_context()
    konteks['active_page'] = 'kalkulator' 

    if request.method == "POST":
        try:
            biaya_tetap = float(request.POST.get("biaya_tetap", 0))
            biaya_variabel = float(request.POST.get("biaya_variabel", 0))
            jumlah_produksi = int(request.POST.get("jumlah_produksi", 0))
            markup = float(request.POST.get("markup", 0))
            if jumlah_produksi == 0:
                konteks['error'] = "Jumlah produksi tidak boleh 0."
                return render(request, 'pembelajaran/kalkulator.html', konteks)
            total_biaya_produksi = biaya_tetap + (biaya_variabel * jumlah_produksi)
            biaya_produksi_per_unit = total_biaya_produksi / jumlah_produksi
            harga_jual_per_unit = biaya_produksi_per_unit * (1 + markup / 100)
            total_pendapatan = harga_jual_per_unit * jumlah_produksi
            laba_rugi = total_pendapatan - total_biaya_produksi
            langkah = [
                f"Total biaya produksi = {biaya_tetap} + ({biaya_variabel} × {jumlah_produksi}) = {total_biaya_produksi}",
                f"Biaya produksi per barang = {total_biaya_produksi} ÷ {jumlah_produksi} = {biaya_produksi_per_unit}",
                f"Harga jual per barang = {biaya_produksi_per_unit} × (1 + {markup}/100) = {harga_jual_per_unit}",
                f"Total pendapatan = {harga_jual_per_unit} × {jumlah_produksi} = {total_pendapatan}",
                f"Keuntungan atau kerugian = {total_pendapatan} - {total_biaya_produksi} = {laba_rugi}"
            ]
            konteks.update({
                'hasil': True, 'total_biaya_produksi': total_biaya_produksi,
                'biaya_produksi_per_unit': biaya_produksi_per_unit, 'harga_jual_per_unit': harga_jual_per_unit,
                'total_pendapatan': total_pendapatan, 'laba_rugi': laba_rugi,
                'markup': markup, 'langkah': langkah
            })
        except (ValueError, TypeError, ZeroDivisionError):
             konteks['error'] = 'Pastikan semua kolom diisi dengan angka yang valid.'
             
    return render(request, 'pembelajaran/kalkulator.html', konteks)

# ----------------------------------------
# FUNGSI HELPER UNTUK LOGIKA KUIS
# ----------------------------------------

def _proses_hitung_kuis(request, subbab, kuis):
    """Fungsi helper internal untuk memproses hasil kuis."""
    semua_pertanyaan = kuis.pertanyaan_set.all()
    skor = 0
    total_soal = semua_pertanyaan.count()
    hasil_kuis = []

    for pertanyaan in semua_pertanyaan:
        jawaban_user_id = request.POST.get(f'pertanyaan_{pertanyaan.id}')
        jawaban_benar = None
        jawaban_user = None

        try:
            jawaban_benar = pertanyaan.pilihan_set.get(is_jawaban_benar=True)
        except Pilihan.DoesNotExist:
            continue 

        is_correct = False
        if jawaban_user_id and int(jawaban_user_id) == jawaban_benar.id:
            skor += 1
            is_correct = True
        
        if jawaban_user_id:
            try:
                jawaban_user = pertanyaan.pilihan_set.get(id=jawaban_user_id)
            except Pilihan.DoesNotExist:
                jawaban_user = None

        hasil_kuis.append({
            'pertanyaan': pertanyaan, 'jawaban_user': jawaban_user,
            'jawaban_benar': jawaban_benar, 'is_correct': is_correct,
            'penjelasan': pertanyaan.penjelasan_jawaban,
        })
    
    return skor, total_soal, hasil_kuis

# ----------------------------------------
# VIEW KUIS (VERSI FINAL - STANDALONE)
# ----------------------------------------

@login_required
def daftar_kuis(request):
    """
    Menampilkan semua Kuis yang tersedia (standalone).
    """
    semua_bab = Bab.objects.prefetch_related('subbab_list__kuis').order_by('urutan')
    
    babs_with_kuis = []
    for bab in semua_bab:
        has_kuis = any(hasattr(subbab, 'kuis') for subbab in bab.subbab_list.all())
        if has_kuis:
            babs_with_kuis.append(bab)
            
    konteks = {
        'semua_bab': babs_with_kuis,
        'active_page': 'kuis', 
    }
    return render(request, 'pembelajaran/daftar_kuis.html', konteks)

@login_required
def tampil_kuis(request, slug):
    """
    **PERBAIKAN:** View ini sekarang menjadi standalone (tanpa sidebar).
    """
    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related('pertanyaan_set__pilihan_set'), subbab=subbab)
    
    # Konteks baru tanpa sidebar
    konteks = {
        'subbab': subbab,
        'kuis': kuis,
        'active_page': 'kuis', # Untuk highlight top-nav
    }
    # Render template 'kuis.html' (yang merupakan versi standalone)
    return render(request, 'pembelajaran/kuis.html', konteks)

@login_required
def hitung_kuis(request, slug):
    """
    **PERBAIKAN:** View ini sekarang menjadi standalone (tanpa sidebar).
    """
    if request.method != 'POST':
        return redirect('tampil_kuis', slug=slug)

    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related('pertanyaan_set__pilihan_set'), subbab=subbab)
    
    # Memanggil helper
    skor, total_soal, hasil_kuis = _proses_hitung_kuis(request, subbab, kuis)

    # Konteks baru tanpa sidebar
    konteks = {
        'subbab': subbab,
        'skor': skor,
        'total_soal': total_soal,
        'hasil_kuis': hasil_kuis,
        'active_page': 'kuis', # Untuk highlight top-nav
    }
    # Render template 'hasil_kuis.html' (yang merupakan versi standalone)
    return render(request, 'pembelajaran/hasil_kuis.html', konteks)