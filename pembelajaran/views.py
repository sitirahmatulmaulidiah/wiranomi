import csv
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from .models import (
    Bab, SubBab, Kuis, Pertanyaan, Pilihan, 
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress 
)
from .forms import RegisterForm
from django.contrib.auth import login, authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User 
from django.utils import timezone 
from datetime import timedelta 
from django.db.models import Prefetch

def get_sidebar_context(request):
    """Mengambil konteks sidebar (daftar bab dan sub-bab)"""
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

def halaman_dashboard(request):
    """Menampilkan halaman dashboard publik."""
    
    # --- INI ADALAH PERBAIKANNYA ---
    # Jika pengguna yang login adalah guru, arahkan ke dashboard guru
    if request.user.is_authenticated and request.user.is_staff:
        # Error sebelumnya: 'halaman_guru'
        # Perbaikan:
        return redirect('guru_dashboard') 
    # -------------------------------
    
    konteks = {'active_page': 'dashboard'}
    return render(request, 'pembelajaran/dashboard.html', konteks)

def halaman_register(request):
    """Menampilkan halaman registrasi."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save() # Form sekarang menangani is_staff
            login(request, user)
            messages.success(request, 'Registrasi berhasil! Selamat datang.')
            
            # Arahkan ke dashboard yang benar setelah registrasi
            if user.is_staff:
                return redirect('guru_dashboard')
            else:
                return redirect('dashboard')
        else:
            # Mengambil pesan error spesifik dari form jika ada
            error_msg = 'Data tidak valid. Silakan periksa kembali isian Anda.'
            if form.errors:
                # Ambil error pertama dari validasi (misal: email sudah ada)
                first_error = next(iter(form.errors.values()))
                error_msg = first_error[0]
            messages.error(request, error_msg)
    else:
        form = RegisterForm()
    
    konteks = {'form': form}
    return render(request, 'pembelajaran/register.html', konteks)

def login_view(request):
    """Menampilkan halaman login dan mengarahkan guru/siswa."""
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


@login_required
def halaman_materi(request):
    """Mengarahkan ke materi pertama yang ada."""
    materi_pertama = SubBab.objects.order_by('bab__urutan', 'urutan').first()
    if materi_pertama:
        return redirect('detail_materi', slug=materi_pertama.slug)

    # Jika tidak ada materi sama sekali
    konteks = get_sidebar_context(request) 
    konteks['judul'] = "Materi Belum Tersedia"
    return render(request, 'pembelajaran/base.html', konteks) 

@login_required
def detail_materi(request, slug):
    """Menampilkan detail satu sub-bab materi."""
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
    })
    return render(request, 'pembelajaran/detail_materi.html', konteks)

@login_required
def kalkulator_harga_jual(request):
    """Menampilkan dan memproses kalkulator HPP."""
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
                'input_markup': markup,
            })

        except (ValueError, TypeError):
            konteks['error'] = 'Pastikan semua kolom diisi dengan angka yang valid.'
        except ZeroDivisionError:
            konteks['error'] = 'Jumlah produksi tidak boleh 0.'

    return render(request, 'pembelajaran/kalkulator.html', konteks)

def _proses_hitung_kuis(request, kuis):
    """Fungsi helper internal untuk menghitung skor kuis dari data POST."""
    semua_pertanyaan = kuis.pertanyaan_set.all()
    skor = 0
    total_soal = semua_pertanyaan.count()
    hasil_kuis = []

    for pertanyaan in semua_pertanyaan:
        jawaban_user_id = request.POST.get(f'pertanyaan_{pertanyaan.id}')
        jawaban_user = None
        jawaban_benar = None
        
        try:
            jawaban_benar = pertanyaan.pilihan_set.get(is_jawaban_benar=True)
        except Pilihan.DoesNotExist:
            jawaban_benar = None
        except Pilihan.MultipleObjectsReturned:
            jawaban_benar = pertanyaan.pilihan_set.filter(is_jawaban_benar=True).first()

        is_correct = False
        if jawaban_user_id:
            try:
                jawaban_user = Pilihan.objects.get(id=jawaban_user_id)
                if jawaban_benar and jawaban_user.id == jawaban_benar.id:
                    skor += 1
                    is_correct = True
            except Pilihan.DoesNotExist:
                jawaban_user = None

        hasil_kuis.append({
            'pertanyaan': pertanyaan,
            'jawaban_user': jawaban_user,
            'jawaban_benar': jawaban_benar,
            'is_correct': is_correct,
            'penjelasan': pertanyaan.penjelasan_jawaban or "Penjelasan belum tersedia.",
        })

    return skor, total_soal, hasil_kuis

@login_required
def daftar_kuis(request):
    """Menampilkan semua Kuis yang tersedia (standalone)."""
    semua_bab = Bab.objects.prefetch_related(
        Prefetch('subbab_list', queryset=SubBab.objects.filter(kuis__isnull=False).select_related('kuis'))
    ).order_by('urutan')
    
    babs_with_kuis = [bab for bab in semua_bab if bab.subbab_list.all().exists()]
            
    konteks = {
        'semua_bab': babs_with_kuis,
        'active_page': 'kuis', 
    }
    return render(request, 'pembelajaran/daftar_kuis.html', konteks)

@login_required
def tampil_kuis(request, slug):
    """Menampilkan halaman kuis untuk satu sub-bab."""
    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related(
        Prefetch('pertanyaan_set', queryset=Pertanyaan.objects.order_by('urutan').prefetch_related('pilihan_set'))
    ), subbab=subbab)
    
    konteks = {
        'subbab': subbab,
        'kuis': kuis,
        'active_page': 'kuis', 
    }
    return render(request, 'pembelajaran/kuis.html', konteks)

# FUNGSI LAMA 'cek_nilai_siswa_view' TELAH DIHAPUS

@login_required
def hitung_kuis(request, slug):
    """Memproses jawaban kuis, menyimpan, dan menampilkan hasil."""
    if request.method != 'POST':
        return redirect('tampil_kuis', slug=slug)

    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related('pertanyaan_set__pilihan_set'), subbab=subbab)
    
    skor, total_soal, hasil_kuis = _proses_hitung_kuis(request, kuis)

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
        'active_page': 'kuis', 
    }
    return render(request, 'pembelajaran/hasil_kuis.html', konteks)


def is_guru(user):
    """Fungsi pengecekan apakah user adalah staff (guru)."""
    return user.is_staff

@login_required
@user_passes_test(is_guru)
def guru_dashboard(request):
    """Menampilkan dashboard utama guru dengan statistik nyata."""
    total_siswa = User.objects.filter(is_staff=False).count()
    total_materi = SubBab.objects.count()
    
    waktu_24_jam_lalu = timezone.now() - timedelta(hours=24)
    kuis_selesai = HasilKuis.objects.filter(
        tanggal_mengerjakan__gte=waktu_24_jam_lalu
    ).count()

    context = {
        'total_siswa': total_siswa,
        'total_materi': total_materi,
        'kuis_selesai': kuis_selesai,
    }
    return render(request, 'pembelajaran/guru_dashboard.html', context)

@login_required
@user_passes_test(is_guru)
def guru_cek_nilai(request):
    tipe_filter = request.GET.get('tipe', 'semua')
    semua_hasil = HasilKuis.objects.select_related(
        'user', 
        'kuis__subbab'
    ).filter(user__is_staff=False).order_by('-tanggal_mengerjakan')
    if tipe_filter in ['kuis', 'latihan', 'evaluasi']:
        daftar_nilai_terfilter = semua_hasil.filter(kuis__judul__icontains=tipe_filter)
    
    else:
        daftar_nilai_terfilter = semua_hasil
        tipe_filter = 'semua' 
    KKM_KUISIONER = 75 

    daftar_nilai_processed = []
    for hasil in daftar_nilai_terfilter:
        try:
            hasil.lulus = hasil.persentase >= KKM_KUISIONER
        except AttributeError:
            if hasil.total_soal > 0:
                hasil.lulus = (hasil.skor / hasil.total_soal) * 100 >= KKM_KUISIONER
            else:
                hasil.lulus = False
        
        daftar_nilai_processed.append(hasil)
    context = {
        'daftar_nilai': daftar_nilai_processed,
        'tipe_aktif': tipe_filter, 
    }
    return render(request, 'pembelajaran/guru_cek_nilai.html', context)

@login_required
@user_passes_test(is_guru)
def guru_download_nilai_csv(request):
    """
    Membuat dan mengirimkan file CSV berisi nilai siswa 
    berdasarkan filter yang diterapkan.
    """
    tipe_filter = request.GET.get('tipe', 'semua')
    semua_hasil = HasilKuis.objects.select_related(
        'user', 
        'kuis__subbab'
    ).filter(user__is_staff=False).order_by('-tanggal_mengerjakan')
    if tipe_filter in ['kuis', 'latihan', 'evaluasi']:
        daftar_nilai_terfilter = semua_hasil.filter(kuis__judul__icontains=tipe_filter)
    else:
        daftar_nilai_terfilter = semua_hasil
        tipe_filter_nama = 'semua' 
    nama_file = f"nilai_siswa_{tipe_filter}_{timezone.now().strftime('%Y%m%d')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{nama_file}"'
    writer = csv.writer(response)

    writer.writerow([
        'Username Siswa', 
        'Email Siswa', 
        'Sub-Materi', 
        'Judul Kuis', 
        'Skor', 
        'Total Soal', 
        'Persentase', 
        'Tanggal Mengerjakan (UTC)'
    ])

    for hasil in daftar_nilai_terfilter:
        persentase = 0
        if hasil.total_soal > 0:
            persentase = (hasil.skor / hasil.total_soal) * 100
            
        writer.writerow([
            hasil.user.username,
            hasil.user.email,
            hasil.kuis.subbab.judul if hasil.kuis.subbab else '-',
            hasil.kuis.judul,
            hasil.skor,
            hasil.total_soal,
            f"{persentase:.2f}", 
            hasil.tanggal_mengerjakan.strftime('%Y-%m-%d %H:%M:%S')
        ])
    return response

@login_required
@user_passes_test(is_guru)
def guru_detail_siswa(request, user_id):
    """Menampilkan detail dan riwayat kuis untuk satu siswa."""
    siswa = get_object_or_404(User, id=user_id, is_staff=False)
    
    riwayat_kuis = HasilKuis.objects.filter(user=siswa).select_related('kuis__subbab')

    KKM_KUISIONER = 75 
    
    for hasil in riwayat_kuis:
        try:
            hasil.lulus = hasil.persentase >= KKM_KUISIONER
        except AttributeError:
            if hasil.total_soal > 0:
                hasil.lulus = (hasil.skor / hasil.total_soal) * 100 >= KKM_KUISIONER
            else:
                hasil.lulus = False

    context = {
        'siswa': siswa,
        'riwayat_kuis': riwayat_kuis
    }
    return render(request, 'pembelajaran/guru_detail_siswa.html', context)

@login_required
@user_passes_test(is_guru)
def guru_kelola_materi(request):
    """Menampilkan daftar materi untuk dikelola (via link ke Admin)."""
    context = {
        'semua_bab': Bab.objects.prefetch_related('subbab_list').order_by('urutan')
    }
    return render(request, 'pembelajaran/guru_kelola_materi.html', context)

@login_required
@user_passes_test(is_guru)
def guru_pengumuman(request):
    """(Mockup) Halaman untuk membuat pengumuman."""
    mock_riwayat = [
        {'judul': 'Kuis Bab 1 Dibuka', 'tanggal': '14 Nov 2025'},
        {'judul': 'Selamat Datang', 'tanggal': '10 Nov 2025'},
    ]
    context = {
        'riwayat_pengumuman': mock_riwayat
    }
    return render(request, 'pembelajaran/guru_pengumuman.html', context)

@login_required
@user_passes_test(is_guru)
def guru_pengaturan(request):
    """(Mockup) Halaman untuk pengaturan profil guru dan KKM."""
    context = {}
    return render(request, 'pembelajaran/guru_pengaturan.html', context)

@login_required
@user_passes_test(is_guru)
def guru_riwayat(request):
    """(MockHalaman untuk riwayat edit konten."""
    mock_log = [
        {'tipe': 'EDIT SOAL', 'tipe_css': 'text-primary', 'tanggal': '16 Nov 2025, 02:30', 'deskripsi': 'Guru "Budi" mengedit Soal #3 pada "Kuis Pemahaman: Biaya Tetap".', 'ip': '127.0.0.1 (Simulasi)'},
        {'tipe': 'TAMBAH MATERI', 'tipe_css': 'text-success', 'tanggal': '15 Nov 2025, 11:00', 'deskripsi': 'Guru "Budi" menambah Sub-Bab baru: "Biaya Promosi" di bawah Bab "Analisis Komponen Biaya Produksi".', 'ip': '127.0.0.1 (Simulasi)'},
    ]
    context = {
        'daftar_log': mock_log
    }
    return render(request, 'pembelajaran/guru_riwayat.html', context)