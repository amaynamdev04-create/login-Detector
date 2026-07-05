"""Use pypandoc to create a prettier PDF from PROJECT_DOCS.md.

This script downloads a pandoc binary if needed and attempts to convert Markdown->PDF.
If PDF conversion fails due to missing LaTeX, it will write an HTML file instead.
"""
import sys
import pypandoc
from pathlib import Path

MD = Path("PROJECT_DOCS.md")
PDF = Path("PROJECT_DOCS_pandoc.pdf")
HTML = Path("PROJECT_DOCS_pandoc.html")

try:
    # ensure pandoc is available (pypandoc can download a binary)
    print("Downloading pandoc binary (if needed)...")
    pypandoc.download_pandoc()
    print("Pandoc download step completed.")
except Exception as exc:
    print("Warning: could not download pandoc:", exc)

try:
    # Try direct md -> pdf (may require LaTeX engine installed on system)
    print("Converting Markdown to PDF via pandoc...")
    pypandoc.convert_file(str(MD), 'pdf', outputfile=str(PDF))
    print(f"Wrote {PDF}")
except Exception as e:
    import traceback
    print("PDF conversion failed, writing HTML instead:", e)
    traceback.print_exc()
    try:
        print("Converting Markdown to HTML as fallback...")
        pypandoc.convert_file(str(MD), 'html', outputfile=str(HTML))
        print(f"Wrote {HTML}")
    except Exception as e2:
        import traceback
        print("HTML conversion failed:", e2)
        traceback.print_exc()
        sys.exit(2)
