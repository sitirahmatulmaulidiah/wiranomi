# pembelajaran/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.halaman_dashboard, name='dashboard'),
    path('register/', views.halaman_register, name='register'),
    path('login/', views.login_view, name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='dashboard'
    ), name='logout'),

    path('pengaturan/', views.view_pengaturan, name='pengaturan'),

    # Materi
    path('materi/', views.halaman_materi, name='halaman_materi'),
    
    # 1. Halaman Materi (Teori)
    path('materi/<slug:slug>/', views.detail_materi, name='detail_materi'),
    
    # 2. Halaman Latihan
    path('materi/<slug:slug>/latihan/', views.detail_latihan, name='detail_latihan'),
    
    # 3. Submit Latihan (URL Khusus untuk memproses jawaban)
    path('latihan/<int:latihan_id>/submit/', views.submit_latihan, name='submit_latihan'),
    
    # --- BAGIAN FITUR LAIN (KUIS, KALKULATOR & EVALUASI) ---
    path('kalkulator/', views.kalkulator_harga_jual, name='kalkulator'),
    
    # URL Evaluasi Akhir (BARU DITAMBAHKAN)
    path('evaluasi/', views.evaluasi, name='evaluasi'),
    
    path('kuis/', views.daftar_kuis, name='daftar_kuis'),
    
    # 4. Halaman Kuis
    path('kuis/<slug:slug>/', views.tampil_kuis, name='tampil_kuis'),
    path('kuis/<slug:slug>/submit/', views.hitung_kuis, name='hitung_kuis'),
    
    # Guru
    path('guru/', views.guru_dashboard, name='guru_dashboard'),
    path('guru/cek-nilai/', views.guru_cek_nilai, name='guru_cek_nilai'),
    path('guru/cek-nilai/download/', views.guru_download_nilai_csv, name='guru_download_nilai_csv'),
    path('guru/detail-siswa/<int:user_id>/', views.guru_detail_siswa, name='guru_detail_siswa'),
    path('guru/pengaturan/', views.guru_pengaturan, name='guru_pengaturan'),
    path('guru/riwayat/', views.guru_riwayat, name='guru_riwayat'),
    path('guru/kelola-materi/', views.guru_kelola_materi, name='guru_kelola_materi'),
    
    # Aksi BAB
    path('guru/bab/tambah/', views.tambah_bab, name='tambah_bab'),
    path('guru/bab/edit/<int:bab_id>/', views.edit_bab, name='edit_bab'),
    path('guru/bab/hapus/<int:bab_id>/', views.hapus_bab, name='hapus_bab'),

    # Aksi SUB-BAB
    path('guru/subbab/tambah/<int:bab_id>/', views.tambah_subbab, name='tambah_subbab'),
    path('guru/subbab/edit/<int:subbab_id>/', views.edit_subbab, name='edit_subbab'),
    path('guru/subbab/hapus/<int:subbab_id>/', views.hapus_subbab, name='hapus_subbab'),

    # --- KELOLA KUIS ---
    path('guru/kuis/kelola/<int:subbab_id>/', views.kelola_kuis, name='kelola_kuis'),
    path('guru/kuis/hapus/<int:kuis_id>/', views.hapus_kuis, name='hapus_kuis'),
    # Detail Soal Kuis
    path('guru/kuis/<int:kuis_id>/soal/', views.daftar_soal_kuis, name='daftar_soal_kuis'),
    path('guru/kuis/<int:kuis_id>/soal/tambah/', views.tambah_soal_kuis, name='tambah_soal_kuis'),
    path('guru/kuis/soal/edit/<int:soal_id>/', views.edit_soal_kuis, name='edit_soal_kuis'),
    path('guru/kuis/soal/hapus/<int:soal_id>/', views.hapus_soal_kuis, name='hapus_soal_kuis'),

    # --- KELOLA LATIHAN ---
    path('guru/latihan/tambah/<int:subbab_id>/', views.tambah_latihan, name='tambah_latihan'),
    path('guru/latihan/edit/<int:latihan_id>/', views.edit_latihan, name='edit_latihan'),
    path('guru/latihan/hapus/<int:latihan_id>/', views.hapus_latihan, name='hapus_latihan'),
    # Detail Soal Latihan
    path('guru/latihan/<int:latihan_id>/soal/', views.daftar_soal_latihan, name='daftar_soal_latihan'),
    path('guru/latihan/<int:latihan_id>/soal/tambah/', views.tambah_soal_latihan, name='tambah_soal_latihan'),
    path('guru/latihan/soal/edit/<int:soal_id>/', views.edit_soal_latihan, name='edit_soal_latihan'),
    path('guru/latihan/soal/hapus/<int:soal_id>/', views.hapus_soal_latihan, name='hapus_soal_latihan'),

    # --- KELOLA EVALUASI ---
    path('guru/evaluasi/tambah/', views.tambah_evaluasi, name='tambah_evaluasi'),
    path('guru/evaluasi/edit/<int:soal_id>/', views.edit_evaluasi, name='edit_evaluasi'),
    path('guru/evaluasi/hapus/<int:soal_id>/', views.hapus_evaluasi, name='hapus_evaluasi'),
]