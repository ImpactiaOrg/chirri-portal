from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image_size(file) -> None:
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"La imagen excede el tamaño máximo de {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB."
        )


def validate_image_mimetype(file) -> None:
    mimetype = getattr(file, "content_type", None)
    if mimetype not in ALLOWED_IMAGE_MIMETYPES:
        raise ValidationError(
            f"Formato no permitido ({mimetype}). Use JPEG, PNG o WebP."
        )
