from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from nexus.views import health

admin.site.site_header = "Nexus Automotive · Usuarios y permisos"
admin.site.site_title = "Nexus Automotive"
admin.site.index_title = "Administración técnica"
urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html", redirect_authenticated_user=True), name="login"),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("nexus.urls")),
]
