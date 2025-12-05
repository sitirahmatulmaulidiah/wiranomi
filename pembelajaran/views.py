import csv
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User 
from datetime import timedelta 
from django.db.models import Prefetch, Count, Q

# Import Models
from .models import (
    Bab, SubBab, Kuis, Pertanyaan, Pilihan, 
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress,
    Latihan, HasilLatihan, SoalLatihan, PilihanLatihan,
    SoalEvaluasi, PilihanJawaban, HasilEvaluasi
)
from .forms import RegisterForm

# --- FUNGSI HELPER ---

def get_sidebar_context(request):
    """Mengambil konteks sidebar: Daftar Bab, Status Materi, Latihan, dan Kuis."""
    semua_bab = Bab.objects.prefetch_related(
        Prefetch('subbab_list', queryset=SubBab.objects.order_by('urutan'))
    ).order_by('urutan')
    
    completed_subbabs = set()
    completed_latihan = set()
    completed_kuis = set()

    if request.user.is_authenticated:
        # 1. Cek Materi (UserProgress)
        completed_subbabs = set(UserProgress.objects.filter(
            user=request.user
        ).values_list('subbab_id', flat=True))

        # 2. Cek Latihan (HasilLatihan -> Latihan -> SubBab)
        # Kita ambil sub_bab_id dari latihan yang sudah dikerjakan
        completed_latihan = set(HasilLatihan.objects.filter(
            user=request.user
        ).values_list('latihan__sub_bab_id', flat=True))

        # 3. Cek Kuis (HasilKuis -> Kuis -> SubBab)
        # Kita ambil subbab_id dari kuis yang sudah dikerjakan
        completed_kuis = set(HasilKuis.objects.filter(
            user=request.user
        ).values_list('kuis__subbab_id', flat=True))

    return {
        'semua_bab': semua_bab,
        'completed_subbabs': completed_subbabs,
        'completed_latihan': completed_latihan, # <-- Data Baru
        'completed_kuis': completed_kuis        # <-- Data Baru
    }

def cek_syarat_evaluasi(user):
    """
    Mengecek apakah user sudah menyelesaikan Latihan dan Kuis YANG AKTIF (Punya Soal).
    Return: (is_unlocked, progress_message)
    """
    if not user.is_authenticated:
        return False, "Silakan login terlebih dahulu."

    # --- LOGIKA BARU: Hanya hitung Kuis/Latihan yang memiliki soal ---
    
    # 1. Hitung Total yang Tersedia (Hanya yang punya soal)
    total_kuis_tersedia = Kuis.objects.filter(pertanyaan_set__isnull=False).distinct().count()
    total_latihan_tersedia = Latihan.objects.filter(daftar_soal__isnull=False).distinct().count()
    
    # 2. Hitung yang sudah dikerjakan User (Distinct ID)
    total_kuis_dikerjakan = HasilKuis.objects.filter(user=user).values('kuis').distinct().count()
    total_latihan_dikerjakan = HasilLatihan.objects.filter(user=user).values('latihan').distinct().count()

    # 3. Hitung Sisa (Pastikan tidak minus)
    sisa_kuis = max(0, total_kuis_tersedia - total_kuis_dikerjakan)
    sisa_latihan = max(0, total_latihan_tersedia - total_latihan_dikerjakan)

    if sisa_kuis == 0 and sisa_latihan == 0:
        return True, "Evaluasi Terbuka"
    else:
        # Pesan detail agar user tahu apa yang kurang
        msg_parts = []
        if sisa_latihan > 0:
            msg_parts.append(f"{sisa_latihan} Latihan")
        if sisa_kuis > 0:
            msg_parts.append(f"{sisa_kuis} Kuis")
            
        msg = f"Selesaikan {', '.join(msg_parts)} lagi untuk membuka."
        return False, msg

def is_guru(user):
    """Fungsi pengecekan apakah user adalah staff (guru)."""
    return user.is_staff


# --- VIEW UTAMA (AUTH & DASHBOARD) ---

def halaman_dashboard(request):
    """Menampilkan halaman dashboard publik."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('guru_dashboard') 
    
    # Cek Status Evaluasi
    evaluasi_unlocked = False
    pesan_kunci = ""
    sudah_evaluasi = False
    nilai_evaluasi = None

    if request.user.is_authenticated:
        # Cek riwayat evaluasi
        riwayat_eval = HasilEvaluasi.objects.filter(user=request.user).last()
        if riwayat_eval:
            sudah_evaluasi = True
            evaluasi_unlocked = True 
            # Hitung nilai skala 100 jika skor masih mentah
            if riwayat_eval.total_soal > 0:
                nilai_evaluasi = int((riwayat_eval.skor / riwayat_eval.total_soal) * 100)
            else:
                nilai_evaluasi = 0
        else:
            # Cek syarat unlock
            evaluasi_unlocked, pesan_kunci = cek_syarat_evaluasi(request.user)
    
    konteks = {
        'active_page': 'dashboard',
        'evaluasi_unlocked': evaluasi_unlocked,
        'pesan_kunci': pesan_kunci,
        'sudah_evaluasi': sudah_evaluasi,
        'nilai_evaluasi': nilai_evaluasi
    }
    return render(request, 'pembelajaran/dashboard.html', konteks)

def halaman_register(request):
    """Menampilkan halaman registrasi."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user_baru = form.save()
            login(request, user_baru)
            messages.success(request, 'Registrasi berhasil! Selamat datang.')
            
            nama = user_baru.username
            if user_baru.is_staff:
                pesan = f"Selamat bergabung, Bapak/Ibu Guru {nama}! Akun pengajar Anda siap digunakan."
            else:
                pesan = f"Hore! Selamat datang {nama}. Akun belajarmu sudah siap!"
            
            messages.success(request, pesan)

            if user_baru.is_staff:
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
            
            peran = "Guru" if user.is_staff else "Siswa"
            messages.success(request, f"Anda berhasil masuk ke akun {peran}.")

            if user.is_staff:
                return redirect('guru_dashboard')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, 'Username atau password salah. Silakan coba lagi.')
    
    else:
        form = AuthenticationForm()
    
    return render(request, 'pembelajaran/login.html', {'form': form})


# --- VIEW MATERI ---

@login_required
def halaman_materi(request):
    """Mengarahkan ke materi pertama yang ada."""
    materi_pertama = SubBab.objects.order_by('bab__urutan', 'urutan').first()
    if materi_pertama:
        return redirect('detail_materi', slug=materi_pertama.slug)

    konteks = get_sidebar_context(request) 
    konteks['judul'] = "Materi Belum Tersedia"
    return render(request, 'pembelajaran/base.html', konteks) 

# views.py

@login_required
def detail_materi(request, slug):
    """Menampilkan detail satu sub-bab materi dengan tombol Selesai manual."""
    konteks = get_sidebar_context(request) 
    
    subbab_aktif = get_object_or_404(
        SubBab.objects.prefetch_related(
            'studi_kasus', 
            'kuis__pertanyaan_set__pilihan_set', 
            'game_drag_drop__item_set'
        ), 
        slug=slug
    )
    
    # --- LOGIKA BARU: MANUAL CHECKLIST ---
    is_completed = False
    if request.user.is_authenticated:
        # 1. Cek apakah sudah pernah ditandai selesai?
        is_completed = UserProgress.objects.filter(
            user=request.user, 
            subbab=subbab_aktif
        ).exists()

        # 2. Jika Tombol "Tandai Selesai" diklik (Method POST)
        if request.method == 'POST' and 'tandai_selesai' in request.POST:
            UserProgress.objects.get_or_create(
                user=request.user,
                subbab=subbab_aktif,
                defaults={'completed_at': timezone.now()}
            )
            is_completed = True
            messages.success(request, "Materi berhasil ditandai selesai! ✅")
            
            # Update sidebar realtime
            konteks['completed_subbabs'].add(subbab_aktif.id)
    
    # --- Akhir Logika Baru ---

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
        'is_completed': is_completed, # <-- Kirim status ke template
    })
    return render(request, 'pembelajaran/detail_materi.html', konteks)


# --- VIEW LATIHAN ---

@login_required
def detail_latihan(request, slug):
    konteks = get_sidebar_context(request)
    subbab = get_object_or_404(SubBab, slug=slug)
    latihan = subbab.list_latihan.first()
    
    soal_list = []
    if latihan:
        soal_list = latihan.daftar_soal.all().prefetch_related('pilihan_latihan_set')

    sudah_mengerjakan = False
    nilai_terakhir = None
    if latihan:
        riwayat = HasilLatihan.objects.filter(user=request.user, latihan=latihan).last()
        if riwayat:
            sudah_mengerjakan = True
            nilai_terakhir = riwayat.nilai

    konteks.update({
        'subbab': subbab,
        'latihan': latihan,
        'soal_list': soal_list,
        'sudah_mengerjakan': sudah_mengerjakan,
        'nilai_terakhir': nilai_terakhir,
        'active_slug': slug, 
        'active_tab': 'latihan'
    })
    
    return render(request, 'pembelajaran/detail_latihan.html', konteks)

@login_required
def submit_latihan(request, latihan_id):
    if request.method != "POST":
        return redirect('dashboard')

    latihan = get_object_or_404(Latihan, id=latihan_id)
    soal_list = latihan.daftar_soal.all().prefetch_related('pilihan_latihan_set')
    
    jumlah_benar = 0
    total_soal = soal_list.count()
    analisis_jawaban = [] 

    for soal in soal_list:
        jawaban_user_id = request.POST.get(f'soal_{soal.id}')
        pilihan_user = None
        pilihan_benar = None
        
        for pil in soal.pilihan_latihan_set.all():
            if pil.is_jawaban_benar:
                pilihan_benar = pil
            if str(pil.id) == jawaban_user_id:
                pilihan_user = pil

        is_correct = False
        if pilihan_user and pilihan_benar:
            if pilihan_user.id == pilihan_benar.id:
                jumlah_benar += 1
                is_correct = True
        
        analisis_jawaban.append({
            'soal': soal,
            'pilihan_user': pilihan_user,
            'pilihan_benar': pilihan_benar,
            'is_correct': is_correct,
        })
    
    nilai_akhir = 0
    if total_soal > 0:
        nilai_akhir = int((jumlah_benar / total_soal) * 100)

    HasilLatihan.objects.create(
        user=request.user,
        latihan=latihan,
        nilai=nilai_akhir,
        text_jawaban=f"Benar {jumlah_benar} dari {total_soal} soal."
    )
    
    konteks = {
        'latihan': latihan,
        'nilai': nilai_akhir,
        'jumlah_benar': jumlah_benar,
        'total_soal': total_soal,
        'analisis_jawaban': analisis_jawaban,
    }
    
    return render(request, 'pembelajaran/review_latihan.html', konteks)


# --- VIEW KALKULATOR ---

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
                f"Total biaya produksi = Rp {total_biaya_produksi_awal:,.0f}",
                f"Biaya HPP = Rp {biaya_produksi_per_unit_awal:,.0f}",
                f"Harga Jual = Rp {harga_jual_per_unit_awal:,.0f}",
                f"Total Pendapatan = Rp {total_pendapatan_awal:,.0f}",
                f"Laba / Rugi = Rp {laba_rugi_awal:,.0f}"
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


# --- VIEW EVALUASI ---

@login_required
def evaluasi(request):
    """Menampilkan dan menghitung skor Evaluasi Akhir."""
    
    # 1. Cek Syarat & Riwayat
    is_unlocked, msg = cek_syarat_evaluasi(request.user)
    riwayat_eval = HasilEvaluasi.objects.filter(user=request.user).last()
    
    if riwayat_eval:
        konteks = {
            'active_page': 'evaluasi',
            'hasil_nilai': int((riwayat_eval.skor / riwayat_eval.total_soal) * 100) if riwayat_eval.total_soal > 0 else 0,
            'sudah_selesai': True
        }
        return render(request, 'pembelajaran/evaluasi.html', konteks)

    if not is_unlocked:
        messages.error(request, f"Evaluasi terkunci! {msg}")
        return redirect('dashboard')

    # 2. Proses Evaluasi
    semua_soal = SoalEvaluasi.objects.all()
    hasil_nilai = None
    
    if request.method == 'POST':
        skor = 0
        total_soal = semua_soal.count()
        
        for soal in semua_soal:
            pilihan_id = request.POST.get(f'soal_{soal.id}')
            if pilihan_id:
                pilihan_user = soal.pilihan.filter(id=pilihan_id).first()
                if pilihan_user and pilihan_user.apakah_benar:
                    skor += 1
        
        HasilEvaluasi.objects.create(
            user=request.user,
            skor=skor,
            total_soal=total_soal
        )

        if total_soal > 0:
            hasil_nilai = int((skor / total_soal) * 100)
        else:
            hasil_nilai = 0

    konteks = {
        'active_page': 'evaluasi', 
        'soal_list': semua_soal,
        'hasil_nilai': hasil_nilai
    }
    return render(request, 'pembelajaran/evaluasi.html', konteks)


# --- VIEW KUIS & FUNGSI HELPER ---

def _proses_hitung_kuis(request, kuis):
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
        })

    return skor, total_soal, hasil_kuis

@login_required
def daftar_kuis(request):
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
    konteks = get_sidebar_context(request) 
    
    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related(
        Prefetch('pertanyaan_set', queryset=Pertanyaan.objects.order_by('urutan').prefetch_related('pilihan_set'))
    ), subbab=subbab)
    
    sudah_mengerjakan = False
    nilai_terakhir = 0
    
    if request.user.is_authenticated:
        riwayat = HasilKuis.objects.filter(user=request.user, kuis=kuis).last()
        if riwayat:
            sudah_mengerjakan = True
            # Menghitung nilai 0-100 dari riwayat
            if riwayat.total_soal > 0:
                nilai_terakhir = int((riwayat.skor / riwayat.total_soal) * 100)
            else:
                nilai_terakhir = 0

    konteks.update({
        'subbab': subbab,
        'kuis': kuis,
        'active_page': 'kuis',
        'active_slug': slug,
        'sudah_mengerjakan': sudah_mengerjakan,
        'nilai_terakhir': nilai_terakhir,
    })
    
    return render(request, 'pembelajaran/kuis.html', konteks)

@login_required
def hitung_kuis(request, slug):
    if request.method != 'POST':
        return redirect('tampil_kuis', slug=slug)

    subbab = get_object_or_404(SubBab, slug=slug)
    kuis = get_object_or_404(Kuis.objects.prefetch_related('pertanyaan_set__pilihan_set'), subbab=subbab)
    
    skor, total_soal, hasil_kuis = _proses_hitung_kuis(request, kuis)

    # Simpan ke Database (Tetap simpan skor mentah agar data presisi)
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

    # --- HITUNG NILAI SKALA 100 UNTUK DITAMPILKAN ---
    nilai_akhir = 0
    if total_soal > 0:
        nilai_akhir = int((skor / total_soal) * 100)

    konteks = {
        'subbab': subbab,
        'skor': skor,             # Jumlah benar (misal: 4)
        'total_soal': total_soal, # Total soal (misal: 5)
        'nilai_akhir': nilai_akhir, # NILAI BARU (misal: 80) - Skala 100
        'hasil_kuis': hasil_kuis,
        'setengah_soal': total_soal / 2, 
        'active_page': 'kuis', 
    }
    return render(request, 'pembelajaran/hasil_kuis.html', konteks)


# --- VIEW GURU ---

@login_required
@user_passes_test(is_guru)
def guru_dashboard(request):
    total_siswa = User.objects.filter(is_staff=False).count()
    total_materi = SubBab.objects.count()
    waktu_24_jam_lalu = timezone.now() - timedelta(hours=24)
    kuis_selesai = HasilKuis.objects.filter(tanggal_mengerjakan__gte=waktu_24_jam_lalu).count()

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
    semua_hasil = HasilKuis.objects.select_related('user', 'kuis__subbab').filter(user__is_staff=False).order_by('-tanggal_mengerjakan')
    
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
    tipe_filter = request.GET.get('tipe', 'semua')
    semua_hasil = HasilKuis.objects.select_related('user', 'kuis__subbab').filter(user__is_staff=False).order_by('-tanggal_mengerjakan')
    
    if tipe_filter in ['kuis', 'latihan', 'evaluasi']:
        daftar_nilai_terfilter = semua_hasil.filter(kuis__judul__icontains=tipe_filter)
    else:
        daftar_nilai_terfilter = semua_hasil
    
    nama_file = f"nilai_siswa_{tipe_filter}_{timezone.now().strftime('%Y%m%d')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{nama_file}"'
    writer = csv.writer(response)

    writer.writerow(['Username Siswa', 'Email Siswa', 'Sub-Materi', 'Judul Kuis', 'Skor', 'Total Soal', 'Persentase', 'Tanggal (UTC)'])

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

    context = {'siswa': siswa, 'riwayat_kuis': riwayat_kuis}
    return render(request, 'pembelajaran/guru_detail_siswa.html', context)

@login_required
@user_passes_test(is_guru)
def guru_kelola_materi(request):
    context = {'semua_bab': Bab.objects.prefetch_related('subbab_list').order_by('urutan')}
    return render(request, 'pembelajaran/guru_kelola_materi.html', context)

@login_required
@user_passes_test(is_guru)
def guru_pengumuman(request):
    mock_riwayat = [
        {'judul': 'Kuis Bab 1 Dibuka', 'tanggal': '14 Nov 2025'},
        {'judul': 'Selamat Datang', 'tanggal': '10 Nov 2025'},
    ]
    context = {'riwayat_pengumuman': mock_riwayat}
    return render(request, 'pembelajaran/guru_pengumuman.html', context)

@login_required
@user_passes_test(is_guru)
def guru_pengaturan(request):
    return render(request, 'pembelajaran/guru_pengaturan.html', {})

@login_required
@user_passes_test(is_guru)
def guru_riwayat(request):
    mock_log = [
        {'tipe': 'EDIT SOAL', 'tipe_css': 'text-primary', 'tanggal': '16 Nov 2025, 02:30', 'deskripsi': 'Guru "Budi" mengedit Soal #3 pada "Kuis Pemahaman: Biaya Tetap".', 'ip': '127.0.0.1 (Simulasi)'},
        {'tipe': 'TAMBAH MATERI', 'tipe_css': 'text-success', 'tanggal': '15 Nov 2025, 11:00', 'deskripsi': 'Guru "Budi" menambah Sub-Bab baru: "Biaya Promosi" di bawah Bab "Analisis Komponen Biaya Produksi".', 'ip': '127.0.0.1 (Simulasi)'},
    ]
    context = {'daftar_log': mock_log}
    return render(request, 'pembelajaran/guru_riwayat.html', context)