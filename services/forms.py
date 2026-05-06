import re
import json

from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from core.models import CheckoutFont
from services.models import APIClient

SYSTEM_FONT_FAMILY = (
    "system-ui, -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
)


class FontSelectWidget(forms.Select):
    """
    Custom Select widget that renders a real-time checkout preview
    showing how the selected font will look. Font data is loaded
    dynamically from the CheckoutFont table in core.models.
    """

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)

        # Build font map dynamically from DB
        font_map = {'': SYSTEM_FONT_FAMILY}
        url_map = {}
        italic_set = []

        for font in CheckoutFont.objects.filter(is_active=True):
            font_map[str(font.pk)] = font.font_family
            if font.font_url:
                url_map[str(font.pk)] = font.font_url
            if font.is_italic:
                italic_set.append(str(font.pk))

        widget_id = attrs.get('id', '') if attrs else f"id_{name}"
        is_arabic = 'ar' in name.lower()

        context = {
            'widget_id': widget_id,
            'is_arabic': is_arabic,
            'font_map': json.dumps(font_map),
            'url_map': json.dumps(url_map),
            'italic_set': json.dumps(italic_set),
        }

        preview_html = render_to_string(
            'services/widgets/font_preview.html', context)

        wrapper_start = (
            '<div style="display: flex; align-items: flex-start; gap: 30px;">'
        )
        wrapper_end = '</div>'
        return mark_safe(wrapper_start + html + preview_html + wrapper_end)


class APIClientForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].required = True
        self.fields['logo_file'].required = True
        self.fields['mobile_logo_file'].required = True
        self.fields['color_code'].required = True

        self.update_font_preview()

    class Meta:
        model = APIClient
        exclude = ('font_en',)
        widgets = {
            'font': FontSelectWidget(),
            'font_ar': FontSelectWidget()
        }

    def update_font_preview(self):
        """
        Updating the queryset for the font fields to show only active fonts
        based on the language, and disabling related object links.
        """
        queryset = CheckoutFont.objects.filter(is_active=True)
        # 'font' represents English (default), 'font_ar' represents Arabic
        field_mapping = {
            'font_en_us': 'en',
            'font_ar': 'ar'
        }
        for field_name, lang in field_mapping.items():
            if field_name in self.fields:
                self.fields[field_name].queryset = queryset.filter(language=lang)

                # Disable related object links (Add/Change/Delete)
                widget = self.fields[field_name].widget
                if hasattr(widget, 'can_add_related'):
                    widget.can_add_related = False
                    widget.can_change_related = False
                    widget.can_delete_related = False

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
