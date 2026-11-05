from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductoForm
from .models import Producto


@login_required
def listar_productos(request):
    productos = Producto.objects.filter(
        propietario=request.user
    ).order_by("nombre")

    return render(
        request,
        "productos/lista.html",
        {"productos": productos},
    )


@login_required
def crear_producto(request):
    if request.method == "POST":
        formulario = ProductoForm(request.POST)

        if formulario.is_valid():
            producto = formulario.save(commit=False)
            producto.propietario = request.user
            producto.save()
            return redirect("productos:lista")
    else:
        formulario = ProductoForm()

    return render(
        request,
        "productos/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Nuevo producto",
        },
    )


@login_required
def editar_producto(request, pk):
    producto = get_object_or_404(
        Producto,
        pk=pk,
        propietario=request.user,
    )

    if request.method == "POST":
        formulario = ProductoForm(request.POST, instance=producto)

        if formulario.is_valid():
            formulario.save()
            return redirect("productos:lista")
    else:
        formulario = ProductoForm(instance=producto)

    return render(
        request,
        "productos/formulario.html",
        {
            "formulario": formulario,
            "titulo": "Editar producto",
        },
    )


@login_required
def eliminar_producto(request, pk):
    producto = get_object_or_404(
        Producto,
        pk=pk,
        propietario=request.user,
    )

    if request.method == "POST":
        producto.delete()
        return redirect("productos:lista")

    return render(
        request,
        "productos/confirmar_eliminacion.html",
        {"producto": producto},
    )