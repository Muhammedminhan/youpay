from django import forms
from django.core.exceptions import ValidationError

from integrations.models import AdditionalChargeConfiguration


class AdditionalChargeConfigurationAdminForm(forms.ModelForm):
    class Meta:
        model = AdditionalChargeConfiguration
        fields = '__all__'

    def clean(self):
        is_active = self.cleaned_data.get('is_active')
        payment_option = self.cleaned_data.get('payment_option')
        percentage = self.cleaned_data.get('percentage')
        fixed_amount = self.cleaned_data.get('fixed_amount')
        instance_id = self.instance.pk if self.instance else None
        obj_exist = AdditionalChargeConfiguration.objects.filter(
            payment_option=payment_option,
            is_active=True).exclude(pk=instance_id)
        if is_active and obj_exist.exists():
            raise ValidationError('Additional charge already exists '
                                  'for the same payment option.')
        if all([not percentage, not fixed_amount]):
            raise ValidationError('Please add percentage or fixed '
                                  'amount to complete the configuration.')
        return self.cleaned_data
