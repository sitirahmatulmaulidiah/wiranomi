from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

GURU_EMAIL_DOMAIN = '@guru.wiranomi.com'

class RegisterForm(UserCreationForm):
    
    email = forms.EmailField(
        required=True, 
        label="Alamat Email",
        help_text="Wajib diisi. Gunakan email sekolah jika Anda guru."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].validators = []
        self.fields['password1'].help_text = None

    def clean_email(self):
        """
        Validasi email dan tentukan apakah user adalah guru atau murid.
        """
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email wajib diisi.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email ini sudah terdaftar. Silakan gunakan email lain.")
        if email.lower().endswith(GURU_EMAIL_DOMAIN):
            self.is_guru = True
        else:
            self.is_guru = False
            
        return email

    def clean_password2(self):
        sandi_1 = self.cleaned_data.get("password1")
        sandi_2 = self.cleaned_data.get("password2")

        if sandi_1 and sandi_2 and sandi_1 != sandi_2:
            raise forms.ValidationError(
                "Password tidak cocok. Silakan coba lagi.",
                code='password_mismatch'
            )
        return sandi_2

    def save(self, commit=True):
        pengguna = super().save(commit=False)
        pengguna.email = self.cleaned_data["email"]
        if hasattr(self, 'is_guru') and self.is_guru:
            pengguna.is_staff = True
        else:
            pengguna.is_staff = False
            
        if commit:
            pengguna.save()
        return pengguna