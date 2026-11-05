from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

ADMINISTRADORA = "Administradora"
OPERADOR = "Operador"

def es_administradora(user):
    return user.is_authenticated and user.is_active and (user.is_superuser or user.groups.filter(name=ADMINISTRADORA).exists())

def es_operador(user):
    return user.is_authenticated and user.is_active and user.groups.filter(name=OPERADOR).exists()

def acceso(admin=False):
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not es_administradora(request.user) and (admin or not es_operador(request.user)):
                raise PermissionDenied("Tu cuenta no tiene permisos para esta operación.")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator

def role_context(request):
    return {"es_admin": es_administradora(request.user), "rol_actual": ADMINISTRADORA if es_administradora(request.user) else OPERADOR}
