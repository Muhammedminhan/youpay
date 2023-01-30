from django import forms

from payments.models import Announcement


class AnnouncementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gateway'].required = True
        self.fields['offer_message'].required = True

    class Meta:
        model = Announcement
        fields = '__all__'
