from django import forms
from django.core.exceptions import ValidationError

from payments.models import Announcement, YouPayTransactionData


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
        payment_option = self.cleaned_data.get('payment_option')
        platform = self.cleaned_data.get('platform')
        instance_id = self.instance.pk if self.instance else None
        same_objs = Announcement.objects.filter(
            gateway=gateway, platform=platform,
            payment_option=payment_option,
            is_active=True).exclude(pk=instance_id)
        if is_active and same_objs.exists():
            raise ValidationError('Another announcement is already active for'
                                  ' the chosen gateway-platform-payment '
                                  'option combination')
        return self.cleaned_data


class YouPayTransactionDataAdminForm(forms.ModelForm):
    class Meta:
        model = YouPayTransactionData
        fields = "__all__"
        labels = {
            "points_collected_cic_number": "Points Collected CIC/CIF Number"
        }
