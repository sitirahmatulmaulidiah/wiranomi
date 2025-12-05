# wiranomi_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings             # <-- Tambahan 1
from django.conf.urls.static import static   # <-- Tambahan 2

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pembelajaran.urls')),
]

# --- Tambahkan Blok Ini di Paling Bawah ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)