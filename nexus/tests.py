"""Pruebas de seguridad, integridad y reglas del CORE (sin depender de JS)."""
import base64
import io
from django.core.management import call_command
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image, ImageDraw
from .models import Correccion, Empresa, ReglaBeneficio, Trabajo
from .services import comparar_empresas, desplazar_mes
from .validators import validar_firma

def firma_png(blank=False):
    image = Image.new("RGB", (500, 150), "white")
    if not blank:
        ImageDraw.Draw(image).line([(35, 100), (60, 35), (100, 110), (160, 60), (300, 95)], fill="black", width=4)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()

@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class NexusTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ReglaBeneficio.objects.all().delete()
        cls.admin = get_user_model().objects.create_user("admin_test", password="SoloPruebas!826")
        cls.admin.groups.add(Group.objects.get_or_create(name="Administradora")[0])
        cls.operador = get_user_model().objects.create_user("operador_test", password="SoloPruebas!826")
        cls.operador.groups.add(Group.objects.get_or_create(name="Operador")[0])
        cls.sin_rol = get_user_model().objects.create_user("sin_rol", password="SoloPruebas!826")
        cls.empresa = Empresa.objects.create(nombre="Andes Rent")
        cls.inactiva = Empresa.objects.create(nombre="Inactiva", activa=False)

    def datos(self, **kwargs):
        datos = {"empresa": self.empresa.pk, "fecha_servicio": timezone.localdate().isoformat(), "patente": "ABC123", "modelo": "Chevrolet Beat", "color": "Gris", "servicio": "completo", "observaciones": ""}
        datos.update(kwargs)
        return datos

    def trabajo(self, **kwargs):
        datos = {"empresa": self.empresa, "fecha_servicio": timezone.localdate(), "patente": "ABC123", "modelo": "Chevrolet Beat", "color": "Gris", "servicio": "completo", "creado_por": self.operador}
        datos.update(kwargs)
        return Trabajo.objects.create(**datos)

    def entregar(self, trabajo):
        trabajo.estado = Trabajo.Estado.ENTREGADO
        trabajo.firmante = "Persona de prueba"
        trabajo.tipo_firmante = "empresa"
        trabajo.firma = firma_png()
        trabajo.entregado_en = timezone.now()
        trabajo.entregado_por = self.admin
        trabajo.save()

    def test_login_required_and_login_flow(self):
        response = self.client.get(reverse("nexus:trabajo_crear"))
        self.assertRedirects(response, "/login/?next=/trabajos/nuevo/")
        response = self.client.post(reverse("login"), {"username": "admin_test", "password": "SoloPruebas!826"})
        self.assertRedirects(response, reverse("nexus:dashboard"))

    def test_logout_only_post(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))

    def test_csrf_protects_write(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post(reverse("nexus:empresa_crear"), {"nombre": "Falsificada", "activa": "on"}).status_code, 403)
        self.assertFalse(Empresa.objects.filter(nombre="Falsificada").exists())

    def test_user_without_role_cannot_access(self):
        self.client.force_login(self.sin_rol)
        self.assertEqual(self.client.get(reverse("nexus:dashboard")).status_code, 403)

    def test_operator_cannot_open_or_post_admin_routes(self):
        self.client.force_login(self.operador)
        trabajo = self.trabajo()
        for name in ["nexus:empresas", "nexus:reglas", "nexus:comparativo", "nexus:empresa_crear", "nexus:regla_crear"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
            self.assertEqual(self.client.post(reverse(name), {}).status_code, 403)
        self.assertEqual(self.client.post(reverse("nexus:trabajo_entregar", args=[trabajo.pk]), {}).status_code, 403)

    def test_company_field_is_dropdown(self):
        self.client.force_login(self.operador)
        response = self.client.get(reverse("nexus:trabajo_crear"))
        self.assertContains(response, '<select name="empresa"')
        self.assertContains(response, "Andes Rent")
        self.assertNotContains(response, '>Inactiva</option>')

    def test_forged_or_inactive_company_is_rejected(self):
        self.client.force_login(self.operador)
        for empresa in [999999, self.inactiva.pk, "abc"]:
            response = self.client.post(reverse("nexus:trabajo_crear"), self.datos(empresa=empresa))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].has_error("empresa"))
        self.assertEqual(Trabajo.objects.count(), 0)

    def test_future_date_rejected_by_post_and_model_save(self):
        self.client.force_login(self.operador)
        future = timezone.localdate() + timedelta(days=1)
        response = self.client.post(reverse("nexus:trabajo_crear"), self.datos(fecha_servicio=future.isoformat()))
        self.assertTrue(response.context["form"].has_error("fecha_servicio"))
        with self.assertRaises(ValidationError):
            self.trabajo(fecha_servicio=future)
        self.assertEqual(Trabajo.objects.count(), 0)

    def test_plate_normalization_and_invalid_plate(self):
        self.client.force_login(self.operador)
        response = self.client.post(reverse("nexus:trabajo_crear"), self.datos(patente="ab-c 123"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Trabajo.objects.get().patente, "ABC123")
        response = self.client.post(reverse("nexus:trabajo_crear"), self.datos(patente="@@@@@"))
        self.assertTrue(response.context["form"].has_error("patente"))

    def test_cannot_forge_status_creator_or_delivery_on_creation(self):
        self.client.force_login(self.operador)
        response = self.client.post(reverse("nexus:trabajo_crear"), self.datos(estado="entregado", creado_por=self.admin.pk, entregado_por=self.admin.pk))
        self.assertEqual(response.status_code, 302)
        trabajo = Trabajo.objects.get()
        self.assertEqual(trabajo.estado, Trabajo.Estado.PENDIENTE)
        self.assertEqual(trabajo.creado_por, self.operador)
        self.assertIsNone(trabajo.entregado_por)

    def test_missing_blank_or_fake_signature_rejected(self):
        self.client.force_login(self.admin)
        trabajo = self.trabajo()
        for signature in ["", "data:image/png;base64,AAAA", firma_png(blank=True), "https://example.com/a.png"]:
            response = self.client.post(reverse("nexus:trabajo_entregar", args=[trabajo.pk]), {"firmante": "Persona prueba", "tipo_firmante": "empresa", "firma": signature})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].has_error("firma"))
            trabajo.refresh_from_db()
            self.assertEqual(trabajo.estado, Trabajo.Estado.PENDIENTE)

    def test_valid_delivery_and_repeated_post_are_not_duplicated(self):
        self.client.force_login(self.admin)
        trabajo = self.trabajo()
        data = {"firmante": "Persona prueba", "tipo_firmante": "empresa", "firma": firma_png()}
        url = reverse("nexus:trabajo_entregar", args=[trabajo.pk])
        self.assertEqual(self.client.post(url, data).status_code, 302)
        trabajo.refresh_from_db()
        original = trabajo.entregado_en
        self.assertEqual(trabajo.estado, Trabajo.Estado.ENTREGADO)
        self.assertEqual(trabajo.entregado_por, self.admin)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        trabajo.refresh_from_db()
        self.assertEqual(trabajo.entregado_en, original)
        self.assertEqual(Trabajo.objects.count(), 1)

    def test_model_and_database_reject_incomplete_delivery(self):
        trabajo = self.trabajo()
        trabajo.estado = Trabajo.Estado.ENTREGADO
        with self.assertRaises(ValidationError):
            trabajo.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Trabajo.objects.filter(pk=trabajo.pk).update(estado="entregado")

    def test_operator_can_edit_pending_but_not_delivered(self):
        self.client.force_login(self.operador)
        trabajo = self.trabajo()
        url = reverse("nexus:trabajo_editar", args=[trabajo.pk])
        self.assertEqual(self.client.post(url, self.datos(color="Azul", motivo="Corregir color del vehículo")).status_code, 302)
        self.assertEqual(Correccion.objects.get().autor, self.operador)
        trabajo.refresh_from_db()
        self.entregar(trabajo)
        self.assertEqual(self.client.post(url, self.datos(color="Rojo", motivo="Intento de corrección")).status_code, 403)

    def test_admin_correction_requires_reason_and_leaves_audit(self):
        self.client.force_login(self.admin)
        trabajo = self.trabajo()
        self.entregar(trabajo)
        url = reverse("nexus:trabajo_editar", args=[trabajo.pk])
        response = self.client.post(url, self.datos(color="Azul"))
        self.assertTrue(response.context["form"].has_error("motivo"))
        self.assertEqual(self.client.post(url, self.datos(color="Azul", motivo="Corrección solicitada por empresa")).status_code, 302)
        audit = Correccion.objects.get()
        self.assertEqual(audit.cambios["color"], {"antes": "Gris", "despues": "Azul"})

    def test_delete_protects_history_and_get_does_not_delete(self):
        self.client.force_login(self.admin)
        trabajo = self.trabajo()
        url = reverse("nexus:trabajo_eliminar", args=[trabajo.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertTrue(Trabajo.objects.filter(pk=trabajo.pk).exists())
        self.entregar(trabajo)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.post(reverse("nexus:empresa_eliminar", args=[self.empresa.pk]))
        self.assertTrue(Empresa.objects.filter(pk=self.empresa.pk).exists())

    def test_rule_sensitive_values_and_duplicate_active_threshold(self):
        self.client.force_login(self.admin)
        data = {"nombre": "Preferente", "minimo_lavados": 50, "beneficio": "Limpieza de cristales", "cupo": 1, "vigencia_dias": 30, "activa": "on"}
        url = reverse("nexus:regla_crear")
        for field in ["minimo_lavados", "cupo", "vigencia_dias"]:
            response = self.client.post(url, {**data, field: 0})
            self.assertTrue(response.context["form"].has_error(field))
        self.assertEqual(self.client.post(url, data).status_code, 302)
        response = self.client.post(url, {**data, "nombre": "Duplicada"})
        self.assertTrue(response.context["form"].has_error("minimo_lavados"))
        self.assertEqual(ReglaBeneficio.objects.count(), 1)

    def test_company_name_is_unique_ignoring_case_and_whitespace(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("nexus:empresa_crear"), {"nombre": "  andes   rent  ", "activa": "on"})
        self.assertTrue(response.context["form"].has_error("nombre"))
        self.assertEqual(Empresa.objects.count(), 2)

    def test_core_includes_delivered_by_service_date_only_and_dense_ties(self):
        corte = (timezone.localdate().replace(day=1) - timedelta(days=1)).replace(day=1)
        start = desplazar_mes(corte, -2)
        otra = Empresa.objects.create(nombre="Costa Drive")
        for empresa in [self.empresa, otra]:
            for fecha in [start, corte]:
                trabajo = self.trabajo(empresa=empresa, fecha_servicio=fecha)
                self.entregar(trabajo)
        self.trabajo(fecha_servicio=corte)  # Pendiente excluido.
        self.entregar(self.trabajo(fecha_servicio=desplazar_mes(corte, -3)))  # Fuera del período.
        ReglaBeneficio.objects.create(nombre="Prueba", minimo_lavados=2, beneficio="Extra", cupo=1)
        resultado = comparar_empresas(corte)
        self.assertEqual(resultado["total_general"], 4)
        first, second = resultado["filas"][:2]
        self.assertEqual([first["puesto"], second["puesto"]], [1, 1])
        self.assertEqual(first["participacion"], 50)
        self.assertEqual(first["meses"], [1, 0, 1])
        self.assertEqual(first["regla"].nombre, "Prueba")

    def test_core_year_boundary_and_invalid_cutoff(self):
        self.assertEqual(desplazar_mes(date(2026, 1, 1), -2), date(2025, 11, 1))
        self.client.force_login(self.admin)
        response = self.client.get(reverse("nexus:comparativo"), {"corte": timezone.localdate().strftime("%Y-%m")})
        self.assertTrue(response.context["form"].has_error("corte"))

    def test_all_main_templates_render(self):
        self.client.force_login(self.admin)
        trabajo = self.trabajo()
        for name in ["nexus:dashboard", "nexus:empresas", "nexus:trabajos", "nexus:reglas", "nexus:comparativo", "nexus:empresa_crear", "nexus:regla_crear"]:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(reverse("nexus:trabajo_detalle", args=[trabajo.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("nexus:trabajo_entregar", args=[trabajo.pk])).status_code, 200)

    def test_catalog_crud_and_pending_deletion(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("nexus:empresa_crear"), {"nombre": "Nueva empresa", "activa": "on"}).status_code, 302)
        empresa = Empresa.objects.get(nombre="Nueva empresa")
        self.assertEqual(self.client.post(reverse("nexus:empresa_editar", args=[empresa.pk]), {"nombre": "Empresa editada", "activa": "on"}).status_code, 302)
        self.assertEqual(self.client.post(reverse("nexus:empresa_eliminar", args=[empresa.pk])).status_code, 302)
        self.assertFalse(Empresa.objects.filter(pk=empresa.pk).exists())
        regla = ReglaBeneficio.objects.create(nombre="Temporal", minimo_lavados=10, beneficio="Extra", cupo=1)
        self.assertEqual(self.client.post(reverse("nexus:regla_editar", args=[regla.pk]), {"nombre": "Editada", "minimo_lavados": 20, "beneficio": "Otro extra", "cupo": 2, "vigencia_dias": 15, "activa": "on"}).status_code, 302)
        regla.refresh_from_db()
        self.assertEqual(regla.minimo_lavados, 20)
        self.assertEqual(self.client.post(reverse("nexus:regla_eliminar", args=[regla.pk])).status_code, 302)
        trabajo = self.trabajo()
        self.assertEqual(self.client.post(reverse("nexus:trabajo_eliminar", args=[trabajo.pk])).status_code, 302)
        self.assertFalse(Trabajo.objects.filter(pk=trabajo.pk).exists())

    def test_startup_preserves_modified_rules(self):
        regla = ReglaBeneficio.objects.create(nombre="Personalizada", minimo_lavados=50, beneficio="Extra ajustado", cupo=4)
        output = io.StringIO()
        call_command("preparar_nexus", stdout=output)
        regla.refresh_from_db()
        self.assertEqual(ReglaBeneficio.objects.count(), 1)
        self.assertEqual(regla.nombre, "Personalizada")
        self.assertEqual(regla.cupo, 4)
