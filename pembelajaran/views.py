import csv
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from .models import (
    Bab, SubBab, Kuis, Pertanyaan, Pilihan, 
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress, StudiKasus # Pastikan StudiKasus diimport
)
from .forms import RegisterForm
from django.contrib.auth import login, authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User 
from datetime import timedelta 
from django.db.models import Prefetch, Count 

# --- UTILITY FUNCTIONS ---

def is_guru(user):
    # Mengasumsikan guru adalah pengguna yang is_staff=True
    return user.is_authenticated and user.is_staff

# Dekorator untuk membatasi akses ke view guru
guru_access = user_passes_test(is_guru, login_url='login')

def get_sidebar_context(request): 
    semua_bab = Bab.objects.prefetch_related(
        Prefetch('subbab_list', queryset=SubBab.objects.order_by('urutan'))
    ).order_by('urutan')

    completed_subbabs = set()
    if request.user.is_authenticated:
        completed_subbabs = set(UserProgress.objects.filter(
            user=request.user
        ).values_list('subbab_id', flat=True))

    return {
        'semua_bab': semua_bab,
        'completed_subbabs': completed_subbabs
    }

# --- AUTH & DASHBOARD VIEW (SISWA) ---

def halaman_dashboard(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('guru_dashboard') 
    
    konteks = {'active_page': 'dashboard'}
    return render(request, 'pembelajaran/dashboard.html', konteks)

def halaman_register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registrasi berhasil! Selamat datang.')
            if user.is_staff:
                return redirect('guru_dashboard')
            else:
                return redirect('dashboard')
        else:
            error_msg = 'Data tidak valid. Silakan periksa kembali isian Anda.'
            if form.errors:
                first_error = next(iter(form.errors.values()))
                error_msg = first_error[0]
            messages.error(request, error_msg)
    else:
        form = RegisterForm()
    
    konteks = {'form': form}
    return render(request, 'pembelajaran/register.html', konteks)

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('guru_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            if user.is_staff:
                return redirect('guru_dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'Username atau password salah. Silakan coba lagi.')
    else:
        form = AuthenticationForm()
    return render(request, 'pembelajaran/login.html', {'form': form})

# --- MATERI VIEWS ---

# Mengganti nama view lama: halaman_materi -> halaman_materi_redirect
@login_required
def halaman_materi_redirect(request):
    """Menggantikan halaman_materi lama, redirect ke jalur Materi yang baru."""
    materi_pertama = SubBab.objects.order_by('bab__urutan', 'urutan').first()
    if materi_pertama:
        # Menggunakan nama URL yang baru
        return redirect('subbab_materi', slug=materi_pertama.slug) 

    konteks = get_sidebar_context(request) 
    konteks['judul'] = "Materi Belum Tersedia"
    return render(request, 'pembelajaran/materi_kosong.html', konteks)

@login_required
def detail_materi(request, slug):
    """Menampilkan konten utama subbab. Ditempatkan di jalur .../subbab/slug/materi/"""
    konteks = get_sidebar_context(request)
    subbab_aktif = get_object_or_404(
        SubBab.objects.prefetch_related(
            'studi_kasus', 
            'kuis__pertanyaan_set__pilihan_set', 
            'game_drag_drop__item_set'
        ), 
        slug=slug
    )

    if request.user.is_authenticated:
        UserProgress.objects.get_or_create(
            user=request.user,
            subbab=subbab_aktif,
            defaults={'completed_at': timezone.now()}
        )
        konteks['completed_subbabs'].add(subbab_aktif.id)
    
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
        'active_cabang': 'materi', # <-- PENTING: Penanda cabang aktif
    })
    return render(request, 'pembelajaran/detail_materi.html', konteks)


@login_required
def detail_latihan(request, slug):
    """Menampilkan halaman latihan (Studi Kasus & Game Drag Drop) per subbab."""
    konteks = get_sidebar_context(request)
    subbab_aktif = get_object_or_404(
        SubBab.objects.prefetch_related(
            'studi_kasus', 
            'game_drag_drop__item_set'
        ), 
        slug=slug
    )
    
    konteks.update({
        'subbab': subbab_aktif,
        'studi_kasus_list': subbab_aktif.studi_kasus.all().order_by('urutan'),
        'game_drag_drop': getattr(subbab_aktif, 'game_drag_drop', None), 
        'active_slug': slug,
        'active_cabang': 'latihan', # <-- PENTING: Penanda cabang aktif
    })
    return render(request, 'pembelajaran/detail_latihan.html', konteks)


# --- KALKULATOR & LATIHAN VIEWS ---

@login_required
def kalkulator_harga_jual(request):
    konteks = {}
    konteks['active_page'] = 'kalkulator' 

    if request.method == "POST":
        try:
            biaya_tetap = float(request.POST.get("biaya_tetap", 0) or 0)
            biaya_variabel = float(request.POST.get("biaya_variabel", 0) or 0)
            jumlah_produksi = int(request.POST.get("jumlah_produksi", 0) or 0)
            markup = float(request.POST.get("markup", 0) or 0)

            if jumlah_produksi <= 0:
                konteks['error'] = "Jumlah produksi harus lebih dari 0."
                return render(request, 'pembelajaran/kalkulator.html', konteks)

            total_biaya_produksi_awal = biaya_tetap + (biaya_variabel * jumlah_produksi)
            biaya_produksi_per_unit_awal = total_biaya_produksi_awal / jumlah_produksi
            harga_jual_per_unit_awal = biaya_produksi_per_unit_awal * (1 + markup / 100)
            total_pendapatan_awal = harga_jual_per_unit_awal * jumlah_produksi
            laba_rugi_awal = total_pendapatan_awal - total_biaya_produksi_awal

            langkah = [
                f"Biaya tetap: Rp {biaya_tetap:,.0f}",
                f"Biaya variabel per unit: Rp {biaya_variabel:,.0f}",
                f"Total biaya produksi = Biaya tetap + (Biaya variabel × jumlah produksi) = "
                f"Rp {total_biaya_produksi_awal:,.0f}",
                f"Biaya produksi per unit = Total biaya produksi ÷ jumlah produksi = "
                f"Rp {biaya_produksi_per_unit_awal:,.0f}",
                f"Harga jual per unit = Biaya per unit × (1 + markup/100) - markup {markup}% = "
                f"Rp {harga_jual_per_unit_awal:,.0f}",
                f"Total pendapatan = Harga jual × jumlah produksi = Rp {total_pendapatan_awal:,.0f}",
                f"Laba / Rugi = Total pendapatan – Total biaya produksi = Rp {laba_rugi_awal:,.0f}"
            ]

            konteks.update({
                'hasil': True,

                'total_biaya_produksi': total_biaya_produksi_awal,
                'biaya_produksi_per_unit': biaya_produksi_per_unit_awal,
                'harga_jual_per_unit': harga_jual_per_unit_awal,
                'total_pendapatan': total_pendapatan_awal,
                'laba_rugi': laba_rugi_awal,

                'markup': markup,
                'langkah': langkah,

                'input_biaya_tetap': biaya_tetap,
                'input_biaya_variabel': biaya_variabel,
                'input_jumlah_produksi': jumlah_produksi,
            })

        except (ValueError, TypeError):
            konteks['error'] = 'Pastikan semua kolom diisi dengan angka yang valid.'

    return render(request, 'pembelajaran/kalkulator.html', konteks)

def _proses_hitung_kuis(request, subbab, kuis):
    semua_pertanyaan = kuis.pertanyaan_set.all()
    skor = 0
    total_soal = semua_pertanyaan.count()
    hasil_kuis = []

    for pertanyaan in semua_pertanyaan:
        jawaban_user_id = request.POST.get(f'pertanyaan_{pertanyaan.id}')
        jawaban_user = None
        jawaban_benar = pertanyaan.pilihan_set.filter(is_jawaban_benar=True).first()

        if jawaban_user_id:
            jawaban_user = pertanyaan.pilihan_set.filter(id=jawaban_user_id).first()
            is_correct = (jawaban_benar and jawaban_user and jawaban_user.id == jawaban_benar.id)
            if is_correct:
                skor += 1
        else:
            is_correct = False

        hasil_kuis.append({
            'pertanyaan': pertanyaan,
            'jawaban_user': jawaban_user,
            'jawaban_benar': jawaban_benar,
            'is_correct': is_correct,
            'penjelasan': pertanyaan.penjelasan_jawaban or "Anda tidak menjawab pertanyaan ini.",
        })

    return skor, total_soal, hasil_kuis

@login_required
# Mengubah nama fungsi untuk mencerminkan daftar Latihan/Kuis
def daftar_latihan(request):
    semua_bab = Bab.objects.prefetch_related(
        Prefetch('subbab_list', queryset=SubBab.objects.filter(kuis__isnull=False).select_related('kuis'))
    ).order_by('urutan')
    
    babs_with_kuis = [bab for bab in semua_bab if bab.subbab_list.all().exists()]
            
    konteks = {
        'semua_bab': babs_with_kuis,
        # Mengubah 'kuis' menjadi 'latihan_pemahaman' untuk penanda di navbar/menu
        'active_page': 'latihan_pemahaman', 
    }
    # Mengganti nama template
    return render(request, 'pembelajaran/daftar_latihan.html', konteks)

@login_required
def tampil_kuis(request, slug):
    """Menampilkan kuis (sekarang disebut Latihan Pemahaman). Ditempatkan di jalur .../subbab/slug/latihan-kuis/"""
    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related(
        Prefetch('pertanyaan_set', queryset=Pertanyaan.objects.order_by('urutan').prefetch_related('pilihan_set'))
    ), subbab=subbab)
    
    konteks = {
        'subbab': subbab,
        'kuis': kuis,
        # Mengubah 'kuis' menjadi 'latihan_pemahaman'
        'active_page': 'latihan_pemahaman', 
        # Mengubah 'kuis' menjadi 'latihan_kuis' (sesuai penanda di base.html)
        'active_cabang': 'latihan_kuis', 
    }
    # Mengganti nama template
    return render(request, 'pembelajaran/latihan_kuis.html', konteks)

@login_required
def hitung_kuis(request, slug):
    """Memproses hasil kuis (sekarang hasil Latihan Pemahaman). Ditempatkan di jalur .../subbab/slug/latihan-kuis/submit/"""
    if request.method != 'POST':
        # Menggunakan nama URL yang baru: 'subbab_latihan_kuis'
        return redirect('subbab_latihan_kuis', slug=slug)

    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related('pertanyaan_set__pilihan_set'), subbab=subbab)
    
    skor, total_soal, hasil_kuis = _proses_hitung_kuis(request, subbab, kuis)

    if request.user.is_authenticated and total_soal > 0:
        HasilKuis.objects.update_or_create(
            user=request.user,
            kuis=kuis,
            defaults={
                'skor': skor,
                'total_soal': total_soal,
                'tanggal_mengerjakan': timezone.now()
            }
        )

    konteks = {
        'subbab': subbab,
        'skor': skor,
        'total_soal': total_soal,
        'hasil_kuis': hasil_kuis,
        'setengah_soal': total_soal / 2, 
        # Mengubah 'kuis' menjadi 'latihan_pemahaman'
        'active_page': 'latihan_pemahaman', 
    }
    # Mengganti nama template
    return render(request, 'pembelajaran/hasil_latihan.html', konteks)

# ----------------------------------------------------
# --- VIEW KHUSUS GURU (IS_STAFF=TRUE) ---
# ----------------------------------------------------

@login_required
@guru_access
def guru_dashboard(request):
    # Dapatkan jumlah total siswa (non-staff)
    total_siswa = User.objects.filter(is_staff=False).count() 
    
    konteks = {
        'active_page': 'guru_dashboard',
        'total_siswa': total_siswa,
        'judul': 'Dashboard Guru'
    }
    return render(request, 'pembelajaran/guru/guru_dashboard.html', konteks)

@login_required
@guru_access
def guru_cek_nilai(request):
    # Contoh data siswa (non-staff) untuk ditampilkan
    semua_siswa = User.objects.filter(is_staff=False).order_by('username')
    
    konteks = {
        'active_page': 'guru_cek_nilai',
        'semua_siswa': semua_siswa,
        # Mengubah judul
        'judul': 'Cek Nilai Latihan Siswa'
    }
    return render(request, 'pembelajaran/guru/guru_cek_nilai.html', konteks)

@login_required
@guru_access
def guru_download_nilai_csv(request):
    # Menginisialisasi response untuk file CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="nilai_siswa_{}.csv"'.format(
        timezone.now().strftime("%Y%m%d_%H%M%S")
    )

    writer = csv.writer(response)
    # Header CSV
    # Mengubah "Total Kuis Selesai" menjadi "Total Latihan Selesai"
    writer.writerow(['ID Siswa', 'Username', 'Total Latihan Selesai', 'Skor Rata-rata']) 
    
    # Placeholder logika: Ambil data nilai siswa (non-staff)
    siswa_data = User.objects.filter(is_staff=False).annotate(
        kuis_selesai=Count('hasilkuis') # Menghitung jumlah kuis yang pernah dikerjakan (nama variable kuis_selesai dipertahankan karena merujuk ke HasilKuis model)
    )
    for user in siswa_data:
        # PENTING: Anda harus menghitung skor rata-rata dari HasilKuis di sini.
        writer.writerow([user.id, user.username, user.kuis_selesai, 'N/A (Perlu hitung rata-rata)']) 
    
    return response

@login_required
@guru_access
def guru_detail_siswa(request, user_id):
    siswa = get_object_or_404(User, id=user_id, is_staff=False)
    # Logika: Ambil semua HasilKuis dan UserProgress siswa ini
    
    konteks = {
        'active_page': 'guru_cek_nilai',
        'siswa': siswa,
        'judul': f'Detail Siswa: {siswa.username}'
    }
    return render(request, 'pembelajaran/guru/guru_detail_siswa.html', konteks)

@login_required
@guru_access
def guru_kelola_materi(request):
    konteks = {
        'active_page': 'guru_kelola_materi',
        'judul': 'Kelola Materi'
    }
    return render(request, 'pembelajaran/guru/guru_kelola_materi.html', konteks)

@login_required
@guru_access
def guru_pengumuman(request):
    konteks = {
        'active_page': 'guru_pengumuman',
        'judul': 'Pengumuman'
    }
    return render(request, 'pembelajaran/guru/guru_pengumuman.html', konteks)

@login_required
@guru_access
def guru_pengaturan(request):
    konteks = {
        'active_page': 'guru_pengaturan',
        'judul': 'Pengaturan Akun Guru'
    }
    return render(request, 'pembelajaran/guru/guru_pengaturan.html', konteks)

@login_required
@guru_access
def guru_riwayat(request):
    konteks = {
        'active_page': 'guru_riwayat',
        'judul': 'Riwayat Aktivitas'
    }
    return render(request, 'pembelajaran/guru/guru_riwayat.html', konteks)