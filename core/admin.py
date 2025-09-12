import logging

from django import forms
from django.contrib import admin
from django.core.cache import cache

from integrations.constants import B2CPAYBACK_HUB_CODE
from payments.constants import PAYMENT_METHOD_QITAF, PAYMENT_METHOD_ANB, \
    PAYMENT_METHOD_NEQATY, PAYMENT_METHOD_ADCB
from .constants import (GUEST_USER_ENABLE, GUEST_USER_DISABLE,
                        GUEST_USER_CUSTOM, BETA_USER_ONLY_EARN,
                        BETA_USER_ONLY_BURN)
from .models import (AppConfig, Currency, Country, PaymentConfiguration,
                     PaymentMethodConfig, BetaUser)
from .utils import invalidate_cached_payment_method_config

admin.site.site_header = 'YouPay Administration'

logger = logging.getLogger(__name__)


class AdminAbstract(admin.ModelAdmin):
    readonly_fields = (
        'created_at', 'updated_at', 'created_by', 'modified_by')
    exclude = ('created_by', 'modified_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        if form.changed_data:
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class AppConfigAdmin(admin.ModelAdmin):
    list_display = ('front_end_domain', 'created_at', 'updated_at')
    readonly_fields = (
        'created_at', 'updated_at', 'created_by', 'modified_by')
    exclude = ('created_by', 'modified_by', 'created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        if form.changed_data:
            try:
                cache.delete('app_config')
            except (TypeError, AttributeError):
                logging.error(
                    'Error while clearing bulk order config cache')

            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class CurrencyAdmin(AdminAbstract):
    list_display = ('iso_code', 'name', 'decimal_notation',
                    'created_at', 'updated_at')
    search_fields = ('iso_code', 'name',)
    list_filter = ('created_by',)


class CountryAdmin(AdminAbstract):
    list_display = ('name', 'iso_code', 'flag', 'currency',
                    'is_gcc', 'created_at')
    search_fields = ('name', 'iso_code', 'currency')
    list_filter = ('currency', 'is_gcc', 'three_letter_code',)
    raw_id_fields = ('currency',)


class PaymentMethodConfigAdmin(admin.ModelAdmin):
    list_display = ('payment_method', 'client', 'country', 'active',
                    'guest_user_enabled')
    search_fields = ('payment_method__payment_method',)
    list_filter = ('payment_method', 'active', 'guest_user_enabled',
                   'client', 'country')
    list_editable = ('client', 'country', 'active', 'guest_user_enabled')

    def save_model(self, request, obj, form, change):
        invalidate_cached_payment_method_config()
        super().save_model(request, obj, form, change)


class SliderCheckboxInput(forms.CheckboxInput):
    template_name = 'core/admin/widgets/slider_checkbox.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        return context


class PaymentMethodConfigAdminForm(forms.ModelForm):
    class Meta:
        model = PaymentMethodConfig
        fields = '__all__'
        widgets = {
            'active': SliderCheckboxInput(),
            'guest_user_enabled': SliderCheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].required = True
        self.fields['payment_method'].required = True


class PaymentMethodConfigInlineFormset(forms.models.BaseInlineFormSet):

    def clean(self):
        super().clean()

        parent_instance = self.instance
        if parent_instance.active:
            total_active_configs = sum(
                form.cleaned_data.get('active', False) for form in self.forms)
            if parent_instance.guest_user_enabled == GUEST_USER_CUSTOM:
                total_guest_user_enabled = sum(
                    form.cleaned_data.get('guest_user_enabled', False) for
                    form in
                    self.forms)
                if (total_guest_user_enabled == 0) or (
                        total_guest_user_enabled == total_active_configs):
                    raise forms.ValidationError(
                        'Configuration does not match custom. Please toggle '
                        'the guest sliders to make your custom setting.')

            if total_active_configs == 0:
                raise forms.ValidationError('No active configurations')

    def save(self, commit=True):
        parent_instance = self.instance
        if parent_instance.guest_user_enabled == GUEST_USER_ENABLE:
            for form in self.forms:
                form.instance.guest_user_enabled = True
                form.cleaned_data['guest_user_enabled'] = True
                form.instance.save()
        elif parent_instance.guest_user_enabled == GUEST_USER_DISABLE:
            for form in self.forms:
                form.instance.guest_user_enabled = False
                form.cleaned_data['guest_user_enabled'] = False
                form.instance.save()

        invalidate_cached_payment_method_config()

        return super().save(commit)


class PaymentMethodConfigInline(admin.TabularInline):
    model = PaymentMethodConfig
    extra = 0

    form = PaymentMethodConfigAdminForm
    formset = PaymentMethodConfigInlineFormset

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('payment_method', 'country', 'client')


class PaymentConfigurationAdminForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['guest_user_enabled'].required = True

    class Meta:
        model = PaymentConfiguration
        fields = '__all__'

    def clean(self):
        cleaned_data = self.cleaned_data
        if self.instance and self.instance.pk:
            payment_gateway = self.instance.payment_gateway
        else:
            payment_gateway = self.cleaned_data.get('payment_gateway')

        if payment_gateway is None:
            raise forms.ValidationError("Payment gateway cannot be empty")
        
        if ((payment_gateway.code != B2CPAYBACK_HUB_CODE and
             self.cleaned_data.get('beta_version'))
                in [BETA_USER_ONLY_EARN, BETA_USER_ONLY_BURN]):
            raise forms.ValidationError(
                "Invalid beta version: 'Only Earn' or 'Only Burn' "
                "options are available for B2C payment methods only.")

        earn_enabled = cleaned_data.get('earn_enabled', False)
        earn_on_partial_redemption = cleaned_data.get(
            'earn_on_partial_redemption', False)

        burn_full_redemption_enabled = cleaned_data.get(
            'burn_full_redemption_enabled', False)
        partial_redemption_allowed = cleaned_data.get(
            'partial_redemption_allowed', False)

        if partial_redemption_allowed and not burn_full_redemption_enabled:
            raise forms.ValidationError(
                "Partial redemption cannot be enabled unless burn full "
                "redemption enabled")
        if earn_on_partial_redemption and not earn_enabled:
            raise forms.ValidationError(
                "Earn on partial redemption cannot be enabled unless earn "
                "enabled")
        if payment_gateway.code == B2CPAYBACK_HUB_CODE:
            if not earn_enabled and not burn_full_redemption_enabled:
                raise forms.ValidationError("Invalid Configuration")
        return cleaned_data


class PaymentConfigurationAdmin(AdminAbstract):
    list_display = ('payment_method', 'active',
                    'guest_user_enabled', 'payment_gateway')
    search_fields = ('payment_method', 'country', 'clients')
    list_filter = ('payment_method', 'active', 'guest_user_enabled',
                   'payment_gateway',)

    form = PaymentConfigurationAdminForm
    inlines = [PaymentMethodConfigInline]

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.select_related('payment_gateway')

    def get_fields(self, request, obj=None):
        fields = ('payment_method', 'code', 'active',
                  'guest_user_enabled', 'beta_version',
                  'is_second_project_config_enabled',
                  'payment_method_config',
                  'partial_redemption_allowed',
                  'burn_full_redemption_enabled', 'earn_enabled',
                  'earn_on_partial_redemption',
                  'payment_gateway', 'created_at', 'updated_at',
                  'created_by', 'modified_by')

        if obj and obj.payment_method in [PAYMENT_METHOD_QITAF,
                                          PAYMENT_METHOD_ANB,
                                          PAYMENT_METHOD_NEQATY,
                                          PAYMENT_METHOD_ANB,
                                          PAYMENT_METHOD_ADCB]:
            fields = ('payment_method', 'code', 'active',
                      'guest_user_enabled', 'beta_version',
                      'is_second_project_config_enabled',
                      'payment_method_config',
                      'payment_gateway', 'created_at', 'updated_at',
                      'created_by', 'modified_by')
        return fields

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return (
                'created_at', 'updated_at', 'created_by', 'modified_by')
        return (
            'payment_gateway', 'created_at', 'updated_at',
            'created_by', 'modified_by')


class BetaUserAdmin(AdminAbstract):
    list_display = ('beta_user_email', 'name',)
    search_fields = ('beta_user_email', 'name')
    readonly_fields = ('created_at', 'updated_at')


admin.site.register(AppConfig, AppConfigAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(PaymentMethodConfig, PaymentMethodConfigAdmin)
admin.site.register(PaymentConfiguration, PaymentConfigurationAdmin)
admin.site.register(BetaUser, BetaUserAdmin)
