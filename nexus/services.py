"""Consultas que conectan la administración con el CORE aprobado."""
from datetime import date, timedelta
from decimal import Decimal
from django.db.models import Count
from django.db.models.functions import TruncMonth
from .models import Empresa, ReglaBeneficio, Trabajo

def desplazar_mes(fecha, cantidad):
    ordinal = fecha.year * 12 + fecha.month - 1 + cantidad
    return date(ordinal // 12, ordinal % 12 + 1, 1)

def comparar_empresas(corte):
    meses = [desplazar_mes(corte, offset) for offset in (-2, -1, 0)]
    fin_exclusivo = desplazar_mes(corte, 1)
    grupos = (Trabajo.objects.filter(estado=Trabajo.Estado.ENTREGADO, fecha_servicio__gte=meses[0], fecha_servicio__lt=fin_exclusivo)
              .annotate(mes=TruncMonth("fecha_servicio")).values("empresa_id", "mes").annotate(cantidad=Count("id")))
    conteos = {(g["empresa_id"], g["mes"].month): g["cantidad"] for g in grupos}
    reglas = list(ReglaBeneficio.objects.filter(activa=True).order_by("-minimo_lavados"))
    filas = []
    for empresa in Empresa.objects.all():
        mensual = [conteos.get((empresa.pk, mes.month), 0) for mes in meses]
        total = sum(mensual)
        regla = next((r for r in reglas if total >= r.minimo_lavados), None) if empresa.activa else None
        filas.append({"empresa": empresa, "meses": mensual, "total": total, "regla": regla,
                      "variacion": Decimal(mensual[2] - mensual[0]) * 100 / mensual[0] if mensual[0] else None})
    filas.sort(key=lambda f: (-f["total"], f["empresa"].nombre.casefold()))
    total_general = sum(f["total"] for f in filas)
    puesto, anterior = 0, None
    for fila in filas:
        if fila["total"] != anterior:
            puesto += 1
            anterior = fila["total"]
        fila["puesto"] = puesto if fila["total"] else None
        fila["participacion"] = Decimal(fila["total"]) * 100 / total_general if total_general else None
    return {"filas": filas, "meses": meses, "inicio": meses[0], "fin": fin_exclusivo - timedelta(days=1),
            "total_general": total_general, "empresas_activas_periodo": sum(f["total"] > 0 for f in filas)}
