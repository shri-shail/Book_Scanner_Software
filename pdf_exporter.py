"""Create a multi-page PDF from saved page images."""
from pathlib import Path

def export_pdf(image_paths, output_path):
    image_paths = [Path(p) for p in image_paths if Path(p).exists()]
    if not image_paths:
        raise RuntimeError("There are no saved page images to export.")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import img2pdf
        with output_path.open("wb") as pdf_file:
            pdf_file.write(img2pdf.convert([str(p) for p in image_paths]))
    except ImportError:
        # Pillow fallback keeps the prototype usable if img2pdf was not installed.
        from PIL import Image
        pages = []
        for path in image_paths:
            im = Image.open(path).convert("RGB")
            pages.append(im)
        first, rest = pages[0], pages[1:]
        first.save(output_path, "PDF", save_all=True, append_images=rest, resolution=150)
    return output_path
