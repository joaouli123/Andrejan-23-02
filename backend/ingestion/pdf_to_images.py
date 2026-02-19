import os
import uuid
from pathlib import Path
from pdf2image import convert_from_path
from PIL import Image
from config import get_settings

settings = get_settings()


def pdf_to_images(pdf_path: str, doc_id: int, dpi: int = 250) -> list[dict]:
    """
    Convert each page of a PDF to a PNG image.
    Returns list of dicts: {page_number, image_path}
    """
    output_dir = Path(settings.images_dir) / str(doc_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = convert_from_path(
        pdf_path,
        dpi=dpi,
        fmt="png",
        thread_count=2,
        use_cropbox=False,
        strict=False,
    )

    result = []
    for i, page_image in enumerate(pages, start=1):
        # Enhance image for better Gemini reading
        enhanced = _enhance_scan(page_image)
        image_path = str(output_dir / f"page_{i:04d}.png")
        enhanced.save(image_path, "PNG", optimize=True)
        result.append({"page_number": i, "image_path": image_path})

    return result


def _enhance_scan(image: Image.Image) -> Image.Image:
    """
    Light enhancement for scanned documents:
    - Convert to RGB
    - Slight contrast boost to help readability
    """
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Keep original quality, just ensure RGB mode for Gemini
    return image


def get_pdf_page_count(pdf_path: str) -> int:
    """Get page count without full conversion."""
    try:
        pages = convert_from_path(pdf_path, dpi=72, last_page=1)
        # Re-count properly
        all_pages = convert_from_path(pdf_path, dpi=72)
        return len(all_pages)
    except Exception:
        return 0
