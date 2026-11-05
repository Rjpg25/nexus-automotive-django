# Nexus Automotive · Administración con Django y Bootstrap

Administración web que alimenta el CORE aprobado **«Comparación de empresas y beneficios por volumen»**. Integra la autenticación del proyecto `crud-login-django` con el registro de empresas, trabajos, entregas firmadas y reglas de beneficios.

**Autor:** Ricardo José Piñango González · Ingeniería en Software · UDLA · Ingeniería Web.

## Entrega y alcance

Esta versión implementa la administración y una consulta funcional del comparativo. La aplicación utiliza datos reales guardados en su propia base; no depende de JavaScript para validar fechas, relaciones, permisos o reglas.

| Directriz académica | Implementación | Evidencia |
| --- | --- | --- |
| Login integrado | `LoginView`, `LogoutView` por POST y sesiones de Django | `config/urls.py` y `templates/registration/login.html` |
| Administración MVC basada en el CORE | CRUD de empresas, trabajos y reglas, entrega firmada y auditoría | App `nexus` y plantillas Bootstrap |
| Validación sensible en back-end | Fecha del servicio no futura; firma obligatoria al entregar; umbrales, cupos y vigencias positivos; umbral activo único | `validators.py`, `models.py`, formularios y pruebas sin JS |
| Referencias mediante selección | Empresa es una FK y se elige por nombre en un `ModelChoiceField` | `TrabajoForm`: queryset de empresas permitidas |
| Control de roles en servidor | Operadora no accede a empresas, reglas, entregas ni comparativo aunque escriba la URL | `permissions.py` y decoradores `acceso` |
| Código versionado y README | Repositorio de Nexus Automotive, rama `main` | Historial Git y este archivo |
| Configuración de despliegue | PostgreSQL, Gunicorn, WhiteNoise, variables de entorno y health check | `render.yaml`, `build.sh`, `start.sh` |
| Video | Demostración de la administración y sus validaciones | Pendiente de grabación y publicación |

**Estado:** administración funcional en local. El despliegue y el video de demostración están pendientes de publicación.

## Funciones

- Login y cierre de sesión; navegación según rol.
- Resumen del lavadero con contadores consultados desde la base.
- Empresas: crear, listar, buscar, editar, activar/desactivar y eliminar si no tienen trabajos.
- Trabajos: crear, listar con filtros y paginación, ver detalle y corregir con motivo obligatorio y auditoría.
- Una empresa activa se selecciona mediante dropdown. El POST de una empresa inexistente o inactiva es rechazado. Un trabajo histórico conserva su empresa aunque después se desactive.
- La patente se normaliza a mayúsculas sin espacios ni guiones y exige entre 5 y 10 caracteres alfanuméricos, con letras y números. Es una regla operativa general; no valida una matrícula contra un registro gubernamental.
- Entrega: nombre y tipo de firmante, firma dibujada, responsable y fecha de confirmación.
- El servidor comprueba que la firma sea un PNG de tamaño acotado y tenga trazos visibles. No autentica biométricamente la identidad ni produce una firma criptográfica.
- Un trabajo entregado se conserva; su corrección solo corresponde a la administradora. Un pendiente puede corregirse por ambos roles y eliminarse por la administradora.
- Reglas: CRUD de nivel, mínimo, beneficio, cupo, vigencia y estado.
- Comparativo: tres meses completos por fecha del servicio, solo entregados, ranking denso, participación, variación y mayor umbral aplicable. Conserva empresas inactivas y sin actividad.

La aprobación inmutable de evaluaciones, asignaciones definitivas, canjes y exportación Excel corresponden a la siguiente etapa del CORE. La sincronización con MAUI/Firebase no se implementa en esta entrega. Los precios, cobros y facturación siguen fuera del alcance.

## Instalar en Windows / VS Code

Probado con Python 3.12 y Django 5.2.19. El proyecto anterior usaba 5.2.17; esta rama fija una revisión posterior de la misma serie.

Abre una terminal PowerShell en la carpeta del proyecto. Si descargaste un ZIP, extráelo antes; no lo ejecutes desde dentro del comprimido.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copia la clave generada a `DJANGO_SECRET_KEY=` dentro de `.env`. Mantén `DJANGO_DEBUG=true` solo en desarrollo. La clave se genera en tu equipo; nunca se sube a Git.

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py preparar_nexus --demo
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver --noreload
```

Abre **http://127.0.0.1:8000/** e inicia sesión con el superusuario que acabas de crear. No hay una contraseña universal incluida en el proyecto.

`--demo` añade únicamente cinco empresas ficticias: Andes Rent, Costa Drive, Sierra Móvil, Ruta Express y MoviCar. No inventa servicios ni firmas. Las tres reglas iniciales se crean una sola vez con una migración de datos. Reiniciar o volver a desplegar no restaura reglas que hayas cambiado o eliminado.

## Instalar en Linux / macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
# Pega la clave generada en DJANGO_SECRET_KEY dentro de .env.
.venv/bin/python manage.py migrate
.venv/bin/python manage.py preparar_nexus --demo
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver --noreload
```

## Roles y usuarios

| Operación | Administradora / superusuario | Operador |
| --- | --- | --- |
| Resumen, listar y consultar trabajos | Sí | Sí |
| Registrar trabajo y corregir pendiente con motivo | Sí | Sí |
| Corregir entregado con motivo | Sí | No |
| Confirmar entrega con firma | Sí | No |
| Eliminar pendiente | Sí | No |
| Empresas, reglas y comparativo | Sí | No |
| Gestión técnica de cuentas y grupos | Superusuario | No |

Las autorizaciones se comprueban en cada vista, antes de leer o escribir datos. Ocultar botones no es el control de seguridad. `is_staff` por sí solo no concede el rol de administradora de Nexus.

Para crear una cuenta operativa, entra como superusuario a **`/admin/auth/user/`**. Crea un usuario con su propia contraseña y asígnale uno de los grupos `Administradora` u `Operador`. Una cuenta sin grupo ni condición de superusuario recibe acceso denegado. Para cuentas operativas no necesitas activar el acceso al admin técnico.

## Datos y relación con MVC

Django utiliza MVT. Su `View` recibe y procesa solicitudes; su `Template` representa la vista de presentación del enfoque MVC. La lógica de negocio compartida se separa en validadores, modelos y servicios.

| Archivo / carpeta | Responsabilidad |
| --- | --- |
| `config/settings.py` | Entorno, base de datos, sesiones, estáticos y seguridad |
| `config/urls.py` | Login, logout, admin técnico y rutas de Nexus |
| `nexus/models.py` | Empresa, Trabajo, ReglaBeneficio y Correccion; validación y restricciones |
| `nexus/validators.py` | Fecha, patente e imagen de firma |
| `nexus/forms.py` | Formularios, dropdown de FK y campos permitidos |
| `nexus/permissions.py` | Acceso de administradora y operador |
| `nexus/views.py` | Coordinación de altas, consultas, correcciones, entregas y eliminaciones |
| `nexus/services.py` | Cálculo del comparativo de tres meses |
| `nexus/migrations/` | Esquema y datos iniciales versionados |
| `templates/nexus/` | Pantallas administrativas |
| `templates/registration/login.html` | Login integrado |
| `static/nexus/` | Estilo Nexus y recuadro de firma |
| `static/vendor/` | Bootstrap 5.3.8 local; no necesita un CDN al usar la web |
| `nexus/tests.py` | Pruebas de acceso, integridad y reglas del negocio |

El modelo usa el usuario de Django para creador, entregador y autor de correcciones. Esas relaciones se asignan desde la sesión del servidor; no se escriben como IDs en un input. En la creación de usuarios, la relación con grupos usa el selector del administrador de Django. No se agrega una jerarquía artificial de país/provincia porque el modelo aprobado no la necesita.

El antiguo módulo `productos/` se conserva como referencia del proyecto base, pero está fuera de las aplicaciones instaladas, de las rutas y de la navegación de Nexus. Sus plantillas no interfieren con las nuevas.

## Validaciones del CORE

1. `validar_fecha_servicio` rechaza fechas futuras, que distorsionarían el período del ranking.
2. `TrabajoForm` comprueba la FK contra empresas activas; preserva la empresa histórica al editar un trabajo asociado a una empresa que después se desactivó.
3. `Trabajo.clean` impide entregas parciales. `ValidatedModel.save` llama a `full_clean` antes de guardar, también fuera del formulario.
4. `validar_firma` decodifica el PNG en Python, limita sus dimensiones y rechaza imágenes vacías o archivos falsos. El servidor no confía en el valor del campo oculto.
5. `ReglaBeneficio` exige mínimo, cupo y vigencia positivos; un índice único condicional impide mínimos activos repetidos.
6. La base contiene una restricción para que un estado entregado incluya firmante, tipo, firma, fecha y responsable. Las FK usan `PROTECT` para conservar referencias operativas.
7. Las correcciones y entregas se guardan en transacciones. En PostgreSQL se bloquea el trabajo durante la operación para evitar entregas simultáneas.
8. Las escrituras usan POST con CSRF. El estado, creador y responsable no se aceptan del formulario de creación.

Los formularios administrativos llevan `novalidate` intencionalmente: los mensajes de rechazo se obtienen del back-end y pueden demostrarse incluso sin validación HTML o JS. La captura del dibujo sí usa JavaScript, y una solicitud sin firma válida continúa siendo rechazada en Python.

## Reglas iniciales y comparativo

| Nivel | Mínimo en tres meses | Beneficio | Cupo | Vigencia propuesta |
| --- | --- | --- | --- | --- |
| Preferente | 50 | Limpieza de cristales complementaria | 1 | 30 días |
| Plus | 100 | Limpieza de cristales complementaria | 2 | 30 días |
| Premium | 150 | Limpieza de cristales complementaria | 3 | 30 días |

Son parámetros propuestos en el análisis, editables por la administradora. El mayor umbral cumplido determina el nivel, sin acumular niveles ni limitar los beneficios al top 3. Menos de 50 lavados queda sin beneficio con estas reglas iniciales.

En **Comparativo** selecciona el último mes cerrado. Si el corte es septiembre de 2026 se evalúan julio, agosto y septiembre, usando la fecha del servicio. Los pendientes no cuentan. Una nueva visita con la misma patente es otro trabajo válido: no se cuentan vehículos únicos.

Participación = total de la empresa / total de todas las empresas × 100. Variación = (último mes − primer mes) / primer mes × 100. Se controlan los ceros; los empates comparten puesto con ranking denso, por ejemplo 1, 1, 2. Esta consulta es dinámica; no equivale a una evaluación aprobada archivada.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test nexus --verbosity 2
```

Las pruebas cubren login, logout por POST, CSRF, roles, dropdown, FK falsificada o inactiva, fecha futura mediante POST y `save`, normalización de patente, campos de sesión manipulados, firmas inválidas o vacías, entregas repetidas, restricción de integridad, correcciones auditadas, protección del historial, umbrales y nombres duplicados, cálculo del comparativo y cambio de año.

Las pruebas automáticas comprueban las rutas y plantillas con el cliente de pruebas de Django. Para la demostración también se revisan las operaciones desde el navegador.

Para comprobar la configuración de producción, define `DJANGO_DEBUG=false`, una clave fuerte y los hosts del servidor antes de ejecutar `python manage.py check --deploy --fail-level WARNING`. Los archivos estáticos se preparan con `python manage.py collectstatic --noinput`.

## Repositorio y rama principal

[Repositorio de Nexus Automotive](https://github.com/Rjpg25/nexus-automotive-django)

La rama principal es `main`. El proyecto toma como base el login y CRUD de productos desarrollado anteriormente y añade la administración específica de Nexus Automotive.

El repositorio excluye `.env`, `.venv`, SQLite y la carpeta local `docs/`. La configuración de ejemplo se conserva en `.env.example`. Los saltos de línea de los archivos de texto se normalizan a LF mediante `.gitattributes`.

## Despliegue en Render

La publicación utiliza una aplicación Python con PostgreSQL, Gunicorn y WhiteNoise. `render.yaml` configura el servicio para la rama `main`.

1. Crea o selecciona una base PostgreSQL destinada a Nexus. Para una conexión interna, la base y el servicio web deben estar en la misma región.
2. En Render crea un Web Service conectado a este repositorio y selecciona `main`, o utiliza el Blueprint `render.yaml`.
3. Configura las variables del servidor según la tabla siguiente.
4. Espera a que el servicio esté disponible y comprueba la URL asignada por Render, el login y `/health/`.

| Ajuste | Valor |
| --- | --- |
| Runtime | Python 3 |
| Build command | `bash build.sh` |
| Start command | `bash start.sh` |
| Health check | `/health/` |
| Rama | `main` |

| Variable | Configuración |
| --- | --- |
| `PYTHON_VERSION` | `3.12.14` en el despliegue preparado |
| `DJANGO_SECRET_KEY` | Clave propia de al menos 50 caracteres, generada con `get_random_secret_key()` |
| `DJANGO_DEBUG` | `false` |
| `DATABASE_URL` | Conexión PostgreSQL de Nexus |
| `NEXUS_ADMIN_USERNAME` | Usuario inicial de administración |
| `NEXUS_ADMIN_PASSWORD` | Contraseña fuerte configurada como secreto del servidor |
| `WEB_CONCURRENCY` | `2` |

`build.sh` instala dependencias, prepara los archivos estáticos y verifica la configuración de producción. `start.sh` aplica migraciones, comprueba roles y cuenta inicial, y arranca Gunicorn. La cuenta inicial solo se crea si no existe; una publicación posterior conserva los usuarios y reglas existentes.

Después de crear la cuenta inicial, retira `NEXUS_ADMIN_PASSWORD` del entorno del servidor. El usuario ya creado se mantiene en la base. Los hosts y el origen CSRF de Render se obtienen de `RENDER_EXTERNAL_HOSTNAME`; un dominio propio debe añadirse a `DJANGO_ALLOWED_HOSTS` y `DJANGO_CSRF_TRUSTED_ORIGINS`.

El plan Free de Render tiene limitaciones: los archivos locales del servicio son temporales, la aplicación puede suspenderse por inactividad y una base PostgreSQL Free expira a los 30 días. La configuración usa PostgreSQL para guardar registros y firmas. Consulta las condiciones vigentes en [Render Free](https://render.com/docs/free).

**URL desplegada:** pendiente de publicación.

## Video de demostración

**Enlace de YouTube o Loom:** pendiente de grabación y publicación.

La demostración presenta login, CRUD de empresas, selección de empresa mediante dropdown, registro y entrega de un trabajo con firma y rechazo de un dato inválido desde el back-end. También muestra la separación MVT/MVC, este repositorio y la URL desplegada.

## Interfaz y dependencias de terceros

La interfaz incluye Bootstrap 5.3.8 distribuido bajo [licencia MIT](https://github.com/twbs/bootstrap/blob/v5.3.8/LICENSE). Los archivos de `static/vendor/` conservan sus encabezados de licencia. La marca SVG es una interpretación tipográfica editable para esta web.

## Referencias oficiales

- ModelForm y ModelChoiceField: https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/
- Autenticación: https://docs.djangoproject.com/en/5.2/topics/auth/default/
- Validación de modelos: https://docs.djangoproject.com/en/5.2/ref/models/instances/#validating-objects
- Restricciones: https://docs.djangoproject.com/en/5.2/ref/models/constraints/
- Despliegue: https://render.com/docs/deploy-django
