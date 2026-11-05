from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone
from .validators import normalizar_patente, validar_fecha_servicio, validar_firma, validar_patente

class ValidatedModel(models.Model):
    """save también valida; formularios y Django Admin comparten las reglas."""
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class Empresa(ValidatedModel):
    nombre = models.CharField("Nombre de la empresa", max_length=120, validators=[MinLengthValidator(2)])
    activa = models.BooleanField("Empresa activa", default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(Lower("nombre"), name="empresa_nombre_sin_duplicados")]

    def clean(self):
        self.nombre = " ".join(self.nombre.split())
        if len(self.nombre) < 2:
            raise ValidationError({"nombre": "Escribe un nombre de al menos dos caracteres."})
        if Empresa.objects.filter(nombre__iexact=self.nombre).exclude(pk=self.pk).exists():
            raise ValidationError({"nombre": "Esta empresa ya está registrada."})

    def __str__(self):
        return self.nombre

class Trabajo(ValidatedModel):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente_entrega", "Pendiente de entrega"
        ENTREGADO = "entregado", "Entregado"
    class Servicio(models.TextChoices):
        COMPLETO = "completo", "Lavado completo"
        EXTERIOR = "exterior", "Lavado exterior"
        INTERIOR = "interior", "Limpieza interior"
    class TipoFirmante(models.TextChoices):
        EMPRESA = "empresa", "Representante de la empresa"
        ADMINISTRADORA = "administradora", "Administradora"

    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, related_name="trabajos", verbose_name="Empresa")
    fecha_servicio = models.DateField("Fecha del servicio", default=timezone.localdate, validators=[validar_fecha_servicio])
    patente = models.CharField("Patente / placa", max_length=10, validators=[validar_patente])
    modelo = models.CharField("Modelo del vehículo", max_length=80, validators=[MinLengthValidator(2)])
    color = models.CharField("Color", max_length=40, validators=[MinLengthValidator(2)])
    servicio = models.CharField("Servicio", max_length=20, choices=Servicio.choices)
    observaciones = models.TextField("Observaciones", max_length=1000, blank=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE, editable=False)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="trabajos_creados", editable=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    firmante = models.CharField("Nombre de quien retira", max_length=120, blank=True)
    tipo_firmante = models.CharField("Quién retira", max_length=20, choices=TipoFirmante.choices, blank=True)
    firma = models.TextField("Firma", blank=True, validators=[validar_firma])
    entregado_en = models.DateTimeField(null=True, blank=True, editable=False)
    entregado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="trabajos_entregados", null=True, blank=True, editable=False)

    class Meta:
        ordering = ["-fecha_servicio", "-pk"]
        indexes = [models.Index(fields=["estado", "fecha_servicio"], name="trabajo_core_fecha")]
        constraints = [models.CheckConstraint(condition=(Q(estado="pendiente_entrega", entregado_en__isnull=True, entregado_por__isnull=True, firma="", firmante="", tipo_firmante="") | (Q(estado="entregado", entregado_en__isnull=False, entregado_por__isnull=False) & ~Q(firma="") & ~Q(firmante="") & ~Q(tipo_firmante=""))), name="entrega_con_datos_completos")]

    def clean_fields(self, exclude=None):
        self.patente = normalizar_patente(self.patente)
        self.modelo = self.modelo.strip()
        self.color = self.color.strip()
        self.firmante = self.firmante.strip()
        super().clean_fields(exclude=exclude)

    def clean(self):
        errors = {}
        if self.estado == self.Estado.ENTREGADO:
            if len(self.firmante.strip()) < 3:
                errors["firmante"] = "Identifica a quien retira con al menos tres caracteres."
            if not self.tipo_firmante:
                errors["tipo_firmante"] = "Selecciona quién retira el vehículo."
            if not self.firma:
                errors["firma"] = "La firma es obligatoria para entregar y contabilizar el trabajo."
            if not self.entregado_en or not self.entregado_por_id:
                errors["estado"] = "La entrega debe confirmarse desde su formulario."
        elif self.firma or self.firmante or self.tipo_firmante or self.entregado_en or self.entregado_por_id:
            errors["estado"] = "Un pendiente no puede contener una entrega parcial."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"NX-{self.pk or 'nuevo'} · {self.patente}"

class ReglaBeneficio(ValidatedModel):
    nombre = models.CharField("Nivel", max_length=40)
    minimo_lavados = models.PositiveIntegerField("Mínimo de lavados en tres meses", validators=[MinValueValidator(1)])
    beneficio = models.CharField("Beneficio complementario", max_length=180)
    cupo = models.PositiveIntegerField("Cupo de extras", validators=[MinValueValidator(1)])
    vigencia_dias = models.PositiveIntegerField("Vigencia en días", default=30, validators=[MinValueValidator(1)])
    activa = models.BooleanField("Regla activa", default=True)

    class Meta:
        ordering = ["minimo_lavados"]
        verbose_name = "regla de beneficio"
        verbose_name_plural = "reglas de beneficios"
        constraints = [
            models.UniqueConstraint(fields=["minimo_lavados"], condition=Q(activa=True), name="umbral_activo_unico"),
            models.CheckConstraint(condition=Q(minimo_lavados__gte=1, cupo__gte=1, vigencia_dias__gte=1), name="regla_valores_positivos"),
        ]

    def clean(self):
        self.nombre = self.nombre.strip()
        self.beneficio = self.beneficio.strip()
        if not self.nombre or not self.beneficio:
            raise ValidationError("El nivel y la descripción del beneficio son obligatorios.")
        if self.activa and ReglaBeneficio.objects.filter(activa=True, minimo_lavados=self.minimo_lavados).exclude(pk=self.pk).exists():
            raise ValidationError({"minimo_lavados": "Ya existe una regla activa con este mínimo de lavados."})

    def __str__(self):
        return f"{self.nombre} · desde {self.minimo_lavados} lavados"

class Correccion(models.Model):
    trabajo = models.ForeignKey(Trabajo, on_delete=models.CASCADE, related_name="correcciones")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    motivo = models.CharField(max_length=300)
    cambios = models.JSONField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name_plural = "correcciones"
