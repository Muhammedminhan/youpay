from django import forms
from django.core.exceptions import ValidationError

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

    def clean(self):
        is_active = self.cleaned_data.get('is_active')
        gateway = self.cleaned_data.get('gateway')
        platform = self.cleaned_data.get('platform')
        instance_id = self.instance.pk if self.instance else None
        same_objs = Announcement.objects.filter(
                gateway=gateway, platform=platform,
                is_active=True).exclude(pk=instance_id)
        if is_active and same_objs.exists():
            raise ValidationError('Another announcement is already active for'
                                  ' the chosen gateway-platform combination')
        return self.cleaned_data
