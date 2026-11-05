from django import forms
from django.db.models import Q
from django.utils import timezone
from .models import Empresa, ReglaBeneficio, Trabajo
from .validators import normalizar_patente, validar_firma, validar_patente

class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-select" if isinstance(field.widget, forms.Select) else "form-control"

class EmpresaForm(BootstrapModelForm):
    class Meta:
        model = Empresa
        fields = ["nombre", "activa"]

class TrabajoForm(BootstrapModelForm):
    motivo = forms.CharField(label="Motivo de la corrección", required=False, max_length=300, help_text="Obligatorio al modificar un trabajo; queda en el historial de auditoría.")
    class Meta:
        model = Trabajo
        fields = ["empresa", "fecha_servicio", "patente", "modelo", "color", "servicio", "observaciones"]
        widgets = {"fecha_servicio": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}), "observaciones": forms.Textarea(attrs={"rows": 3}), "patente": forms.TextInput(attrs={"placeholder": "Ej. ABC123"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available = Q(activa=True)
        if self.instance.pk:
            available |= Q(pk=self.instance.empresa_id)
        # ModelChoiceField comprueba en Python que la FK recibida esté permitida.
        self.fields["empresa"].queryset = Empresa.objects.filter(available)
        self.fields["empresa"].empty_label = "Selecciona una empresa"
        self.fields["fecha_servicio"].widget.attrs["max"] = timezone.localdate().isoformat()
        if not self.instance.pk:
            del self.fields["motivo"]

    def clean_patente(self):
        patente = normalizar_patente(self.cleaned_data["patente"])
        validar_patente(patente)
        return patente

    def clean_motivo(self):
        value = self.cleaned_data.get("motivo", "").strip()
        if self.instance.pk and len(value) < 5:
            raise forms.ValidationError("Explica la corrección con al menos cinco caracteres.")
        return value

class ReglaBeneficioForm(BootstrapModelForm):
    class Meta:
        model = ReglaBeneficio
        fields = ["nombre", "minimo_lavados", "beneficio", "cupo", "vigencia_dias", "activa"]

class EntregaForm(forms.Form):
    firmante = forms.CharField(label="Nombre de quien retira", min_length=3, max_length=120, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "name"}))
    tipo_firmante = forms.ChoiceField(label="Quién retira", choices=[("", "Selecciona una opción"), *Trabajo.TipoFirmante.choices], widget=forms.Select(attrs={"class": "form-select"}))
    firma = forms.CharField(label="Firma", validators=[validar_firma], widget=forms.HiddenInput)

class PeriodoForm(forms.Form):
    corte = forms.DateField(input_formats=["%Y-%m"], widget=forms.DateInput(format="%Y-%m", attrs={"type": "month", "class": "form-control"}), label="Mes de corte")
    def clean_corte(self):
        value = self.cleaned_data["corte"].replace(day=1)
        if value >= timezone.localdate().replace(day=1):
            raise forms.ValidationError("Selecciona un mes que ya haya cerrado.")
        return value
