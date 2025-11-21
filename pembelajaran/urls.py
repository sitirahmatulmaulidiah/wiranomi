# pembelajaran/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

# JANGAN tambahkan 'admin' atau 'ckeditor' atau 'static' di file ini.
# File ini HANYA untuk URL aplikasi 'pembelajaran'.

urlpatterns = [
    # --- URL Halaman Utama & Auth ---
    path('', views.halaman_dashboard, name='dashboard'),
    path('register/', views.halaman_register, name='register'),
    
    # Login & Logout
    path('login/', auth_views.LoginView.as_view(
        template_name='pembelajaran/login.html',
        redirect_authenticated_user=True,
        next_page='dashboard'
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='dashboard'
    ), name='logout'),

    # --- BAGIAN MATERI & LATIHAN ---
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
    
    # --- URL DASHBOARD GURU ---
    path('guru/', views.guru_dashboard, name='guru_dashboard'),
    path('guru/cek-nilai/', views.guru_cek_nilai, name='guru_cek_nilai'),
    path('guru/cek-nilai/download/', views.guru_download_nilai_csv, name='guru_download_nilai_csv'),
    path('guru/detail-siswa/<int:user_id>/', views.guru_detail_siswa, name='guru_detail_siswa'),
    path('guru/kelola-materi/', views.guru_kelola_materi, name='guru_kelola_materi'),
    path('guru/pengumuman/', views.guru_pengumuman, name='guru_pengumuman'),
    path('guru/pengaturan/', views.guru_pengaturan, name='guru_pengaturan'),
    path('guru/riwayat/', views.guru_riwayat, name='guru_riwayat'),
]