from django import forms

from payments.models import Announcement


class AnnouncementForm(forms.ModelForm):
    offer_message = forms.CharField(
        max_length=95, widget=forms.Textarea
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gateway'].required = True
        self.fields['offer_message'].required = True

    class Meta:
        model = Announcement
        fields = '__all__'
