import csv
import json
from django.http import HttpResponse
from django.utils import timezone
from itertools import chain 
from operator import attrgetter
from django.utils.text import slugify 
from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Max
from .models import (
    Bab, SubBab, Kuis, Pertanyaan, Pilihan, 
    GameDragDrop, ItemDragDrop, HasilKuis, UserProgress,
    Latihan, HasilLatihan, SoalLatihan, PilihanLatihan,
    SoalEvaluasi, PilihanJawaban, PengaturanGuru, HasilEvaluasi
)
from .forms import (
    RegisterForm, BabForm, SubBabForm, GuruProfileForm, 
    PengaturanKKMForm, KuisForm, LatihanForm, SoalEvaluasiForm,
    PilihanEvaluasiFormSet, SoalLatihanForm, PilihanLatihanFormSet,
    PertanyaanKuisForm, PilihanKuisFormSet, ProfilSiswaForm
)
from django.contrib.auth import login, authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User 
from datetime import timedelta 
from django.db.models import Prefetch, Count, Q
from .forms import RegisterForm
from django.db.models import Prefetch
from django.contrib.auth import update_session_auth_hash
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType

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

def get_sidebar_context(request):
    semua_bab = Bab.objects.prefetch_related(
        Prefetch('subbab_list', queryset=SubBab.objects.order_by('urutan'))
    ).order_by('urutan')
    
    completed_subbabs = set()
    completed_latihan = set()
    completed_kuis = set()

    if request.user.is_authenticated:
        completed_subbabs = set(UserProgress.objects.filter(
            user=request.user
        ).values_list('subbab_id', flat=True))
        completed_latihan = set(HasilLatihan.objects.filter(
            user=request.user
        ).values_list('latihan__sub_bab_id', flat=True))
        completed_kuis = set(HasilKuis.objects.filter(
            user=request.user
        ).values_list('kuis__subbab_id', flat=True))

    return {
        'semua_bab': semua_bab,
        'completed_subbabs': completed_subbabs,
        'completed_latihan': completed_latihan,
        'completed_kuis': completed_kuis       
    }

def cek_syarat_evaluasi(user):
    """Fungsi untuk mengecek apakah user sudah memenuhi syarat membuka evaluasi akhir."""
    if not user.is_authenticated:
        return False, "Silakan login terlebih dahulu."

    total_kuis_tersedia = Kuis.objects.filter(pertanyaan_set__isnull=False).distinct().count()
    total_latihan_tersedia = Latihan.objects.filter(daftar_soal__isnull=False).distinct().count()
    total_kuis_dikerjakan = HasilKuis.objects.filter(user=user).values('kuis').distinct().count()
    total_latihan_dikerjakan = HasilLatihan.objects.filter(user=user).values('latihan').distinct().count()


    sisa_kuis = max(0, total_kuis_tersedia - total_kuis_dikerjakan)
    sisa_latihan = max(0, total_latihan_tersedia - total_latihan_dikerjakan)

    if sisa_kuis == 0 and sisa_latihan == 0:
        return True, "Evaluasi Terbuka"
    else:
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

def halaman_dashboard(request):
    """Menampilkan halaman dashboard publik."""
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('guru_dashboard') 

    evaluasi_unlocked = False
    pesan_kunci = ""
    sudah_evaluasi = False
    nilai_evaluasi = None

    if request.user.is_authenticated:
        riwayat_eval = HasilEvaluasi.objects.filter(user=request.user).last()
        if riwayat_eval:
            sudah_evaluasi = True
            evaluasi_unlocked = True 
            if riwayat_eval.total_soal > 0:
                nilai_evaluasi = int((riwayat_eval.skor / riwayat_eval.total_soal) * 100)
            else:
                nilai_evaluasi = 0
        else:
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

            nama = user_baru.username
            if user_baru.is_staff:
                pesan = f"Selamat bergabung, Bapak/Ibu Guru {nama}! Akun pengajar Anda siap digunakan."
                target_redirect = 'guru_dashboard'
            else:
                pesan = f"Hore! Selamat datang {nama}. Akun belajarmu sudah siap!"
                target_redirect = 'dashboard'

            messages.success(request, pesan)
            return redirect(target_redirect)
            
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

@login_required
def halaman_materi(request):
    """Mengarahkan ke materi pertama yang ada."""
    materi_pertama = SubBab.objects.order_by('bab__urutan', 'urutan').first()
    if materi_pertama:
        return redirect('detail_materi', slug=materi_pertama.slug)

    konteks = get_sidebar_context(request) 
    konteks = get_sidebar_context(request) 
    konteks['judul'] = "Materi Belum Tersedia"
    return render(request, 'pembelajaran/base.html', konteks) 

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

    is_completed = False
    
    if request.user.is_authenticated:
        is_completed = UserProgress.objects.filter(
            user=request.user, 
            subbab=subbab_aktif
        ).exists()

        if request.method == 'POST' and 'tandai_selesai' in request.POST:
            UserProgress.objects.get_or_create(
                user=request.user,
                subbab=subbab_aktif,
                defaults={'completed_at': timezone.now()}
            )
            is_completed = True
            messages.success(request, "Materi berhasil ditandai selesai! ✅")

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
        'is_completed': is_completed, 
    })
    return render(request, 'pembelajaran/detail_materi.html', konteks)

@login_required
def detail_latihan(request, slug):
    konteks = get_sidebar_context(request)
    subbab = get_object_or_404(SubBab, slug=slug)
    latihan = getattr(subbab, 'latihan', None)
    
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


@login_required
def evaluasi(request):
    is_guru = request.user.is_staff 
    
    semua_soal = SoalEvaluasi.objects.prefetch_related('pilihan').all()
    hasil_nilai = None

    # --- LOGIKA BARU: AMBIL DURASI DARI PENGATURAN GURU ---
    # Kita ambil objek pertama (asumsi admin/guru utama) untuk menentukan batas waktu
    pengaturan = PengaturanGuru.objects.first()
    durasi_menit = pengaturan.durasi_evaluasi if pengaturan else 30 # Default 30 menit jika belum di-setting
    # ------------------------------------------------------

    if request.method == 'POST' and not is_guru:
        # --- 1. AMBIL WAKTU PENGERJAAN DARI FORM ---
        waktu_dihabiskan = request.POST.get('waktu_dihabiskan', 0)
        try:
            waktu_dihabiskan = int(waktu_dihabiskan)
        except (ValueError, TypeError):
            waktu_dihabiskan = 0
        # -------------------------------------------

        skor = 0
        total_soal = semua_soal.count()
        
        for soal in semua_soal:
            pilihan_id = request.POST.get(f'soal_{soal.id}')
            if pilihan_id:
                pilihan_user = soal.pilihan.filter(id=pilihan_id).first()
                if pilihan_user and pilihan_user.apakah_benar:
                    skor += 1
        
        # --- 2. SIMPAN HASIL & WAKTU KE DATABASE ---
        HasilEvaluasi.objects.create(
            user=request.user,
            skor=skor,
            total_soal=total_soal,
            lama_pengerjaan=waktu_dihabiskan  # Menyimpan durasi real yang dipakai siswa
        )

        if total_soal > 0:
            hasil_nilai = int((skor / total_soal) * 100)
        else:
            hasil_nilai = 0

    konteks = {
        'active_page': 'evaluasi', 
        'soal_list': semua_soal,
        'hasil_nilai': hasil_nilai,
        'is_guru': is_guru,
        'durasi_menit': durasi_menit, # <-- Variabel ini penting untuk Timer Mundur di HTML
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
    konteks = get_sidebar_context(request) 
    
    subbab = get_object_or_404(SubBab, slug=slug)
    
    try:
        kuis = Kuis.objects.prefetch_related(
            Prefetch('pertanyaan_set', queryset=Pertanyaan.objects.order_by('urutan').prefetch_related('pilihan_set'))
        ).get(subbab=subbab)
    except Kuis.DoesNotExist:
        kuis = None  # Jika kuis belum dibuat, variabel kuis diisi None

    sudah_mengerjakan = False
    nilai_terakhir = 0
    
    # Cek riwayat HANYA jika kuisnya ada
    if kuis and request.user.is_authenticated:
        riwayat = HasilKuis.objects.filter(user=request.user, kuis=kuis).last()
        if riwayat:
            sudah_mengerjakan = True
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
    
    # --- LOGIKA BARU: Ambil Durasi Pengerjaan ---
    waktu_dihabiskan = request.POST.get('waktu_dihabiskan', 0)
    try:
        # Konversi ke integer (jaga-jaga jika string kosong/error)
        waktu_dihabiskan = int(waktu_dihabiskan)
    except (ValueError, TypeError):
        waktu_dihabiskan = 0
    # --------------------------------------------

    # Proses hitung skor (menggunakan helper function Anda)
    skor, total_soal, hasil_kuis = _proses_hitung_kuis(request, kuis)

    if request.user.is_authenticated and total_soal > 0:
        # Menggunakan update_or_create agar jika user mengerjakan ulang, data diperbarui
        HasilKuis.objects.update_or_create(
            user=request.user,
            kuis=kuis,
            defaults={
                'skor': skor,
                'total_soal': total_soal,
                'tanggal_mengerjakan': timezone.now(),
                'lama_pengerjaan': waktu_dihabiskan  # <-- Simpan durasi di sini
            }
        )

    nilai_akhir = 0
    if total_soal > 0:
        nilai_akhir = int((skor / total_soal) * 100)

    konteks = {
        'subbab': subbab,
        'skor': skor,             
        'total_soal': total_soal, 
        'nilai_akhir': nilai_akhir, 
        'hasil_kuis': hasil_kuis,
        'setengah_soal': total_soal / 2, 
        'active_page': 'kuis', 
        'lama_pengerjaan_formatted': f"{waktu_dihabiskan // 60} menit {waktu_dihabiskan % 60} detik"
    }
    return render(request, 'pembelajaran/hasil_kuis.html', konteks)

@login_required
def view_pengaturan(request):
    user = request.user
    
    if request.method == 'POST':
        form = ProfilSiswaForm(request.POST)
        if form.is_valid():
            # 1. Update Data Profil (Nama Depan, Belakang, Email)
            user.first_name = form.cleaned_data['first_name'] 
            user.last_name = form.cleaned_data['last_name'] 
            user.email = form.cleaned_data['email']
            user.save()

            # 2. Update Password (Jika diisi)
            password_baru = form.cleaned_data.get('password_baru')
            if password_baru:
                user.set_password(password_baru)
                user.save()
                update_session_auth_hash(request, user) # Agar tidak logout otomatis
                messages.success(request, 'Profil dan password berhasil diperbarui!')
            else:
                messages.success(request, 'Profil berhasil diperbarui!')
                
            return redirect('pengaturan')
    else:
        # PENTING: Mengisi form dengan data user saat ini (Initial Data)
        initial_data = {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        }
        form = ProfilSiswaForm(initial=initial_data)

    context = {
        'profil_form': form, 
    }
    return render(request, 'pembelajaran/pengaturan.html', context)


@login_required
@user_passes_test(is_guru)
def guru_dashboard(request):
    total_siswa = User.objects.filter(is_staff=False).count()
    total_materi = SubBab.objects.count()
    siswa_tuntas = HasilEvaluasi.objects.values('user').distinct().count()
    
    waktu_24_jam_lalu = timezone.now() - timedelta(hours=24)
    kuis_selesai = HasilKuis.objects.filter(
        tanggal_mengerjakan__gte=waktu_24_jam_lalu
    ).count()

    context = {
        'total_siswa': total_siswa,
        'total_materi': total_materi,
        'kuis_selesai': kuis_selesai,
        'siswa_tuntas': siswa_tuntas, 
    }
    return render(request, 'pembelajaran/guru_dashboard.html', context)


@login_required
@user_passes_test(is_guru)
def guru_progres_siswa(request):
    # 1. Ambil Total Item yang Harus Dikerjakan (Target)
    total_subbab = SubBab.objects.count()
    total_latihan = Latihan.objects.count()
    total_kuis = Kuis.objects.count()
    # Evaluasi cuma 1, jadi tidak perlu query count

    # 2. Ambil Semua Siswa
    semua_siswa = User.objects.filter(is_staff=False).order_by('first_name')
    
    data_progres = []

    for siswa in semua_siswa:
        # Hitung Materi (Bacaan)
        materi_done = UserProgress.objects.filter(user=siswa).count()
        persen_materi = int((materi_done / total_subbab) * 100) if total_subbab > 0 else 0

        # Hitung Latihan
        # Kita hitung berapa latihan unik yang sudah dikerjakan
        latihan_done = HasilLatihan.objects.filter(user=siswa).values('latihan').distinct().count()
        persen_latihan = int((latihan_done / total_latihan) * 100) if total_latihan > 0 else 0

        # Hitung Kuis
        kuis_done = HasilKuis.objects.filter(user=siswa).values('kuis').distinct().count()
        persen_kuis = int((kuis_done / total_kuis) * 100) if total_kuis > 0 else 0

        # Cek Evaluasi Akhir
        evaluasi = HasilEvaluasi.objects.filter(user=siswa).last()
        nilai_eval = None
        if evaluasi:
            if evaluasi.total_soal > 0:
                nilai_eval = int((evaluasi.skor / evaluasi.total_soal) * 100)
            else:
                nilai_eval = 0

        # Hitung Total Progres Keseluruhan (Rata-rata sederhana)
        # Bobot: Materi(30%) + Latihan(30%) + Kuis(30%) + Evaluasi(10%) -> Contoh Sederhana dirata-rata saja
        komponen_total = 3 + (1 if evaluasi else 0) # Pembagi
        total_percent = (persen_materi + persen_latihan + persen_kuis) 
        if evaluasi: total_percent += 100 # Jika sudah eval dianggap 100% bagian eval
        
        avg_progress = int(total_percent / 4) # Kita bagi 4 komponen utama

        data_progres.append({
            'nama': siswa.get_full_name() or siswa.username,
            'materi_done': materi_done,
            'materi_total': total_subbab,
            'persen_materi': persen_materi,
            
            'latihan_done': latihan_done,
            'latihan_total': total_latihan,
            'persen_latihan': persen_latihan,

            'kuis_done': kuis_done,
            'kuis_total': total_kuis,
            'persen_kuis': persen_kuis,

            'nilai_eval': nilai_eval, # Bisa None, atau Angka (0-100)
            'avg_progress': avg_progress
        })

    context = {
        'data_progres': data_progres,
        'active_page': 'progres'
    }
    return render(request, 'pembelajaran/guru_progres_siswa.html', context)

@login_required
@user_passes_test(is_guru)
def guru_cek_nilai(request):
    # 1. Ambil Pengaturan KKM
    pengaturan, _ = PengaturanGuru.objects.get_or_create(user=request.user)
    KKM_LATIHAN = pengaturan.kkm_latihan
    KKM_KUIS = pengaturan.kkm_kuis
    KKM_EVALUASI = pengaturan.kkm_evaluasi

    # 2. Ambil Parameter Filter
    tipe_filter = request.GET.get('tipe', 'semua')
    status_filter = request.GET.get('status', '') 
    subbab_filter = request.GET.get('subbab', '') 
    siswa_filter = request.GET.get('siswa', '')   

    # 3. Query Data
    qs_kuis = HasilKuis.objects.select_related('user', 'kuis__subbab').filter(user__is_staff=False)
    qs_latihan = HasilLatihan.objects.select_related('user', 'latihan__sub_bab').filter(user__is_staff=False)
    qs_evaluasi = HasilEvaluasi.objects.select_related('user').filter(user__is_staff=False)

    # 4. Gabungkan Data
    daftar_hasil = []
    if tipe_filter == 'kuis':
        daftar_hasil = list(qs_kuis)
    elif tipe_filter == 'latihan':
        daftar_hasil = list(qs_latihan)
    elif tipe_filter == 'evaluasi':
        daftar_hasil = list(qs_evaluasi)
    else:
        daftar_hasil = list(chain(qs_kuis, qs_latihan, qs_evaluasi))

    # 5. Proses Data
    daftar_nilai_processed = []
    
    for hasil in daftar_hasil:
        is_lulus = False
        subbab_id = None
        user_id = hasil.user.id
        
        # Variable baru untuk durasi string
        durasi_str = "-" 

        if isinstance(hasil, HasilKuis):
            hasil.tipe_label = "Kuis"
            hasil.judul_konten = hasil.kuis.judul
            hasil.nama_subbab = hasil.kuis.subbab.judul if hasil.kuis.subbab else "-"
            subbab_id = hasil.kuis.subbab.id if hasil.kuis.subbab else None
            hasil.tanggal_sort = hasil.tanggal_mengerjakan
            
            # Hitung Durasi Kuis
            menit = hasil.lama_pengerjaan // 60
            detik = hasil.lama_pengerjaan % 60
            durasi_str = f"{menit}m {detik}d"

            if hasil.total_soal > 0:
                hasil.skor = int((hasil.skor / hasil.total_soal) * 100)
            else:
                hasil.skor = 0
            
            hasil.total_soal = 100
            is_lulus = hasil.skor >= KKM_KUIS

        elif isinstance(hasil, HasilLatihan):
            hasil.tipe_label = "Latihan"
            hasil.judul_konten = hasil.latihan.judul
            hasil.nama_subbab = hasil.latihan.sub_bab.judul if hasil.latihan.sub_bab else "-"
            subbab_id = hasil.latihan.sub_bab.id if hasil.latihan.sub_bab else None
            hasil.tanggal_sort = hasil.tanggal_kumpul
            hasil.skor = hasil.nilai 
            hasil.total_soal = 100
            is_lulus = hasil.nilai >= KKM_LATIHAN
            durasi_str = "-" # Latihan tidak ada durasi

        elif isinstance(hasil, HasilEvaluasi):
            hasil.tipe_label = "Evaluasi"
            hasil.judul_konten = "Evaluasi Akhir"
            hasil.nama_subbab = "-"
            hasil.tanggal_sort = hasil.tanggal_mengerjakan
            
            # Hitung Durasi Evaluasi
            menit = hasil.lama_pengerjaan // 60
            detik = hasil.lama_pengerjaan % 60
            durasi_str = f"{menit}m {detik}d"

            if hasil.total_soal > 0:
                hasil.skor = int((hasil.skor / hasil.total_soal) * 100)
            else:
                hasil.skor = 0
            
            hasil.total_soal = 100
            is_lulus = hasil.skor >= KKM_EVALUASI

        hasil.lulus = is_lulus
        hasil.durasi_display = durasi_str # Simpan ke objek hasil

        # --- LOGIKA FILTERING ---
        if status_filter == 'lulus' and not is_lulus: continue
        if status_filter == 'gagal' and is_lulus: continue

        if subbab_filter and tipe_filter in ['kuis', 'latihan']:
            if str(subbab_id) != str(subbab_filter): continue

        if siswa_filter and tipe_filter in ['kuis', 'latihan']:
            if str(user_id) != str(siswa_filter): continue

        daftar_nilai_processed.append(hasil)
    
    daftar_nilai_processed.sort(key=attrgetter('tanggal_sort'), reverse=True)
    
    list_subbab = SubBab.objects.all().order_by('urutan')
    list_siswa = User.objects.filter(is_staff=False).order_by('first_name')

    context = {
        'daftar_nilai': daftar_nilai_processed,
        'tipe_aktif': tipe_filter,
        'list_subbab': list_subbab,
        'list_siswa': list_siswa,
        'filter_status': status_filter,
        'filter_subbab': int(subbab_filter) if subbab_filter else '',
        'filter_siswa': int(siswa_filter) if siswa_filter else '',
    }
    return render(request, 'pembelajaran/guru_cek_nilai.html', context)


@login_required
@user_passes_test(is_guru)
def guru_download_nilai_csv(request):
    # 1. Ambil Pengaturan KKM
    pengaturan, _ = PengaturanGuru.objects.get_or_create(user=request.user)
    KKM_LATIHAN = pengaturan.kkm_latihan
    KKM_KUIS = pengaturan.kkm_kuis
    KKM_EVALUASI = pengaturan.kkm_evaluasi

    # 2. Ambil Parameter Filter (Sama persis dengan halaman cek nilai)
    tipe_filter = request.GET.get('tipe', 'semua')
    status_filter = request.GET.get('status', '') 
    subbab_filter = request.GET.get('subbab', '') 
    siswa_filter = request.GET.get('siswa', '')   

    # 3. Query Data Awal
    qs_kuis = HasilKuis.objects.select_related('user', 'kuis__subbab').filter(user__is_staff=False)
    qs_latihan = HasilLatihan.objects.select_related('user', 'latihan__sub_bab').filter(user__is_staff=False)
    qs_evaluasi = HasilEvaluasi.objects.select_related('user').filter(user__is_staff=False)

    # 4. Gabungkan Data Sesuai Tipe
    daftar_hasil = []
    if tipe_filter == 'kuis':
        daftar_hasil = list(qs_kuis)
    elif tipe_filter == 'latihan':
        daftar_hasil = list(qs_latihan)
    elif tipe_filter == 'evaluasi':
        daftar_hasil = list(qs_evaluasi)
    else:
        daftar_hasil = list(chain(qs_kuis, qs_latihan, qs_evaluasi))

    # 5. Proses Data & Terapkan Filter (Logic ini diduplikasi dari guru_cek_nilai agar hasil sama)
    daftar_nilai_processed = []
    
    for hasil in daftar_hasil:
        is_lulus = False
        subbab_id = None
        user_id = hasil.user.id
        
        # Variabel untuk CSV
        tipe_label = ""
        judul_konten = ""
        nama_subbab = "-"
        durasi_str = "-"
        tanggal_sort = timezone.now()
        skor_final = 0
        total_soal = 100

        if isinstance(hasil, HasilKuis):
            tipe_label = "Kuis"
            judul_konten = hasil.kuis.judul
            nama_subbab = hasil.kuis.subbab.judul if hasil.kuis.subbab else "-"
            subbab_id = hasil.kuis.subbab.id if hasil.kuis.subbab else None
            tanggal_sort = hasil.tanggal_mengerjakan
            
            # Hitung Durasi
            menit = hasil.lama_pengerjaan // 60
            detik = hasil.lama_pengerjaan % 60
            durasi_str = f"{menit}m {detik}d"

            if hasil.total_soal > 0:
                skor_final = int((hasil.skor / hasil.total_soal) * 100)
            
            is_lulus = skor_final >= KKM_KUIS

        elif isinstance(hasil, HasilLatihan):
            tipe_label = "Latihan"
            judul_konten = hasil.latihan.judul
            nama_subbab = hasil.latihan.sub_bab.judul if hasil.latihan.sub_bab else "-"
            subbab_id = hasil.latihan.sub_bab.id if hasil.latihan.sub_bab else None
            tanggal_sort = hasil.tanggal_kumpul
            skor_final = hasil.nilai 
            is_lulus = skor_final >= KKM_LATIHAN
            durasi_str = "-" 

        elif isinstance(hasil, HasilEvaluasi):
            tipe_label = "Evaluasi"
            judul_konten = "Evaluasi Akhir"
            nama_subbab = "-"
            tanggal_sort = hasil.tanggal_mengerjakan
            
            menit = hasil.lama_pengerjaan // 60
            detik = hasil.lama_pengerjaan % 60
            durasi_str = f"{menit}m {detik}d"

            if hasil.total_soal > 0:
                skor_final = int((hasil.skor / hasil.total_soal) * 100)
            
            is_lulus = skor_final >= KKM_EVALUASI

        # --- LOGIKA FILTERING ---
        if status_filter == 'lulus' and not is_lulus: continue
        if status_filter == 'gagal' and is_lulus: continue

        if subbab_filter and tipe_filter in ['kuis', 'latihan']:
            if str(subbab_id) != str(subbab_filter): continue

        if siswa_filter and tipe_filter in ['kuis', 'latihan']:
            if str(user_id) != str(siswa_filter): continue

        # Simpan data yang sudah bersih ke dictionary sementara untuk ditulis ke CSV
        daftar_nilai_processed.append({
            'user': hasil.user,
            'tipe': tipe_label,
            'subbab': nama_subbab,
            'judul': judul_konten,
            'durasi': durasi_str,
            'skor': skor_final,
            'status': "Lulus" if is_lulus else "Remidi",
            'tanggal': tanggal_sort
        })
    
    # Sort data sesuai tanggal terbaru
    daftar_nilai_processed.sort(key=lambda x: x['tanggal'], reverse=True)

    # 6. Generate CSV
    nama_file = f"Laporan_Nilai_{tipe_filter.capitalize()}_{timezone.now().strftime('%d-%m-%Y')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{nama_file}"'
    
    # Tambahkan BOM untuk Excel agar bisa baca karakter utf-8 dengan benar
    response.write(u'\ufeff'.encode('utf8'))
    
    writer = csv.writer(response, delimiter=';') # Gunakan titik koma agar rapi di Excel Indonesia

    # Header CSV
    writer.writerow([
        'No',
        'Nama Siswa',
        'Username',
        'Sub-Materi',
        'Judul Kegiatan',
        'Tipe',
        'Lama Pengerjaan',
        'Skor Akhir',
        'Status KKM',
        'Waktu Selesai'
    ])

    # Isi Data
    no_urut = 1
    for item in daftar_nilai_processed:
        nama_siswa = f"{item['user'].first_name} {item['user'].last_name}".strip()
        if not nama_siswa:
            nama_siswa = item['user'].username

        # Format Tanggal
        tgl_str = timezone.localtime(item['tanggal']).strftime('%d/%m/%Y %H:%M')

        writer.writerow([
            no_urut,
            nama_siswa,
            item['user'].username,
            item['subbab'],
            item['judul'],
            item['tipe'],
            item['durasi'],
            item['skor'],
            item['status'], # Lulus / Remidi
            tgl_str
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
    logs = LogEntry.objects.filter(user=request.user).select_related('content_type', 'user').order_by('-action_time')[:20]
    
    daftar_log = []
    for log in logs:
        if log.action_flag == ADDITION:
            tipe = "TAMBAH"
            aksi_text = "menambahkan"
        elif log.action_flag == CHANGE:
            tipe = "EDIT"
            aksi_text = "mengedit"
        elif log.action_flag == DELETION:
            tipe = "HAPUS"
            aksi_text = "menghapus"
        else:
            tipe = "INFO"
            aksi_text = "melakukan aksi pada"

        detail_perubahan = ""
        if log.change_message and log.change_message != '[]':
            try:
                data_json = json.loads(log.change_message)
                list_pesan = []
                
                if isinstance(data_json, list):
                    for item in data_json:
                        if 'changed' in item:
                            field_list = item['changed'].get('fields', [])
                            if field_list:
                                list_pesan.append(f"mengubah {', '.join(field_list)}")
                        elif 'added' in item:
                            nama_objek = item['added'].get('name', 'item')
                            list_pesan.append(f"menambahkan {nama_objek}")
                        elif 'deleted' in item:
                            nama_objek = item['deleted'].get('name', 'item')
                            list_pesan.append(f"menghapus {nama_objek}")
                
                if list_pesan:
                    detail_perubahan = f" ({', '.join(list_pesan)})"
                else:
                    detail_perubahan = "" 
            except json.JSONDecodeError:
                detail_perubahan = f" - {log.change_message}"

        deskripsi = f'Anda {aksi_text} {log.content_type.name} "{log.object_repr}"{detail_perubahan}.'
        tanggal = timezone.localtime(log.action_time).strftime('%d %b %Y, %H:%M')
        daftar_log.append({
            'tipe': tipe,
            'tanggal': tanggal,
            'deskripsi': deskripsi,
            'user': log.user.username, 
        })

    context = {
        'daftar_log': daftar_log
    }
    return render(request, 'pembelajaran/guru_riwayat.html', context)

@login_required
@user_passes_test(is_guru)
def guru_kelola_materi(request):
    context = {
        'semua_bab': Bab.objects.prefetch_related('subbab_list__kuis', 'subbab_list__latihan').order_by('urutan'),
        'semua_evaluasi': SoalEvaluasi.objects.all().order_by('urutan'), 
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

            base_url = reverse('guru_kelola_materi')
            return redirect(f"{base_url}?active_bab={subbab.bab.id}&active_subbab={subbab.id}")
    else:
        form = LatihanForm()

    return render(request, 'pembelajaran/guru_form_input.html', {
        'form': form, 
        'judul_halaman': f'Tambah Latihan di {subbab.judul}',
        'tombol_simpan': 'Simpan Latihan',
        'subbab': subbab 
    })

@login_required
@user_passes_test(is_guru)
def edit_latihan(request, latihan_id):
    latihan = get_object_or_404(Latihan, id=latihan_id)
    subbab = latihan.sub_bab 
    
    if request.method == 'POST':
        form = LatihanForm(request.POST, instance=latihan)
        if form.is_valid():
            form.save()
            catat_riwayat(request.user, latihan, CHANGE, "Mengedit Latihan")
            messages.success(request, "Latihan berhasil diperbarui.")

            base_url = reverse('guru_kelola_materi')
            return redirect(f"{base_url}?active_bab={subbab.bab.id}&active_subbab={subbab.id}")
    else:
        form = LatihanForm(instance=latihan)

    return render(request, 'pembelajaran/guru_form_input.html', {
        'form': form, 
        'judul_halaman': 'Edit Latihan',
        'tombol_simpan': 'Simpan Perubahan',
        'subbab': subbab 
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


@login_required
@user_passes_test(is_guru)
def guru_daftar_siswa(request):
    daftar_siswa = User.objects.filter(is_staff=False).order_by('first_name')
    
    context = {
        'daftar_siswa': daftar_siswa,
        'active_page': 'siswa'
    }
    return render(request, 'pembelajaran/guru_daftar_siswa.html', context)

@login_required
@user_passes_test(is_guru)
def guru_reset_password_siswa(request, user_id):
    if request.method == 'POST':
        siswa = get_object_or_404(User, id=user_id)
        password_baru = request.POST.get('password_baru')
        
        if password_baru:
            siswa.set_password(password_baru)
            siswa.save()
            try:
                catat_riwayat(request.user, siswa, CHANGE, f"Mereset password siswa: {siswa.username}")
            except:
                pass
            messages.success(request, f"Password untuk {siswa.first_name} berhasil diubah.")
        else:
            messages.error(request, "Password tidak boleh kosong.")
            
    return redirect('guru_daftar_siswa')

@login_required
@user_passes_test(is_guru)
def guru_tambah_siswa(request):
    if request.method == 'POST':
        nama_depan = request.POST.get('first_name')
        nama_belakang = request.POST.get('last_name', '')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan.")
        else:
            try:
                siswa_baru = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=nama_depan,
                    last_name=nama_belakang
                )
                catat_riwayat(request.user, siswa_baru, ADDITION, "Menambahkan siswa baru")
                messages.success(request, f"Siswa {nama_depan} berhasil ditambahkan.")
            except Exception as e:
                messages.error(request, f"Gagal menambah siswa: {e}")
            
    return redirect('guru_daftar_siswa')

@login_required
@user_passes_test(is_guru)
def guru_reset_password_siswa(request, user_id):
    if request.method == 'POST':
        siswa = get_object_or_404(User, id=user_id)
        password_baru = request.POST.get('password_baru')
        
        if password_baru:
            siswa.set_password(password_baru)
            siswa.save()
            catat_riwayat(request.user, siswa, CHANGE, f"Mereset password siswa: {siswa.username}")
            messages.success(request, f"Password untuk {siswa.first_name} berhasil diubah.")
        else:
            messages.error(request, "Password tidak boleh kosong.")
            
    return redirect('guru_daftar_siswa')

@login_required
@user_passes_test(is_guru)
def guru_edit_siswa(request, user_id):
    if request.method == 'POST':
        siswa = get_object_or_404(User, id=user_id)
        
        siswa.first_name = request.POST.get('first_name')
        siswa.last_name = request.POST.get('last_name')
        siswa.email = request.POST.get('email')
        siswa.save()
        
        catat_riwayat(request.user, siswa, CHANGE, "Mengedit data siswa")
        messages.success(request, "Data siswa berhasil diperbarui.")
        
    return redirect('guru_daftar_siswa')

@login_required
@user_passes_test(is_guru)
def guru_hapus_siswa(request, user_id):
    if request.method == 'POST':
        siswa = get_object_or_404(User, id=user_id)
        nama_siswa = siswa.first_name
        
        catat_riwayat(request.user, siswa, DELETION, f"Menghapus siswa {nama_siswa}")
        siswa.delete()
        messages.success(request, f"Data siswa {nama_siswa} berhasil dihapus.")
        
    return redirect('guru_daftar_siswa')