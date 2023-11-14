import re

from django import forms

from services.models import APIClient


class APIClientForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['logo_file'].required = True
        self.fields['mobile_logo_file'].required = True
        self.fields['color_code'].required = True

    class Meta:
        model = APIClient
        fields = '__all__'

    def clean_color_code(self):
        color_code = self.cleaned_data.get("color_code")
        if color_code is None or color_code == '':
            raise forms.ValidationError('Color code is required')
        # validation for color code
        if color_code and not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$',
                                       color_code):
            raise forms.ValidationError(
                'Color code should be in the format '
                '#XXXXX or #XXX, where X is a hex value')
        return color_code
