
from modeltranslation.translator import register, TranslationOptions
from .models import APIClient


@register(APIClient)
class APIClientTranslationOptions(TranslationOptions):
    fields = ('font',)
    required_languages = {}
