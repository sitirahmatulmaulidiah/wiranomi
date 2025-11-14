from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegisterForm(UserCreationForm):
    
    email = forms.EmailField(
        required=True, 
        label="Alamat Email",
        help_text="Wajib diisi. Kami tidak akan membagikan email Anda."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].validators = []
        self.fields['password1'].help_text = None

    def clean_password2(self):
        sandi_1 = self.cleaned_data.get("password1")
        sandi_2 = self.cleaned_data.get("password2")

        if sandi_1 and sandi_2 and sandi_1 != sandi_2:
            # Tampilkan error HANYA jika password tidak cocok
            raise forms.ValidationError(
                "Password tidak cocok. Silakan coba lagi.",
                code='password_mismatch'
            )
        return sandi_2

    def save(self, commit=True):
        pengguna = super().save(commit=False)
        pengguna.email = self.cleaned_data["email"]
        if commit:
            pengguna.save()
        return pengguna