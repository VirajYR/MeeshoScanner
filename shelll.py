import fitz
with fitz.open("uploads/Supplier_Manifest.pdf") as doc:
    for page in doc:
        print(page.get_text())