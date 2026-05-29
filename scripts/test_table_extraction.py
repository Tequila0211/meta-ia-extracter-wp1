"""Test PyMuPDF table extraction with borderless settings on A001.pdf."""
import pymupdf

doc = pymupdf.open("data/00_raw_pdfs/A001.pdf")
print(f"Total pages: {len(doc)}")

for page_num in range(len(doc)):
    page = doc[page_num]
    
    # Try different strategies for borderless tables
    tables = page.find_tables(
        strategy="text" # strategy='text' tells PyMuPDF to find tables based on text alignment!
    )
    
    table_list = tables.tables
    if table_list:
        print(f"\n--- Page {page_num + 1} has {len(table_list)} tables ---")
        for i, t in enumerate(table_list):
            data = t.extract()
            print(f"Table {i+1} dimensions: {len(data)}x{len(data[0]) if data else 0}")
            for row in data[:4]: # print first 4 rows
                print("  ", [str(c or "").strip().replace('\n', ' ') for c in row])

doc.close()
