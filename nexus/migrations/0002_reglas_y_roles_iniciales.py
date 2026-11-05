from django.db import migrations

def inicializar(apps, schema_editor):
    Regla = apps.get_model("nexus", "ReglaBeneficio")
    Group = apps.get_model("auth", "Group")
    for nombre in ["Administradora", "Operador"]:
        Group.objects.get_or_create(name=nombre)
    for nombre, minimo, cupo in [("Preferente", 50, 1), ("Plus", 100, 2), ("Premium", 150, 3)]:
        Regla.objects.get_or_create(minimo_lavados=minimo, activa=True, defaults={"nombre": nombre, "beneficio": "Limpieza de cristales complementaria", "cupo": cupo, "vigencia_dias": 30})

class Migration(migrations.Migration):
    dependencies = [("nexus", "0001_initial")]
    operations = [migrations.RunPython(inicializar, migrations.RunPython.noop)]
