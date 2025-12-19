from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.forms import inlineformset_factory
from ckeditor.widgets import CKEditorWidget 
from .models import (
    PengaturanGuru, Bab, SubBab, Kuis, Latihan, SoalEvaluasi,
    SoalLatihan, PilihanLatihan, Pertanyaan, Pilihan, PilihanJawaban
)


GURU_EMAIL_DOMAIN = '@guru.wiranomi.com'

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(label="Nama Depan", required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label="Nama Belakang", required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, label="Alamat Email", help_text="Wajib diisi. Gunakan email sekolah jika Anda guru.")
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",'first_name', 'last_name', "email")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'password1' in self.fields:
            self.fields['password1'].validators = []
            self.fields['password1'].help_text = None
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email: raise forms.ValidationError("Email wajib diisi.")
        if User.objects.filter(email__iexact=email).exists(): raise forms.ValidationError("Email ini sudah terdaftar.")
        if email.lower().endswith(GURU_EMAIL_DOMAIN): self.is_guru = True
        else: self.is_guru = False
        return email
    def save(self, commit=True):
        pengguna = super().save(commit=False)
        pengguna.first_name = self.cleaned_data["first_name"]
        pengguna.last_name = self.cleaned_data["last_name"]
        pengguna.email = self.cleaned_data["email"]
        if hasattr(self, 'is_guru') and self.is_guru: pengguna.is_staff = True
        else: pengguna.is_staff = False
        if commit: pengguna.save()
        return pengguna

class ProfilSiswaForm(forms.Form):
    first_name = forms.CharField(
        label="Nama Depan",
        max_length=150, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control-custom'})
    )
    last_name = forms.CharField(
        label="Nama Belakang",
        max_length=150, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control-custom'})
    )
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control-custom'})
    )

    password_baru = forms.CharField(
        required=False, 
        label="Ubah Password (Opsional)",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control-custom',
            'placeholder': 'Isi jika ingin mengganti password',
            'autocomplete': 'new-password'
        }),
        help_text="*Biarkan kosong jika tidak ingin mengubah password"        
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        return email

class GuruProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Nama Depan", 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Nama Belakang", 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Email", 
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password_baru = forms.CharField(
        label="Ubah Password (Opsional)", 
        required=False, 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Isi jika ingin mengganti password'}), 
        help_text="Kosongkan jika tidak ingin mengubah password."
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email'] 

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists(): 
            raise forms.ValidationError("Email ini sudah digunakan.")
        return email
    
class PengaturanKKMForm(forms.ModelForm):
    kkm_latihan = forms.IntegerField(label="KKM Latihan", widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}))
    kkm_kuis = forms.IntegerField(label="KKM Kuis Pemahaman", widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}))
    kkm_evaluasi = forms.IntegerField(label="KKM Evaluasi Akhir", widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}))
    class Meta:
        model = PengaturanGuru  
        fields = ['kkm_latihan', 'kkm_kuis', 'kkm_evaluasi']

class BabForm(forms.ModelForm):
    class Meta:
        model = Bab
        fields = ['judul', 'urutan']
        widgets = {
            'judul': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nama Bab'}),
            'urutan': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

class SubBabForm(forms.ModelForm):
    konten = forms.CharField(widget=CKEditorWidget(), label="Isi Materi")
    class Meta:
        model = SubBab
        fields = ['judul', 'konten', 'urutan']
        widgets = {
            'judul': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Judul Sub-Bab'}),
            'urutan': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

class KuisForm(forms.ModelForm):
    class Meta:
        model = Kuis
        fields = ['judul']
        widgets = {'judul': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Judul Kuis'})}

class LatihanForm(forms.ModelForm):
    class Meta:
        model = Latihan
        fields = ['judul']
        widgets = {'judul': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Judul Latihan'})}

class SoalEvaluasiForm(forms.ModelForm):
    pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Pertanyaan")
    
    class Meta:
        model = SoalEvaluasi
        fields = ['pertanyaan', 'urutan'] 
        widgets = {
            'urutan': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

class SoalLatihanForm(forms.ModelForm):
    teks_pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Teks Pertanyaan")
    penjelasan_jawaban = forms.CharField(widget=CKEditorWidget(), label="Pembahasan", required=False)
    
    class Meta:
        model = SoalLatihan
        fields = ['teks_pertanyaan', 'penjelasan_jawaban', 'urutan']

PilihanLatihanFormSet = inlineformset_factory(
    SoalLatihan, PilihanLatihan,
    fields=['teks_pilihan', 'is_jawaban_benar'],
    extra=4, can_delete=True,
    widgets={
        'teks_pilihan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Isi pilihan jawaban'}),
        'is_jawaban_benar': forms.CheckboxInput(attrs={'class': 'form-check-input'})
    }
)

class PertanyaanKuisForm(forms.ModelForm):
    teks_pertanyaan = forms.CharField(widget=CKEditorWidget(), label="Teks Pertanyaan")
    
    class Meta:
        model = Pertanyaan
        fields = ['teks_pertanyaan', 'urutan']

PilihanKuisFormSet = inlineformset_factory(
    Pertanyaan, Pilihan,
    fields=['teks_pilihan', 'is_jawaban_benar'],
    extra=4, can_delete=True,
    widgets={
        'teks_pilihan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Isi pilihan jawaban'}),
        'is_jawaban_benar': forms.CheckboxInput(attrs={'class': 'form-check-input'})
    }
)

PilihanEvaluasiFormSet = inlineformset_factory(
    SoalEvaluasi, PilihanJawaban,
    fields=['teks_pilihan', 'apakah_benar'],
    extra=4, can_delete=True,
    widgets={
        'teks_pilihan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Isi pilihan jawaban'}),
        'apakah_benar': forms.CheckboxInput(attrs={'class': 'form-check-input'})
    }
)