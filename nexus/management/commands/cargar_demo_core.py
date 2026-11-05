import base64
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from nexus.models import Empresa, ReglaBeneficio, Trabajo
from nexus.permissions import es_administradora
from nexus.services import comparar_empresas, desplazar_mes


class Command(BaseCommand):
    help = "Carga datos ficticios para comprobar el comparativo y sus niveles."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        # Usamos una cuenta de administración existente.
        usuario = get_user_model().objects.filter(
            username=options["usuario"]
        ).first()

        if usuario is None or not es_administradora(usuario):
            raise CommandError(
                "Indica un usuario activo con permisos de administración."
            )

        # La demostración utiliza las reglas que acabamos de verificar.
        reglas = set(
            ReglaBeneficio.objects.filter(activa=True).values_list(
                "minimo_lavados", "cupo"
            )
        )

        if reglas != {(50, 1), (100, 2), (150, 3)}:
            raise CommandError(
                "Esta carga requiere las reglas activas "
                "50/1, 100/2 y 150/3."
            )

        # Último mes cerrado y los dos anteriores.
        corte = (
            timezone.localdate().replace(day=1) - timedelta(days=1)
        ).replace(day=1)

        meses = [
            desplazar_mes(corte, desplazamiento)
            for desplazamiento in (-2, -1, 0)
        ]

        marca = f"DEMO_CORE_{corte:%Y_%m}"
        prefijo = f"DEMO CORE {corte:%Y-%m} | "

        if (
            Trabajo.objects.filter(observaciones=marca).exists()
            or Empresa.objects.filter(nombre__startswith=prefijo).exists()
        ):
            self.stdout.write(
                self.style.WARNING(
                    "Ya existen datos DEMO de este corte. "
                    "No se insertaron registros adicionales."
                )
            )
            return

        # Imagen ficticia, identificada expresamente como prueba.
        imagen = Image.new("RGB", (500, 150), "white")
        dibujo = ImageDraw.Draw(imagen)
        dibujo.text((20, 15), "FIRMA DE PRUEBA - DEMO", fill="black")
        dibujo.line(
            [(30, 110), (70, 45), (110, 100), (180, 60), (350, 95)],
            fill="black",
            width=4,
        )

        archivo = BytesIO()
        imagen.save(archivo, format="PNG")
        firma = (
            "data:image/png;base64,"
            + base64.b64encode(archivo.getvalue()).decode("ascii")
        )

        datos_entrega = {
            "estado": Trabajo.Estado.ENTREGADO,
            "firmante": "Firmante DEMO",
            "tipo_firmante": Trabajo.TipoFirmante.EMPRESA,
            "firma": firma,
            "entregado_por": usuario,
            "entregado_en": timezone.now(),
        }

        secuencia = 0

        def crear_trabajo(empresa, fecha, entregado):
            nonlocal secuencia
            secuencia += 1

            # objects.create utiliza save y las validaciones del modelo.
            Trabajo.objects.create(
                empresa=empresa,
                fecha_servicio=fecha,
                patente=f"DM{secuencia:05d}",
                modelo="Vehículo DEMO",
                color="Gris",
                servicio=Trabajo.Servicio.COMPLETO,
                creado_por=usuario,
                observaciones=marca,
                **(datos_entrega if entregado else {}),
            )

        # Nombre, cantidades mensuales y cupo esperado.
        casos = [
            ("Sin beneficio", [15, 16, 18], 0),
            ("Preferente", [15, 15, 20], 1),
            ("Plus", [30, 30, 40], 2),
            ("Premium", [45, 50, 55], 3),
        ]

        empresas = {}

        for nombre, cantidades, cupo_esperado in casos:
            empresa = Empresa.objects.create(
                nombre=prefijo + nombre,
                activa=True,
            )
            empresas[nombre] = empresa

            for mes, cantidad in zip(meses, cantidades):
                for _ in range(cantidad):
                    crear_trabajo(
                        empresa,
                        mes.replace(day=15),
                        entregado=True,
                    )

        # Si se contaran por error, esta empresa pasaría de 49 a 59.
        for _ in range(10):
            crear_trabajo(
                empresas["Sin beneficio"],
                corte.replace(day=15),
                entregado=False,
            )

        # Comprobamos el resultado usando el servicio del comparativo.
        resultado = comparar_empresas(corte)
        filas = {
            fila["empresa"].pk: fila
            for fila in resultado["filas"]
        }

        mensajes = []

        for nombre, cantidades, cupo_esperado in casos:
            fila = filas[empresas[nombre].pk]
            regla = fila["regla"]
            cupo_real = regla.cupo if regla else 0

            if (
                fila["meses"] != cantidades
                or fila["total"] != sum(cantidades)
                or cupo_real != cupo_esperado
            ):
                raise CommandError(
                    "La comprobación no coincide. "
                    "La carga se revierte completamente."
                )

            nivel = regla.nombre if regla else "Sin beneficio"
            mensajes.append(
                f"{nombre}: {fila['total']} entregados "
                f"| nivel {nivel} | cupo {cupo_real}"
            )

        for mensaje in mensajes:
            self.stdout.write(mensaje)

        self.stdout.write(
            self.style.SUCCESS(
                "Carga lista: 349 entregados y 10 pendientes."
            )
        )
        self.stdout.write(
            f"Consulta el comparativo con corte {corte:%Y-%m}."
        )