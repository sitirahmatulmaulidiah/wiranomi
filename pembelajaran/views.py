import cvs
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
from datetime import timedelta 
from django.db.models import Prefetch

def get_sidebar_context():
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
        'active_page': 'kuis', 
    }
    return render(request, 'pembelajaran/hasil_kuis.html', konteks)

