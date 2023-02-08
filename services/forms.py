from django import forms
from django.core.files.images import get_image_dimensions

from services.models import APIClient
from services.constants import (CLIENT_LOGO_MAX_SIZE, CLIENT_LOGO_MAX_HEIGHT,
                                ONE_MB)


class APIClientForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True

    class Meta:
        model = APIClient
        fields = '__all__'

    def clean_logo_file(self):
        picture = self.cleaned_data.get("logo_file")
        if not picture:
            raise forms.ValidationError("No logo image!")
        else:
            if picture.size > CLIENT_LOGO_MAX_SIZE:
                size_mb = CLIENT_LOGO_MAX_SIZE / ONE_MB
                raise forms.ValidationError(
                    "The image size is above {} MB".format(size_mb))
            w, h = get_image_dimensions(picture)
            if h > CLIENT_LOGO_MAX_HEIGHT:
                raise forms.ValidationError(
                    "The image is {} pixel high. It's supposed to be "
                    "{} px max".format(h, CLIENT_LOGO_MAX_HEIGHT))
        return picture
