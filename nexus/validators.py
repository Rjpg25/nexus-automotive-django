"""Validaciones ejecutadas en Python antes de guardar datos del CORE."""
import base64
import binascii
import io
import re
import warnings
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image, ImageChops, UnidentifiedImageError

def validar_fecha_servicio(value):
    if value > timezone.localdate():
        raise ValidationError("La fecha del servicio no puede estar en el futuro.")

def normalizar_patente(value):
    return re.sub(r"[\s-]+", "", value.strip().upper())

def validar_patente(value):
    if not re.fullmatch(r"(?=.*[A-Z])(?=.*[0-9])[A-Z0-9]{5,10}", value, re.ASCII):
        raise ValidationError("Usa entre 5 y 10 letras y números; incluye al menos una letra y un número.")

def validar_firma(value):
    """Valida un PNG acotado con trazos; no verifica identidad biométrica."""
    if not value:
        return
    try:
        if not value.startswith("data:image/png;base64,") or len(value) > 350_000:
            raise ValueError
        raw = base64.b64decode(value.split(",", 1)[1], validate=True)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as im:
                if im.format != "PNG" or not (100 <= im.width <= 1600 and 40 <= im.height <= 800):
                    raise ValueError
                im.load()
                rgba = im.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "white")
                background.alpha_composite(rgba)
                difference = ImageChops.difference(background.convert("RGB"), Image.new("RGB", rgba.size, "white")).convert("L")
                if sum(difference.histogram()[20:]) < 40:
                    raise ValueError
    except (ValueError, binascii.Error, UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("Registra una firma visible y válida en el recuadro (PNG, máximo 250 KB).")
