# pembelajaran/urls.py
from django.contrib import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # halaman dashboard & auth
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

    # halaman materi
    path('materi/', views.halaman_materi, name='halaman_materi'),
    path('materi/<slug:slug>/', views.detail_materi, name='detail_materi'),
    
    # fitur kalkulator dan kuis
    path('kalkulator/', views.kalkulator_harga_jual, name='kalkulator'),
    path('kuis/', views.daftar_kuis, name='daftar_kuis'),
    path('kuis/<slug:slug>/', views.tampil_kuis, name='tampil_kuis'),
    path('kuis/<slug:slug>/submit/', views.hitung_kuis, name='hitung_kuis'),

    # halaman dashboard guru
    path('guru/', views.guru_dashboard, name='guru_dashboard'),
    path('guru/cek-nilai/', views.guru_cek_nilai, name='guru_cek_nilai'),
    path('guru/cek-nilai/download/', views.guru_download_nilai_csv, name='guru_download_nilai_csv'),
    path('guru/detail-siswa/<int:user_id>/', views.guru_detail_siswa, name='guru_detail_siswa'),
    path('guru/kelola-materi/', views.guru_kelola_materi, name='guru_kelola_materi'),
    path('guru/pengumuman/', views.guru_pengumuman, name='guru_pengumuman'),
    path('guru/pengaturan/', views.guru_pengaturan, name='guru_pengaturan'),
    path('guru/riwayat/', views.guru_riwayat, name='guru_riwayat'),
]