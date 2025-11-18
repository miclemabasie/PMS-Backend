from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget

from apps.core.models import Gender
from apps.users.models import User, Profile


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["email", "username", "first_name", "last_name", "role"]
        error_class = "error"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only superusers can set role; otherwise default to USER
        if not self.current_user or not self.current_user.is_superuser:
            self.fields["role"].disabled = True


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_staff",
        ]
        error_class = "error"


class UserProfileForm(forms.ModelForm):
    phone_number = forms.CharField(required=False)
    bio = forms.CharField(widget=forms.Textarea, required=False)
    profile_photo = forms.ImageField(required=False)
    gender = forms.ChoiceField(choices=Gender.choices, required=False)
    country = forms.ChoiceField(
        choices=[("", "(select country)")] + list(CountryField().choices),
        required=False,
    )
    city = forms.CharField(required=False)
    address = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        self.profile_instance = kwargs.pop("profile_instance", None)
        super().__init__(*args, **kwargs)
        if self.profile_instance:
            for field in [
                "phone_number",
                "bio",
                "profile_photo",
                "gender",
                "country",
                "city",
                "address",
            ]:
                self.fields[field].initial = getattr(self.profile_instance, field)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if self.profile_instance:
            for field in [
                "phone_number",
                "bio",
                "profile_photo",
                "gender",
                "country",
                "city",
                "address",
            ]:
                setattr(self.profile_instance, field, self.cleaned_data[field])
            if commit:
                self.profile_instance.save()
        return user
