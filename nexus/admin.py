from django.contrib import admin
from .forms import EmpresaForm, ReglaBeneficioForm
from .models import Correccion, Empresa, ReglaBeneficio, Trabajo

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    form = EmpresaForm
    list_display = ["nombre", "activa"]
    list_filter = ["activa"]
    search_fields = ["nombre"]

@admin.register(ReglaBeneficio)
class ReglaAdmin(admin.ModelAdmin):
    form = ReglaBeneficioForm
    list_display = ["nombre", "minimo_lavados", "cupo", "vigencia_dias", "activa"]
    list_filter = ["activa"]

class SoloLecturaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Trabajo)
class TrabajoAdmin(SoloLecturaAdmin):
    exclude = ["firma"]
    list_display = ["patente", "empresa", "fecha_servicio", "estado"]
    list_filter = ["estado", "empresa"]
    search_fields = ["patente"]

@admin.register(Correccion)
class CorreccionAdmin(SoloLecturaAdmin):
    list_display = ["trabajo", "autor", "motivo", "fecha"]
