from django.urls import path
from . import views

app_name = "nexus"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("empresas/", views.empresas, name="empresas"),
    path("empresas/nueva/", views.empresa_form, name="empresa_crear"),
    path("empresas/<int:pk>/editar/", views.empresa_form, name="empresa_editar"),
    path("empresas/<int:pk>/eliminar/", views.empresa_eliminar, name="empresa_eliminar"),
    path("trabajos/", views.trabajos, name="trabajos"),
    path("trabajos/nuevo/", views.trabajo_form, name="trabajo_crear"),
    path("trabajos/<int:pk>/", views.trabajo_detalle, name="trabajo_detalle"),
    path("trabajos/<int:pk>/editar/", views.trabajo_form, name="trabajo_editar"),
    path("trabajos/<int:pk>/entregar/", views.trabajo_entregar, name="trabajo_entregar"),
    path("trabajos/<int:pk>/eliminar/", views.trabajo_eliminar, name="trabajo_eliminar"),
    path("reglas/", views.reglas, name="reglas"),
    path("reglas/nueva/", views.regla_form, name="regla_crear"),
    path("reglas/<int:pk>/editar/", views.regla_form, name="regla_editar"),
    path("reglas/<int:pk>/eliminar/", views.regla_eliminar, name="regla_eliminar"),
    path("core/", views.comparativo, name="comparativo"),
]
