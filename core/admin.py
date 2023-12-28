import logging

from django import forms
from django.contrib import admin
from django.core.cache import cache

from .constants import (GUEST_USER_CUSTOM, GUEST_USER_ENABLE,
                        GUEST_USER_DISABLE)
from .models import (AppConfig, Currency, Country, PaymentMethod,
                     PaymentMethodConfig)

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
        self.fields['platform'].required = True
        self.fields['payment_method'].required = True


class PaymentMethodConfigInlineFormset(forms.models.BaseInlineFormSet):
    def clean(self):
        super().clean()

        parent_instance = self.instance
        if parent_instance.guest_user_enabled == GUEST_USER_CUSTOM:
            total_guest_user_enabled = sum(
                1 for form in self.forms
                if form.cleaned_data.get('guest_user_enabled')
            )

            total_forms = self.total_form_count()

            if (total_guest_user_enabled == 0) or (
                    total_guest_user_enabled == total_forms):
                raise forms.ValidationError(
                    'Configuration does not match custom. Please toggle the '
                    'guest sliders to make your custom setting.'
                )
        existing_configs = set()
        for form in self.forms:
            payment_method = form.cleaned_data.get('payment_method')
            country = form.cleaned_data.get('country')
            platform = form.cleaned_data.get('platform')
            client = form.cleaned_data.get('client')

            if (
                    payment_method, country, platform,
                    client) in existing_configs:
                form.add_error(
                    None,
                    forms.ValidationError(
                        'A configuration already exists for this combination.'
                    )
                )

            existing_configs.add((payment_method, country, platform, client))

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

        return super().save(commit)


class PaymentMethodConfigInline(admin.TabularInline):
    model = PaymentMethodConfig
    extra = 0

    form = PaymentMethodConfigAdminForm
    formset = PaymentMethodConfigInlineFormset


class PaymentMethodAdmin(AdminAbstract):
    fields = ('payment_method', 'active',
              'guest_user_enabled', 'payment_gateway', 'created_at',
              'updated_at', 'created_by', 'modified_by')
    list_display = ('payment_method', 'active',
                    'guest_user_enabled', 'payment_gateway')
    search_fields = ('payment_method', 'country', 'clients')
    list_filter = ('payment_method', 'active', 'guest_user_enabled',
                   'payment_gateway',)

    inlines = [PaymentMethodConfigInline]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return (
                'created_at', 'updated_at', 'created_by', 'modified_by')
        return (
            'payment_method', 'payment_gateway', 'created_at', 'updated_at',
            'created_by', 'modified_by')


admin.site.register(AppConfig, AppConfigAdmin)
admin.site.register(Currency, CurrencyAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(PaymentMethod, PaymentMethodAdmin)
