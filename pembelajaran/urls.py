# pembelajaran/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # halaman dashboard & auth (TIDAK BERUBAH)
    path('', views.halaman_dashboard, name='dashboard'),
    path('register/', views.halaman_register, name='register'),
    path('login/', auth_views.LoginView.as_view(
        template_name='pembelajaran/login.html',
        redirect_authenticated_user=True,
        next_page='dashboard'
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='dashboard'
    ), name='logout'),

    # --- JALUR BARU BERBASIS SUBBAB SLUG ---
    
    # Materi: Menggunakan views.detail_materi yang sudah ada
    path('subbab/<slug:slug>/materi/', 
         views.detail_materi, 
         name='subbab_materi'),
    
    # Latihan: Studi Kasus dan Game Drag Drop
    path('subbab/<slug:slug>/latihan/', 
         views.detail_latihan, 
         name='subbab_latihan'), 
    
    # Latihan Pemahaman (Dulu Kuis)
    # Memastikan path dan name sudah menggunakan konvensi baru
    path('subbab/<slug:slug>/latihan-kuis/', 
         views.tampil_kuis,  # Nama fungsi view tetap tampil_kuis
         name='subbab_latihan_kuis'),
    path('subbab/<slug:slug>/latihan-kuis/submit/', 
         views.hitung_kuis,  # Nama fungsi view tetap hitung_kuis
         name='subbab_hitung_latihan'),
         
    # --- JALUR LAMA UNTUK REDIRECT & DAFTAR ---
    
    # Redefinisi halaman_materi lama agar mengarah ke subbab pertama yang baru
    path('materi/', views.halaman_materi_redirect, name='halaman_materi_redirect'), 
    
    # Daftar Latihan (Global)
    # Memperbaiki fungsi view yang dipanggil dari views.daftar_kuis menjadi views.daftar_latihan
    path('latihan/', views.daftar_latihan, name='daftar_latihan'), 

    # fitur kalkulator (TIDAK BERUBAH)
    path('kalkulator/', views.kalkulator_harga_jual, name='kalkulator'),

    # halaman dashboard guru (TIDAK BERUBAH)
    path('guru/', views.guru_dashboard, name='guru_dashboard'),
    path('guru/cek-nilai/', views.guru_cek_nilai, name='guru_cek_nilai'),
    path('guru/cek-nilai/download/', views.guru_download_nilai_csv, name='guru_download_nilai_csv'),
    path('guru/detail-siswa/<int:user_id>/', views.guru_detail_siswa, name='guru_detail_siswa'),
    path('guru/kelola-materi/', views.guru_kelola_materi, name='guru_kelola_materi'),
    path('guru/pengumuman/', views.guru_pengumuman, name='guru_pengumuman'),
    path('guru/pengaturan/', views.guru_pengaturan, name='guru_pengaturan'),
    path('guru/riwayat/', views.guru_riwayat, name='guru_riwayat'),
]