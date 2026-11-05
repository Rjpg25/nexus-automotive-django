from django.conf import settings
from django.db import models


class Producto(models.Model):
    nombre = models.CharField(max_length=120)
    cantidad = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True)
    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='productos',
    )

    def __str__(self):
        return self.nombre