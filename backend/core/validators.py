import contextlib
import xml.etree.ElementTree as ET

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

IMAGE_ERROR = (
    "Upload a valid image. The file you uploaded was either not an image "
    "or a corrupted image."
)
SVG_ERROR = "Upload a valid SVG file."

_FORBIDDEN_ELEMENTS = {"script", "foreignobject", "iframe", "object", "embed"}
_ALLOWED_DATA_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/gif;base64,",
    "data:image/webp;base64,",
)


def _local_name(name):
    return name.rsplit("}", 1)[-1].lower()


def _read(value):
    value.seek(0)
    data = value.read()
    value.seek(0)
    return data


def _validate_svg(value):
    data = _read(value)
    lowered = data.lower()
    if b"<!entity" in lowered or b"javascript:" in lowered:
        raise ValidationError(SVG_ERROR)
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValidationError(SVG_ERROR) from exc
    if _local_name(root.tag) != "svg":
        raise ValidationError(SVG_ERROR)
    for element in root.iter():
        if _local_name(element.tag) in _FORBIDDEN_ELEMENTS:
            raise ValidationError(SVG_ERROR)
        for raw_name, raw_value in element.attrib.items():
            name = _local_name(raw_name)
            target = (raw_value or "").strip().lower()
            if name.startswith("on"):
                raise ValidationError(SVG_ERROR)
            if name == "style" and ("javascript:" in target or "expression(" in target):
                raise ValidationError(SVG_ERROR)
            if (
                name == "href"
                and target
                and not target.startswith("#")
                and not target.startswith(_ALLOWED_DATA_IMAGE_PREFIXES)
            ):
                raise ValidationError(SVG_ERROR)


def validate_sponsor_logo(value):
    name = (getattr(value, "name", "") or "").lower()
    content_type = (getattr(value, "content_type", "") or "").lower()
    if name.endswith(".svg") or content_type == "image/svg+xml":
        _validate_svg(value)
        return
    try:
        Image.open(value).verify()
    except (
        Image.DecompressionBombError,
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise ValidationError(IMAGE_ERROR) from exc
    finally:
        with contextlib.suppress(OSError, ValueError):
            value.seek(0)
