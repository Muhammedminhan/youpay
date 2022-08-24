from django.contrib import admin


# Register your models here.
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
