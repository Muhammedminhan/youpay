from django import forms
from django.core.exceptions import ValidationError

from integrations.models import (AdditionalChargeConfiguration,
                                 GatewayChargeConfiguration)
from core.constants import (CHARGE_TYPE_FIXED, CHARGE_TYPE_PERCENTAGE,
                            CHARGE_TYPE_FIXED_PERCENTAGE)


class AdditionalChargeConfigurationAdminForm(forms.ModelForm):
    class Meta:
        model = AdditionalChargeConfiguration
        fields = '__all__'

    def clean(self):
        is_active = self.cleaned_data.get('is_active')
        payment_option = self.cleaned_data.get('payment_option')
        percentage = self.cleaned_data.get('percentage')
        fixed_amount = self.cleaned_data.get('fixed_amount')
        charge_type = self.cleaned_data.get('charge_type')
        currency = self.cleaned_data.get('currency')
        instance_id = self.instance.pk if self.instance else None
        obj_exist = AdditionalChargeConfiguration.objects.filter(
            payment_option=payment_option, charge_type=charge_type,
            is_active=True, currency=currency).exclude(pk=instance_id)
        if is_active and obj_exist.exists():
            raise ValidationError('Additional charge already exists '
                                  'for the same payment option.')
        if all([not percentage, not fixed_amount]):
            raise ValidationError('Please add percentage or fixed '
                                  'amount to complete the configuration.')
        return self.cleaned_data

    def clean_percentage(self):
        percentage = self.cleaned_data.get('percentage')
        # percentage validation
        if percentage and (100 < percentage or percentage < 0):
            raise ValidationError('Invalid value for percentage')
        return percentage

    def clean_fixed_amount(self):
        fixed_amount = self.cleaned_data.get('fixed_amount')
        # fixed_amount validation
        if fixed_amount and fixed_amount < 0:
            raise ValidationError('Invalid value for fixed amount')
        return fixed_amount


class GatewayChargeConfigurationAdminForm(forms.ModelForm):
    class Meta:
        model = GatewayChargeConfiguration
        fields = '__all__'

    def clean(self):
        is_active = self.cleaned_data.get('is_active')
        payment_mode = self.cleaned_data.get('payment_mode')
        charge_type = self.cleaned_data.get('charge_type')
        currency = self.cleaned_data.get('currency')
        percentage = self.cleaned_data.get('percentage')
        amount = self.cleaned_data.get('fixed_amount')
        instance_id = self.instance.pk if self.instance else None
        obj_exist = GatewayChargeConfiguration.objects.filter(
            payment_mode=payment_mode, is_active=True,
            charge_type=charge_type, currency=currency).exclude(
            pk=instance_id)
        if is_active and obj_exist.exists():
            raise ValidationError('Gateway charge already exists '
                                  'for the payment mode with same'
                                  ' type and currency.')
        if charge_type == CHARGE_TYPE_FIXED:
            if not amount or percentage:
                raise ValidationError('Please add only amount to complete '
                                      'the configuration.')
        elif charge_type == CHARGE_TYPE_PERCENTAGE:
            if not percentage or amount:
                raise ValidationError(
                    'Please add only percentage to complete '
                    'the configuration.')
        elif (charge_type == CHARGE_TYPE_FIXED_PERCENTAGE and
              not (amount and percentage)):
            raise ValidationError('Please add percentage and amount'
                                  ' to complete the configuration.')
        return self.cleaned_data
