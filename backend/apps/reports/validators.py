from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}


def validate_image_size(file) -> None:
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"La imagen excede el tamaño máximo de {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB."
        )


def validate_image_mimetype(file) -> None:
    # content_type only exists on fresh UploadedFile. Absent on FieldFile
    # loaded from storage during a save that doesn't replace the file —
    # in that case the mimetype was already checked on the original upload.
    mimetype = getattr(file, "content_type", None)
    if mimetype is None:
        return
    if mimetype not in ALLOWED_IMAGE_MIMETYPES:
        raise ValidationError(
            f"Formato no permitido ({mimetype}). Use JPEG, PNG o WebP."
        )


MAX_PDF_SIZE_BYTES = 20 * 1024 * 1024
ALLOWED_PDF_MIMETYPES = {"application/pdf"}


def validate_pdf_size(file) -> None:
    if file.size > MAX_PDF_SIZE_BYTES:
        raise ValidationError(
            f"El PDF excede el tamaño máximo de {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB."
        )


def validate_pdf_mimetype(file) -> None:
    mimetype = getattr(file, "content_type", None)
    if mimetype is None:
        return
    if mimetype not in ALLOWED_PDF_MIMETYPES:
        raise ValidationError(
            f"Formato no permitido ({mimetype}). Solo se aceptan PDFs."
        )
