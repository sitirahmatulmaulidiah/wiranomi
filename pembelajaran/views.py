import csv
from django.http import HttpResponse
from django.utils import timezone
from itertools import chain 
from operator import attrgetter
from django.utils.text import slugify 
from django.shortcuts import render, get_object_or_404, redirect
from .models import (
    Bab, SubBab, Kuis, Pertanyaan, Pilihan, 
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress,
    Latihan, HasilLatihan, SoalLatihan, PilihanLatihan,
    SoalEvaluasi, PilihanJawaban, PengaturanGuru
)
from .forms import (
    RegisterForm, BabForm, SubBabForm, GuruProfileForm, 
    PengaturanKKMForm, KuisForm, LatihanForm, SoalEvaluasiForm,
    PilihanEvaluasiFormSet, SoalLatihanForm, PilihanLatihanFormSet,
    PertanyaanKuisForm, PilihanKuisFormSet
)
from django.contrib.auth import login, authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User 
from datetime import timedelta 
from django.db.models import Prefetch
from django.contrib.auth import update_session_auth_hash

# IMPORTS UNTUK RIWAYAT LOG
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType

# --- HELPER FUNGSI LOGGING ---
def catat_riwayat(user, obj, action_flag, message=""):
    """
    Mencatat aktivitas user ke tabel LogEntry Django.
    action_flag: ADDITION (1), CHANGE (2), DELETION (3)
    """
    try:
        LogEntry.objects.log_action(
            user_id=user.id,
            content_type_id=ContentType.objects.get_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=action_flag,
            change_message=message
        )
    except Exception as e:
        print(f"Gagal mencatat log: {e}")


# ==========================================
# 1. BAGIAN UMUM & SISWA
# ==========================================

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

@login_required
def halaman_materi(request):
    materi_pertama = SubBab.objects.order_by('bab__urutan', 'urutan').first()
    if materi_pertama:
        return redirect('detail_materi', slug=materi_pertama.slug)

    konteks = get_sidebar_context(request) 
    konteks['judul'] = "Materi Belum Tersedia"
    return render(request, 'pembelajaran/base.html', konteks) 

@login_required
def detail_materi(request, slug):
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
                'input_markup': markup,
            })

        except (ValueError, TypeError):
            konteks['error'] = 'Pastikan semua kolom diisi dengan angka yang valid.'
        except ZeroDivisionError:
            konteks['error'] = 'Jumlah produksi tidak boleh 0.'

    return render(request, 'pembelajaran/kalkulator.html', konteks)

@login_required
def evaluasi(request):
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

@login_required
def hitung_kuis(request, slug):
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


# ==========================================
# 2. BAGIAN GURU: DASHBOARD & PENGATURAN
# ==========================================

def is_guru(user):
    return user.is_staff

@login_required
@user_passes_test(is_guru)
def guru_dashboard(request):
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
    pengaturan, _ = PengaturanGuru.objects.get_or_create(user=request.user)
    KKM_LATIHAN = pengaturan.kkm_latihan
    KKM_KUIS = pengaturan.kkm_kuis
    KKM_EVALUASI = pengaturan.kkm_evaluasi

    tipe_filter = request.GET.get('tipe', 'semua')
    qs_kuis = HasilKuis.objects.select_related('user', 'kuis__subbab').filter(user__is_staff=False)
    qs_latihan = HasilLatihan.objects.select_related('user', 'latihan__sub_bab').filter(user__is_staff=False)

    daftar_hasil = []
    
    if tipe_filter == 'kuis':
        daftar_hasil = list(qs_kuis)
    elif tipe_filter == 'latihan':
        daftar_hasil = list(qs_latihan)
    elif tipe_filter == 'evaluasi':
        daftar_hasil = list(qs_kuis.filter(kuis__judul__icontains='evaluasi'))
    else:
        daftar_hasil = list(chain(qs_kuis, qs_latihan))

    daftar_nilai_processed = []
    
    for hasil in daftar_hasil:
        if isinstance(hasil, HasilKuis):
            judul_lower = hasil.kuis.judul.lower()
            batas_kkm = KKM_EVALUASI if 'evaluasi' in judul_lower else KKM_KUIS
            
            hasil.judul_konten = hasil.kuis.judul
            hasil.nama_subbab = hasil.kuis.subbab.judul if hasil.kuis.subbab else "-"
            hasil.tipe_label = "Kuis" if 'evaluasi' not in judul_lower else "Evaluasi"
            hasil.tanggal_sort = hasil.tanggal_mengerjakan
        
            try:
                hasil.lulus = hasil.persentase >= batas_kkm
            except:
                hasil.lulus = False

        elif isinstance(hasil, HasilLatihan):
            hasil.judul_konten = hasil.latihan.judul
            hasil.nama_subbab = hasil.latihan.sub_bab.judul if hasil.latihan.sub_bab else "-"
            hasil.tipe_label = "Latihan"
            hasil.tanggal_sort = hasil.tanggal_kumpul
            hasil.skor = hasil.nilai 
            hasil.total_soal = 100 
            hasil.lulus = hasil.nilai >= KKM_LATIHAN

        daftar_nilai_processed.append(hasil)
    daftar_nilai_processed.sort(key=attrgetter('tanggal_sort'), reverse=True)
    
    context = {
        'daftar_nilai': daftar_nilai_processed,
        'tipe_aktif': tipe_filter, 
    }
    return render(request, 'pembelajaran/guru_cek_nilai.html', context)

@login_required
@user_passes_test(is_guru)
def guru_download_nilai_csv(request):
    tipe_filter = request.GET.get('tipe', 'semua')
    
    qs_kuis = HasilKuis.objects.select_related('user', 'kuis__subbab').filter(user__is_staff=False)
    qs_latihan = HasilLatihan.objects.select_related('user', 'latihan__sub_bab').filter(user__is_staff=False)

    daftar_hasil = []
    if tipe_filter == 'kuis':
        daftar_hasil = list(qs_kuis)
    elif tipe_filter == 'latihan':
        daftar_hasil = list(qs_latihan)
    elif tipe_filter == 'evaluasi':
        daftar_hasil = list(qs_kuis.filter(kuis__judul__icontains='evaluasi'))
    else:
        daftar_hasil = list(chain(qs_kuis, qs_latihan))

    def get_tanggal(obj):
        if hasattr(obj, 'tanggal_mengerjakan'):
            return obj.tanggal_mengerjakan
        elif hasattr(obj, 'tanggal_kumpul'):
            return obj.tanggal_kumpul
        return timezone.now()

    def get_nama_siswa(obj):
        nama = obj.user.first_name if obj.user.first_name else obj.user.username
        return nama.lower()

    daftar_hasil.sort(key=get_tanggal, reverse=True)
    daftar_hasil.sort(key=get_nama_siswa)

    nama_file = f"Laporan_Nilai_Wiranomi_{tipe_filter.capitalize()}_{timezone.now().strftime('%d-%m-%Y')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{nama_file}"'
    
    response.write(u'\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')

    writer.writerow([
        'No',
        'Nama Siswa',
        'Email Siswa',
        'Tipe', 
        'Judul Sub-Bab', 
        'Judul Kegiatan', 
        'Nilai',
        'Tanggal',
        'Keterangan'
    ])

    no_urut = 1
    for hasil in daftar_hasil:
        nama_siswa = f"{hasil.user.first_name} {hasil.user.last_name}".strip() or hasil.user.username
        email_siswa = hasil.user.email
        
        tipe = "-"
        sub_bab = "-"
        judul_kegiatan = "-"
        nilai = 0
        str_tanggal = "-"
        keterangan = "-"
        
        raw_date = None

        if hasattr(hasil, 'tanggal_mengerjakan'):
            raw_date = hasil.tanggal_mengerjakan
            judul_kegiatan = hasil.kuis.judul
            
            if 'evaluasi' in judul_kegiatan.lower():
                tipe = 'Evaluasi'
            else:
                tipe = 'Kuis'
            
            if hasil.kuis.subbab:
                sub_bab = hasil.kuis.subbab.judul
            
            nilai = hasil.skor
            keterangan = f"Benar {hasil.skor} dari {hasil.total_soal} soal"

        elif hasattr(hasil, 'tanggal_kumpul'):
            raw_date = hasil.tanggal_kumpul
            tipe = 'Latihan'
            judul_kegiatan = hasil.latihan.judul
            
            if hasil.latihan.sub_bab:
                sub_bab = hasil.latihan.sub_bab.judul
            
            nilai = hasil.nilai
            keterangan = hasil.text_jawaban

        if raw_date:
            try:
                local_date = timezone.localtime(raw_date)
                str_tanggal = local_date.strftime('%d/%m/%Y %H:%M')
            except Exception:
                str_tanggal = str(raw_date)

        writer.writerow([
            no_urut,
            nama_siswa,
            email_siswa,
            tipe,
            sub_bab,
            judul_kegiatan,
            nilai,
            str_tanggal,
            keterangan
        ])
        no_urut += 1

    return response

@login_required
@user_passes_test(is_guru)
def guru_detail_siswa(request, user_id):
    siswa = get_object_or_404(User, id=user_id, is_staff=False)
    riwayat_kuis = HasilKuis.objects.filter(user=siswa).select_related('kuis__subbab')

    pengaturan, _ = PengaturanGuru.objects.get_or_create(user=request.user)
    KKM_STANDAR = pengaturan.kkm_kuis 
    
    for hasil in riwayat_kuis:
        try:
            hasil.lulus = hasil.persentase >= KKM_STANDAR
        except AttributeError:
            if hasil.total_soal > 0:
                hasil.lulus = (hasil.skor / hasil.total_soal) * 100 >= KKM_STANDAR
            else:
                hasil.lulus = False

    context = {
        'siswa': siswa,
        'riwayat_kuis': riwayat_kuis
    }
    return render(request, 'pembelajaran/guru_detail_siswa.html', context)

@login_required
@user_passes_test(is_guru)
def guru_pengaturan(request):
    pengaturan, created = PengaturanGuru.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        if 'submit_profil' in request.POST:
            profil_form = GuruProfileForm(request.POST, instance=request.user)
            kkm_form = PengaturanKKMForm(instance=pengaturan)
            
            if profil_form.is_valid():
                user = profil_form.save()
                password_baru = profil_form.cleaned_data.get('password_baru')
                if password_baru:
                    user.set_password(password_baru)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Profil dan password berhasil diperbarui.')
                else:
                    messages.success(request, 'Profil berhasil diperbarui.')
                return redirect('guru_pengaturan')
                
        elif 'submit_kkm' in request.POST:
            kkm_form = PengaturanKKMForm(request.POST, instance=pengaturan)
            profil_form = GuruProfileForm(instance=request.user)
            
            if kkm_form.is_valid():
                kkm_form.save()
                messages.success(request, 'Pengaturan KKM berhasil disimpan.')
                return redirect('guru_pengaturan')
    else:
        profil_form = GuruProfileForm(instance=request.user)
        kkm_form = PengaturanKKMForm(instance=pengaturan)

    context = {
        'profil_form': profil_form,
        'kkm_form': kkm_form
    }
    return render(request, 'pembelajaran/guru_pengaturan.html', context)

@login_required
@user_passes_test(is_guru)
def guru_riwayat(request):
    # Ambil 20 log terakhir
    logs = LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')[:20]
    
    daftar_log = []
    for log in logs:
        # Set Tipe & Warna berdasarkan action_flag Django
        if log.action_flag == ADDITION:
            tipe = "TAMBAH"
            tipe_css = "text-success"
        elif log.action_flag == CHANGE:
            tipe = "EDIT"
            tipe_css = "text-warning"
        elif log.action_flag == DELETION:
            tipe = "HAPUS"
            tipe_css = "text-danger"
        else:
            tipe = "INFO"
            tipe_css = "text-secondary"

        deskripsi = f'User "{log.user.username}" {tipe.lower()} {log.content_type.name} "{log.object_repr}".'
        if log.change_message:
            deskripsi += f" ({log.change_message})"

        tanggal = timezone.localtime(log.action_time).strftime('%d %b %Y, %H:%M')

        daftar_log.append({
            'tipe': tipe,
            'tipe_css': tipe_css,
            'tanggal': tanggal,
            'deskripsi': deskripsi,
            'ip': '-' 
        })

    context = {
        'daftar_log': daftar_log
    }
    return render(request, 'pembelajaran/guru_riwayat.html', context)


@login_required
@user_passes_test(is_guru)
def guru_kelola_materi(request):
    context = {
        'semua_bab': Bab.objects.prefetch_related('subbab_list__kuis', 'subbab_list__list_latihan').order_by('urutan'),
        'semua_evaluasi': SoalEvaluasi.objects.all().order_by('-dibuat_pada'),
        'bab_form': BabForm(),
        'evaluasi_form': SoalEvaluasiForm(),
    }
    return render(request, 'pembelajaran/guru_kelola_materi.html', context)

@login_required
@user_passes_test(is_guru)
def tambah_bab(request):
    if request.method == 'POST':
        form = BabForm(request.POST)
        if form.is_valid():
            obj = form.save()
            catat_riwayat(request.user, obj, ADDITION, "Menambahkan Bab baru")
            messages.success(request, "Bab baru berhasil ditambahkan.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def edit_bab(request, bab_id):
    bab = get_object_or_404(Bab, id=bab_id)
    if request.method == 'POST':
        form = BabForm(request.POST, instance=bab)
        if form.is_valid():
            obj = form.save()
            catat_riwayat(request.user, obj, CHANGE, "Mengubah Bab")
            messages.success(request, "Bab berhasil diperbarui.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def hapus_bab(request, bab_id):
    bab = get_object_or_404(Bab, id=bab_id)
    catat_riwayat(request.user, bab, DELETION, f"Menghapus Bab '{bab.judul}'")
    bab.delete()
    messages.success(request, "Bab berhasil dihapus.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def tambah_subbab(request, bab_id):
    bab = get_object_or_404(Bab, id=bab_id)
    if request.method == 'POST':
        form = SubBabForm(request.POST)
        if form.is_valid():
            subbab = form.save(commit=False)
            subbab.bab = bab
            base_slug = slugify(subbab.judul)
            subbab.slug = base_slug
            
            counter = 1
            while SubBab.objects.filter(slug=subbab.slug).exists():
                subbab.slug = f"{base_slug}-{counter}"
                counter += 1
                
            subbab.save()
            catat_riwayat(request.user, subbab, ADDITION, f"Menambahkan Sub-Bab di {bab.judul}")
            messages.success(request, "Sub-Bab berhasil ditambahkan.")
            return redirect('guru_kelola_materi')
    else:
        form = SubBabForm()

    return render(request, 'pembelajaran/guru_form_subbab.html', {'form': form, 'judul_halaman': f'Tambah Sub-Bab di {bab.judul}'})

@login_required
@user_passes_test(is_guru)
def edit_subbab(request, subbab_id):
    subbab = get_object_or_404(SubBab, id=subbab_id)
    if request.method == 'POST':
        form = SubBabForm(request.POST, instance=subbab)
        if form.is_valid():
            subbab_obj = form.save(commit=False)
            subbab_obj.slug = slugify(subbab_obj.judul)
            if SubBab.objects.filter(slug=subbab_obj.slug).exclude(id=subbab_obj.id).exists():
                subbab_obj.slug = f"{slugify(subbab_obj.judul)}-{subbab_obj.id}"
            
            subbab_obj.save()
            catat_riwayat(request.user, subbab_obj, CHANGE, "Mengubah konten Sub-Bab")
            messages.success(request, "Sub-Bab berhasil diperbarui.")
            return redirect('guru_kelola_materi')
    else:
        form = SubBabForm(instance=subbab)

    return render(request, 'pembelajaran/guru_form_subbab.html', {'form': form, 'judul_halaman': 'Edit Sub-Bab'})

@login_required
@user_passes_test(is_guru)
def hapus_subbab(request, subbab_id):
    subbab = get_object_or_404(SubBab, id=subbab_id)
    catat_riwayat(request.user, subbab, DELETION, f"Menghapus Sub-Bab '{subbab.judul}'")
    subbab.delete()
    messages.success(request, "Sub-Bab berhasil dihapus.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def kelola_kuis(request, subbab_id):
    subbab = get_object_or_404(SubBab, id=subbab_id)
    try:
        kuis = subbab.kuis
    except Kuis.DoesNotExist:
        kuis = None

    if request.method == 'POST':
        form = KuisForm(request.POST, instance=kuis)
        if form.is_valid():
            kuis_obj = form.save(commit=False)
            kuis_obj.subbab = subbab
            kuis_obj.save()
            
            action = CHANGE if kuis else ADDITION
            msg = "Mengupdate Kuis" if kuis else "Membuat Kuis Baru"
            catat_riwayat(request.user, kuis_obj, action, msg)
            
            messages.success(request, f"Kuis untuk '{subbab.judul}' berhasil disimpan.")
            return redirect('guru_kelola_materi')
    else:
        form = KuisForm(instance=kuis) if kuis else KuisForm(initial={'judul': f'Kuis: {subbab.judul}'})

    return render(request, 'pembelajaran/guru_form_input.html', {
        'form': form, 
        'judul_halaman': f'Kelola Kuis: {subbab.judul}',
        'tombol_simpan': 'Simpan Kuis'
    })

@login_required
@user_passes_test(is_guru)
def hapus_kuis(request, kuis_id):
    kuis = get_object_or_404(Kuis, id=kuis_id)
    catat_riwayat(request.user, kuis, DELETION, f"Menghapus Kuis '{kuis.judul}'")
    kuis.delete()
    messages.success(request, "Kuis berhasil dihapus.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def daftar_soal_kuis(request, kuis_id):
    kuis = get_object_or_404(Kuis, id=kuis_id)
    soal_list = kuis.pertanyaan_set.all().order_by('urutan')
    return render(request, 'pembelajaran/guru_daftar_soal.html', {
        'parent_obj': kuis,
        'soal_list': soal_list,
        'judul_halaman': f'Daftar Soal: {kuis.judul}',
        'tipe': 'kuis'
    })

@login_required
@user_passes_test(is_guru)
def tambah_soal_kuis(request, kuis_id):
    kuis = get_object_or_404(Kuis, id=kuis_id)
    if request.method == 'POST':
        form = PertanyaanKuisForm(request.POST)
        formset = PilihanKuisFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            soal = form.save(commit=False)
            soal.kuis = kuis
            soal.save()
            
            pilihan = formset.save(commit=False)
            for p in pilihan:
                p.pertanyaan = soal
                p.save()
                
            catat_riwayat(request.user, soal, ADDITION, "Menambah soal Kuis")
            messages.success(request, "Pertanyaan kuis berhasil ditambahkan.")
            return redirect('daftar_soal_kuis', kuis_id=kuis.id)
    else:
        form = PertanyaanKuisForm()
        formset = PilihanKuisFormSet()

    return render(request, 'pembelajaran/guru_form_soal.html', {
        'form': form,
        'formset': formset,
        'judul_halaman': 'Tambah Pertanyaan Kuis',
        'parent_id': kuis.id,
        'tipe': 'kuis'
    })

@login_required
@user_passes_test(is_guru)
def edit_soal_kuis(request, soal_id):
    soal = get_object_or_404(Pertanyaan, id=soal_id)
    if request.method == 'POST':
        form = PertanyaanKuisForm(request.POST, instance=soal)
        formset = PilihanKuisFormSet(request.POST, instance=soal)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            catat_riwayat(request.user, soal, CHANGE, "Mengedit soal Kuis")
            messages.success(request, "Pertanyaan kuis berhasil diperbarui.")
            return redirect('daftar_soal_kuis', kuis_id=soal.kuis.id)
    else:
        form = PertanyaanKuisForm(instance=soal)
        formset = PilihanKuisFormSet(instance=soal)

    return render(request, 'pembelajaran/guru_form_soal.html', {
        'form': form,
        'formset': formset,
        'judul_halaman': 'Edit Pertanyaan Kuis',
        'parent_id': soal.kuis.id,
        'tipe': 'kuis'
    })

@login_required
@user_passes_test(is_guru)
def hapus_soal_kuis(request, soal_id):
    soal = get_object_or_404(Pertanyaan, id=soal_id)
    kuis_id = soal.kuis.id
    catat_riwayat(request.user, soal, DELETION, "Menghapus soal Kuis")
    soal.delete()
    messages.success(request, "Pertanyaan berhasil dihapus.")
    return redirect('daftar_soal_kuis', kuis_id=kuis_id)


# --- LOGIKA LATIHAN ---

@login_required
@user_passes_test(is_guru)
def tambah_latihan(request, subbab_id):
    subbab = get_object_or_404(SubBab, id=subbab_id)
    if request.method == 'POST':
        form = LatihanForm(request.POST)
        if form.is_valid():
            latihan = form.save(commit=False)
            latihan.sub_bab = subbab
            latihan.save()
            catat_riwayat(request.user, latihan, ADDITION, "Menambah Latihan baru")
            messages.success(request, "Latihan berhasil ditambahkan.")
            return redirect('guru_kelola_materi')
    else:
        form = LatihanForm()

    return render(request, 'pembelajaran/guru_form_subbab.html', {
        'form': form, 
        'judul_halaman': f'Tambah Latihan di {subbab.judul}'
    })

@login_required
@user_passes_test(is_guru)
def edit_latihan(request, latihan_id):
    latihan = get_object_or_404(Latihan, id=latihan_id)
    if request.method == 'POST':
        form = LatihanForm(request.POST, instance=latihan)
        if form.is_valid():
            form.save()
            catat_riwayat(request.user, latihan, CHANGE, "Mengedit Latihan")
            messages.success(request, "Latihan berhasil diperbarui.")
            return redirect('guru_kelola_materi')
    else:
        form = LatihanForm(instance=latihan)

    return render(request, 'pembelajaran/guru_form_subbab.html', {
        'form': form, 
        'judul_halaman': 'Edit Latihan'
    })

@login_required
@user_passes_test(is_guru)
def hapus_latihan(request, latihan_id):
    latihan = get_object_or_404(Latihan, id=latihan_id)
    catat_riwayat(request.user, latihan, DELETION, f"Menghapus Latihan '{latihan.judul}'")
    latihan.delete()
    messages.success(request, "Latihan berhasil dihapus.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def daftar_soal_latihan(request, latihan_id):
    latihan = get_object_or_404(Latihan, id=latihan_id)
    soal_list = latihan.daftar_soal.all().order_by('urutan')
    return render(request, 'pembelajaran/guru_daftar_soal.html', {
        'parent_obj': latihan,
        'soal_list': soal_list,
        'judul_halaman': f'Daftar Soal: {latihan.judul}',
        'tipe': 'latihan'
    })

@login_required
@user_passes_test(is_guru)
def tambah_soal_latihan(request, latihan_id):
    latihan = get_object_or_404(Latihan, id=latihan_id)
    if request.method == 'POST':
        form = SoalLatihanForm(request.POST)
        formset = PilihanLatihanFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            soal = form.save(commit=False)
            soal.latihan = latihan
            soal.save()
            
            pilihan = formset.save(commit=False)
            for p in pilihan:
                p.soal_latihan = soal
                p.save()
            
            catat_riwayat(request.user, soal, ADDITION, "Menambah soal Latihan")
            messages.success(request, "Soal latihan berhasil ditambahkan.")
            return redirect('daftar_soal_latihan', latihan_id=latihan.id)
    else:
        form = SoalLatihanForm()
        formset = PilihanLatihanFormSet()
        
    return render(request, 'pembelajaran/guru_form_soal.html', {
        'form': form,
        'formset': formset,
        'judul_halaman': 'Tambah Soal Latihan',
        'parent_id': latihan.id,
        'tipe': 'latihan'
    })

@login_required
@user_passes_test(is_guru)
def edit_soal_latihan(request, soal_id):
    soal = get_object_or_404(SoalLatihan, id=soal_id)
    if request.method == 'POST':
        form = SoalLatihanForm(request.POST, instance=soal)
        formset = PilihanLatihanFormSet(request.POST, instance=soal)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            catat_riwayat(request.user, soal, CHANGE, "Mengedit soal Latihan")
            messages.success(request, "Soal latihan berhasil diperbarui.")
            return redirect('daftar_soal_latihan', latihan_id=soal.latihan.id)
    else:
        form = SoalLatihanForm(instance=soal)
        formset = PilihanLatihanFormSet(instance=soal)
        
    return render(request, 'pembelajaran/guru_form_soal.html', {
        'form': form,
        'formset': formset,
        'judul_halaman': 'Edit Soal Latihan',
        'parent_id': soal.latihan.id,
        'tipe': 'latihan'
    })

@login_required
@user_passes_test(is_guru)
def hapus_soal_latihan(request, soal_id):
    soal = get_object_or_404(SoalLatihan, id=soal_id)
    latihan_id = soal.latihan.id
    catat_riwayat(request.user, soal, DELETION, "Menghapus soal Latihan")
    soal.delete()
    messages.success(request, "Soal berhasil dihapus.")
    return redirect('daftar_soal_latihan', latihan_id=latihan_id)

@login_required
@user_passes_test(is_guru)
def tambah_evaluasi(request):
    if request.method == 'POST':
        form = SoalEvaluasiForm(request.POST)
        if form.is_valid():
            obj = form.save()
            catat_riwayat(request.user, obj, ADDITION, "Menambah soal Evaluasi")
            messages.success(request, "Soal Evaluasi berhasil ditambahkan.")
    return redirect('guru_kelola_materi')

@login_required
@user_passes_test(is_guru)
def edit_evaluasi(request, soal_id):
    soal = get_object_or_404(SoalEvaluasi, id=soal_id)
    
    if request.method == 'POST':
        form = SoalEvaluasiForm(request.POST, instance=soal)
        formset = PilihanEvaluasiFormSet(request.POST, instance=soal)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            catat_riwayat(request.user, soal, CHANGE, "Mengedit soal Evaluasi")
            messages.success(request, "Soal Evaluasi dan pilihan jawaban berhasil diperbarui.")
            return redirect('guru_kelola_materi')
    else:
        form = SoalEvaluasiForm(instance=soal)
        formset = PilihanEvaluasiFormSet(instance=soal)
    
    return render(request, 'pembelajaran/guru_form_soal.html', {
        'form': form,
        'formset': formset,
        'judul_halaman': 'Edit Soal Evaluasi',
        'parent_url': 'guru_kelola_materi'
    })

@login_required
@user_passes_test(is_guru)
def hapus_evaluasi(request, soal_id):
    soal = get_object_or_404(SoalEvaluasi, id=soal_id)
    catat_riwayat(request.user, soal, DELETION, "Menghapus soal Evaluasi")
    soal.delete()
    messages.success(request, "Soal Evaluasi berhasil dihapus.")
    return redirect('guru_kelola_materi')