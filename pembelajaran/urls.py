# pembelajaran/urls.py
from django.urls import path, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),

    # URL Halaman Utama & Auth
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

    # URL Pembelajaran (Hanya Materi)
    path('materi/', views.halaman_materi, name='halaman_materi'),
    path('materi/<slug:slug>/', views.detail_materi, name='detail_materi'),
    
    # URL Fitur (Standalone)
    path('kalkulator/', views.kalkulator_harga_jual, name='kalkulator'),
    path('kuis/', views.daftar_kuis, name='daftar_kuis'),
    
    # --- URL KUIS YANG SUDAH DISERDERHANAKAN ---
    # URL ini akan menangani SEMUA kuis
    path('kuis/<slug:slug>/', views.tampil_kuis, name='tampil_kuis'),
    path('kuis/<slug:slug>/submit/', views.hitung_kuis, name='hitung_kuis'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)