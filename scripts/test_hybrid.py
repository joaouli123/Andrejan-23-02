"""
Quick test: process 3 pages of a PDF to validate hybrid Tesseract+Gemini pipeline.
Run inside the Docker container.
"""
import asyncio
import os
import sys
import time

# Add app to path
sys.path.insert(0, "/app")

from ingestion.open_source_vision import extract_page_open_source

async def test_pipeline():
    # Find any PDF in uploads
    uploads_dir = "/app/data/uploads"
    pdf_files = [f for f in os.listdir(uploads_dir) if f.endswith(".pdf")] if os.path.exists(uploads_dir) else []
    
    if not pdf_files:
        print("No PDF files in uploads. Checking for test PDF...")
        # List all data files
        for root, dirs, files in os.walk("/app/data"):
            for f in files:
                if f.endswith(".pdf"):
                    pdf_files.append(os.path.join(root, f))
                    break
    
    if not pdf_files:
        print("ERROR: No PDF files found to test!")
        print("Upload a PDF via the frontend first, or place one in /app/data/uploads/")
        return
    
    pdf_path = pdf_files[0]
    if not pdf_path.startswith("/"):
        pdf_path = os.path.join(uploads_dir, pdf_path)
    
    print(f"Testing with: {pdf_path}")
    print(f"Pipeline: Native → Tesseract (200 DPI) → Gemini 2.0 Flash")
    print("=" * 60)
    
    # Test pages 1, 2, 3
    for page_num in [1, 2, 3]:
        start = time.time()
        try:
            text, quality = await extract_page_open_source(pdf_path, page_num)
            elapsed = time.time() - start
            # Determine which tier was used (from log)
            tier = "unknown"
            if len(text) > 0:
                preview = text[:150].replace("\n", " ")
                print(f"\nPage {page_num}: {len(text)} chars, q={quality:.2f}, {elapsed:.1f}s")
                print(f"  Preview: {preview}...")
            else:
                print(f"\nPage {page_num}: EMPTY, {elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"\nPage {page_num}: ERROR ({elapsed:.1f}s) - {e}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
