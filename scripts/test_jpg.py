"""Test different DPI levels in PyMuPDF."""
import pymupdf
from pathlib import Path

doc = pymupdf.open("data/00_raw_pdfs/A001.pdf")
page = doc[3] # page 4

for dpi in [200, 150, 130, 100]:
    zoom = dpi / 72
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    png_path = Path(f"scratch/test_{dpi}.png")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(png_path))
    
    jpg_path = Path(f"scratch/test_{dpi}.jpg")
    pix.save(str(jpg_path), "jpg")
    
    print(f"DPI {dpi} -> PNG: {png_path.stat().st_size / 1024:.2f} KB | JPG: {jpg_path.stat().st_size / 1024:.2f} KB")
    
    png_path.unlink()
    jpg_path.unlink()

doc.close()
