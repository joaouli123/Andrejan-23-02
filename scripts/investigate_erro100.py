#!/usr/bin/env python3
"""Investigate why 'erro 100' is not found by the chatbot."""
import sqlite3

DB = "/app/data/andreja.db"
c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Search for pages containing error-related keywords with '100'
print("=" * 60)
print("1. PAGES CONTAINING 'erro' or 'error' near '100'")
print("=" * 60)
cur.execute("""
    SELECT document_id, page_number, length(gemini_text), gemini_text
    FROM pages
    WHERE lower(gemini_text) LIKE '%erro%100%'
       OR lower(gemini_text) LIKE '%error%100%'
       OR lower(gemini_text) LIKE '%100%erro%'
    ORDER BY document_id, page_number
""")
rows = cur.fetchall()
print(f"Found {len(rows)} pages")
for r in rows:
    doc_id, pg, tlen, text = r
    # Find context around 'erro' or '100'
    tl = text.lower()
    idx = tl.find("erro")
    if idx == -1:
        idx = tl.find("100")
    start = max(0, idx - 100)
    end = min(len(text), idx + 200)
    snippet = text[start:end].replace("\n", " ")
    print(f"  Doc {doc_id}, Page {pg}, TextLen={tlen}")
    print(f"  ...{snippet}...")
    print()

# 2. Search for E100 code
print("=" * 60)
print("2. PAGES CONTAINING 'E100' or 'e100'")
print("=" * 60)
cur.execute("""
    SELECT document_id, page_number, length(gemini_text), gemini_text
    FROM pages
    WHERE gemini_text LIKE '%E100%' OR gemini_text LIKE '%e100%'
    ORDER BY document_id, page_number
""")
rows = cur.fetchall()
print(f"Found {len(rows)} pages")
for r in rows:
    doc_id, pg, tlen, text = r
    tl = text.lower()
    idx = tl.find("e100")
    if idx == -1:
        idx = tl.find("100")
    start = max(0, idx - 100)
    end = min(len(text), idx + 200)
    snippet = text[start:end].replace("\n", " ")
    print(f"  Doc {doc_id}, Page {pg}, TextLen={tlen}")
    print(f"  ...{snippet}...")
    print()

# 3. Search for just 'display' keyword (since user asked about display error)
print("=" * 60)
print("3. PAGES CONTAINING 'display'")
print("=" * 60)
cur.execute("""
    SELECT document_id, page_number, length(gemini_text)
    FROM pages
    WHERE lower(gemini_text) LIKE '%display%'
    ORDER BY document_id, page_number
""")
rows = cur.fetchall()
print(f"Found {len(rows)} pages with 'display'")
for r in rows:
    print(f"  Doc {r[0]}, Page {r[1]}, TextLen={r[2]}")

# 4. Search broadly for '100' 
print()
print("=" * 60)
print("4. PAGES CONTAINING '100' (first 20)")
print("=" * 60)
cur.execute("""
    SELECT document_id, page_number, length(gemini_text)
    FROM pages
    WHERE gemini_text LIKE '%100%'
    ORDER BY document_id, page_number
    LIMIT 20
""")
rows = cur.fetchall()
print(f"Found pages (showing up to 20):")
for r in rows:
    print(f"  Doc {r[0]}, Page {r[1]}, TextLen={r[2]}")

# 5. Pages with very short text (possible extraction failures)
print()
print("=" * 60)
print("5. PAGES WITH SHORT TEXT (<100 chars)")
print("=" * 60)
cur.execute("""
    SELECT document_id, page_number, length(gemini_text), quality_score, gemini_text
    FROM pages
    WHERE length(gemini_text) < 100
    ORDER BY document_id, page_number
""")
rows = cur.fetchall()
print(f"Found {len(rows)} pages with <100 chars")
for r in rows:
    print(f"  Doc {r[0]}, Page {r[1]}, TextLen={r[2]}, Quality={r[3]}")
    print(f"  Text: {repr(r[4][:100])}")
    print()

# 6. Overall stats
print("=" * 60)
print("6. OVERALL STATS")
print("=" * 60)
cur.execute("""
    SELECT document_id, count(*), 
           avg(length(gemini_text)), 
           min(length(gemini_text)), 
           max(length(gemini_text)),
           sum(CASE WHEN length(gemini_text) < 50 THEN 1 ELSE 0 END) as short_pages,
           sum(CASE WHEN embedding_id IS NOT NULL AND embedding_id != '' THEN 1 ELSE 0 END) as with_embeddings
    FROM pages GROUP BY document_id
""")
for r in cur.fetchall():
    print(f"  Doc {r[0]}: {r[1]} pages, avg_len={r[2]:.0f}, min={r[3]}, max={r[4]}, short={r[5]}, embeddings={r[6]}")

# 7. Check Qdrant collection info
print()
print("=" * 60)
print("7. SAMPLE EMBEDDING IDs")
print("=" * 60)
cur.execute("SELECT page_number, embedding_id FROM pages WHERE document_id=1 LIMIT 5")
for r in cur.fetchall():
    print(f"  Page {r[0]}: embedding_id={r[1]}")

c.close()
