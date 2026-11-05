from datetime import timedelta
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, connection, transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .forms import EmpresaForm, EntregaForm, PeriodoForm, ReglaBeneficioForm, TrabajoForm
from .models import Correccion, Empresa, ReglaBeneficio, Trabajo
from .permissions import acceso, es_administradora
from .services import comparar_empresas

@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return HttpResponse("unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")

@acceso()
@require_GET
def dashboard(request):
    trabajos = Trabajo.objects.select_related("empresa", "creado_por")
    return render(request, "nexus/dashboard.html", {
        "seccion": "dashboard", "hoy": timezone.localdate(),
        "total_empresas": Empresa.objects.filter(activa=True).count(),
        "total_pendientes": trabajos.filter(estado=Trabajo.Estado.PENDIENTE).count(),
        "total_entregados": trabajos.filter(estado=Trabajo.Estado.ENTREGADO).count(),
        "total_hoy": trabajos.filter(fecha_servicio=timezone.localdate()).count(),
        "ultimos": trabajos.order_by("-creado_en")[:6],
        "reglas": ReglaBeneficio.objects.filter(activa=True) if es_administradora(request.user) else [],
    })

@acceso(admin=True)
@require_GET
def empresas(request):
    q = request.GET.get("q", "").strip()[:120]
    queryset = Empresa.objects.annotate(numero_trabajos=Count("trabajos")).order_by("nombre", "pk")
    if q:
        queryset = queryset.filter(nombre__icontains=q)
    return render(request, "nexus/empresas.html", {"seccion": "empresas", "pagina": Paginator(queryset, 15).get_page(request.GET.get("page")), "q": q})

def guardar_catalogo(request, formulario, titulo, retorno, seccion):
    if request.method == "POST" and formulario.is_valid():
        try:
            with transaction.atomic():
                formulario.save()
        except (IntegrityError, ValidationError):
            formulario.add_error(None, "Los datos entran en conflicto con otro registro. Revisa los valores e inténtalo otra vez.")
        else:
            messages.success(request, "Cambios guardados correctamente.")
            return redirect(retorno)
    return render(request, "nexus/formulario.html", {"form": formulario, "titulo": titulo, "retorno": retorno, "seccion": seccion})

@acceso(admin=True)
@require_http_methods(["GET", "POST"])
def empresa_form(request, pk=None):
    objeto = get_object_or_404(Empresa, pk=pk) if pk else None
    return guardar_catalogo(request, EmpresaForm(request.POST or None, instance=objeto), "Editar empresa" if pk else "Nueva empresa", "nexus:empresas", "empresas")

@acceso(admin=True)
@require_http_methods(["GET", "POST"])
def empresa_eliminar(request, pk):
    objeto = get_object_or_404(Empresa, pk=pk)
    if request.method == "POST":
        try:
            objeto.delete()
        except ProtectedError:
            messages.error(request, "Esta empresa tiene trabajos. Desactívala para conservar su historial.")
        else:
            messages.success(request, "Empresa eliminada.")
        return redirect("nexus:empresas")
    return render(request, "nexus/confirmar.html", {"objeto": objeto, "retorno": "nexus:empresas", "seccion": "empresas", "aviso": "Si ya tiene trabajos, se conservará y podrás desactivarla desde Editar."})

@acceso()
@require_GET
def trabajos(request):
    q = request.GET.get("q", "").strip()[:120]
    estado = request.GET.get("estado", "")
    queryset = Trabajo.objects.select_related("empresa")
    if q:
        queryset = queryset.filter(Q(patente__icontains=q) | Q(empresa__nombre__icontains=q) | Q(modelo__icontains=q))
    if estado in Trabajo.Estado.values:
        queryset = queryset.filter(estado=estado)
    return render(request, "nexus/trabajos.html", {"seccion": "trabajos", "pagina": Paginator(queryset, 12).get_page(request.GET.get("page")), "q": q, "estado": estado})

@acceso()
@require_GET
def trabajo_detalle(request, pk):
    trabajo = get_object_or_404(Trabajo.objects.select_related("empresa", "creado_por", "entregado_por"), pk=pk)
    return render(request, "nexus/detalle.html", {"seccion": "trabajos", "trabajo": trabajo, "correcciones": trabajo.correcciones.select_related("autor")})

@acceso()
@require_http_methods(["GET", "POST"])
def trabajo_form(request, pk=None):
    with transaction.atomic():
        trabajo = get_object_or_404(Trabajo.objects.select_for_update(), pk=pk) if pk else Trabajo(creado_por=request.user)
        if pk and trabajo.estado == Trabajo.Estado.ENTREGADO and not es_administradora(request.user):
            raise PermissionDenied("Solo la administradora puede corregir trabajos entregados.")
        campos = ["empresa_id", "fecha_servicio", "patente", "modelo", "color", "servicio", "observaciones"]
        anterior = {campo: str(getattr(trabajo, campo)) for campo in campos}
        empresa_anterior = str(trabajo.empresa) if trabajo.empresa_id else ""
        form = TrabajoForm(request.POST or None, instance=trabajo)
        if request.method == "POST" and form.is_valid():
            empresa = Empresa.objects.select_for_update().filter(pk=form.cleaned_data["empresa"].pk).first()
            if empresa is None or (not empresa.activa and (not pk or str(empresa.pk) != anterior["empresa_id"])):
                form.add_error("empresa", "La empresa ya no está activa. Selecciona otra.")
            else:
                trabajo = form.save()
                cambios = {c: {"antes": anterior[c], "despues": str(getattr(trabajo, c))} for c in campos if anterior[c] != str(getattr(trabajo, c))}
                if "empresa_id" in cambios:
                    cambios["empresa_id"] = {"antes": empresa_anterior, "despues": str(trabajo.empresa)}
                if pk and cambios:
                    Correccion.objects.create(trabajo=trabajo, autor=request.user, motivo=form.cleaned_data["motivo"], cambios=cambios)
                messages.success(request, "Trabajo corregido con auditoría." if pk else "Trabajo registrado. Queda pendiente de entrega.")
                return redirect("nexus:trabajo_detalle", pk=trabajo.pk)
    return render(request, "nexus/formulario.html", {"form": form, "titulo": "Corregir trabajo" if pk else "Registrar trabajo", "retorno": "nexus:trabajos", "seccion": "trabajos", "es_trabajo": True})

@acceso(admin=True)
@require_http_methods(["GET", "POST"])
def trabajo_entregar(request, pk):
    with transaction.atomic():
        trabajo = get_object_or_404(Trabajo.objects.select_for_update().select_related("empresa"), pk=pk)
        if trabajo.estado == Trabajo.Estado.ENTREGADO:
            messages.info(request, "Este trabajo ya fue entregado. No se ha duplicado la entrega.")
            return redirect("nexus:trabajo_detalle", pk=pk)
        form = EntregaForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            trabajo.firmante = form.cleaned_data["firmante"]
            trabajo.tipo_firmante = form.cleaned_data["tipo_firmante"]
            trabajo.firma = form.cleaned_data["firma"]
            trabajo.entregado_en = timezone.now()
            trabajo.entregado_por = request.user
            trabajo.estado = Trabajo.Estado.ENTREGADO
            trabajo.save()
            messages.success(request, "Entrega confirmada con firma. Este servicio ya puede alimentar el CORE.")
            return redirect("nexus:trabajo_detalle", pk=pk)
    return render(request, "nexus/entrega.html", {"seccion": "trabajos", "trabajo": trabajo, "form": form})

@acceso(admin=True)
@require_http_methods(["GET", "POST"])
def trabajo_eliminar(request, pk):
    with transaction.atomic():
        trabajo = get_object_or_404(Trabajo.objects.select_for_update(), pk=pk)
        if trabajo.estado == Trabajo.Estado.ENTREGADO:
            raise PermissionDenied("Un trabajo entregado se conserva para proteger el historial del CORE.")
        if request.method == "POST":
            trabajo.delete()
            messages.success(request, "Trabajo pendiente eliminado.")
            return redirect("nexus:trabajos")
    return render(request, "nexus/confirmar.html", {"objeto": trabajo, "retorno": "nexus:trabajos", "seccion": "trabajos", "aviso": "Solo se permite eliminar trabajos pendientes de entrega."})

@acceso(admin=True)
@require_GET
def reglas(request):
    return render(request, "nexus/reglas.html", {"seccion": "reglas", "reglas": ReglaBeneficio.objects.all()})

@acceso(admin=True)
@require_http_methods(["GET", "POST"])
def regla_form(request, pk=None):
    objeto = get_object_or_404(ReglaBeneficio, pk=pk) if pk else None
    return guardar_catalogo(request, ReglaBeneficioForm(request.POST or None, instance=objeto), "Editar regla" if pk else "Nueva regla de beneficio", "nexus:reglas", "reglas")

@acceso(admin=True)
@require_http_methods(["GET", "POST"])
def regla_eliminar(request, pk):
    objeto = get_object_or_404(ReglaBeneficio, pk=pk)
    if request.method == "POST":
        objeto.delete()
        messages.success(request, "Regla eliminada.")
        return redirect("nexus:reglas")
    return render(request, "nexus/confirmar.html", {"objeto": objeto, "retorno": "nexus:reglas", "seccion": "reglas", "aviso": "La consulta del comparativo utilizará las reglas activas restantes."})

@acceso(admin=True)
@require_GET
def comparativo(request):
    corte = (timezone.localdate().replace(day=1) - timedelta(days=1)).replace(day=1)
    form = PeriodoForm(request.GET or None, initial={"corte": corte})
    resultado = None
    if not form.is_bound or form.is_valid():
        resultado = comparar_empresas(form.cleaned_data["corte"] if form.is_bound else corte)
    return render(request, "nexus/comparativo.html", {"seccion": "core", "form": form, "resultado": resultado})
