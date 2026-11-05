from django import template

register = template.Library()

@register.filter
def etiqueta_campo(value):
    return {"empresa_id": "Empresa", "fecha_servicio": "Fecha del servicio", "patente": "Patente", "modelo": "Modelo", "color": "Color", "servicio": "Servicio", "observaciones": "Observaciones"}.get(value, value)
