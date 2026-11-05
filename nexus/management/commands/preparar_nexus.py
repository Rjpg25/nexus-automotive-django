"""Inicializa roles y reglas sin contraseñas ni datos reales."""
import os
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from nexus.models import Empresa

class Command(BaseCommand):
    help = "Comprueba roles y cuenta inicial; --demo añade empresas ficticias."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true")

    @transaction.atomic
    def handle(self, *args, **options):
        for nombre in ["Administradora", "Operador"]:
            Group.objects.get_or_create(name=nombre)
        if options["demo"]:
            for nombre in ["Andes Rent", "Costa Drive", "Sierra Móvil", "Ruta Express", "MoviCar"]:
                Empresa.objects.get_or_create(nombre=nombre)
        # Inicialización opcional de producción: credenciales solo por entorno.
        username = os.getenv("NEXUS_ADMIN_USERNAME", "")
        password = os.getenv("NEXUS_ADMIN_PASSWORD", "")
        if username and not get_user_model().objects.filter(username=username).exists():
            if not password:
                raise CommandError("Falta NEXUS_ADMIN_PASSWORD para crear la cuenta inicial.")
            candidate = get_user_model()(username=username, email=os.getenv("NEXUS_ADMIN_EMAIL", ""))
            validate_password(password, user=candidate)
            get_user_model().objects.create_superuser(username=username, email=candidate.email, password=password)
            self.stdout.write("Cuenta de administración inicial creada.")
        self.stdout.write(self.style.SUCCESS("Roles de Nexus preparados. No se modificaron reglas ni credenciales existentes."))
