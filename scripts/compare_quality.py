"""
Compara texto extraído e salvo no banco com re-extração direta do PDF.
Roda dentro do container Docker no VPS.
"""
import sqlite3
import sys

# Páginas para comparar (amostras variadas)
SAMPLE_PAGES = [1, 2, 3, 5, 8, 10, 15, 20, 25]

def main():
    db = sqlite3.connect("/app/data/andreja.db")
    cur = db.cursor()
    
    # Pegar o documento mais recente
    cur.execute("SELECT id, filename, status, processed_pages, total_pages FROM documents ORDER BY id DESC LIMIT 1")
    doc = cur.fetchone()
    if not doc:
        print("Nenhum documento encontrado!")
        return
    
    doc_id, filename, status, processed, total = doc
    print(f"=== Documento: {filename} ===")
    print(f"Status: {status} | Processado: {processed}/{total}")
    print()
    
    # Pegar páginas salvas
    cur.execute(
        "SELECT page_number, gemini_text, quality_score FROM pages WHERE document_id = ? ORDER BY page_number",
        (doc_id,)
    )
    pages = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
    
    print(f"Total de páginas salvas no banco: {len(pages)}")
    print()
    
    for pg in SAMPLE_PAGES:
        if pg > processed:
            continue
        if pg not in pages:
            print(f"--- PÁGINA {pg}: NÃO ENCONTRADA NO BANCO! ---")
            continue
        
        content, quality = pages[pg]
        content_clean = content.strip() if content else ""
        
        print(f"{'='*60}")
        print(f"PÁGINA {pg} | Qualidade: {quality:.2f} | Chars salvos: {len(content_clean)}")
        print(f"{'='*60}")
        
        # Mostrar primeiros 500 chars do texto salvo
        preview = content_clean[:500]
        if len(content_clean) > 500:
            preview += f"\n... [{len(content_clean) - 500} chars restantes]"
        print(preview)
        print()
    
    # Estatísticas gerais
    print(f"\n{'='*60}")
    print("ESTATÍSTICAS GERAIS")
    print(f"{'='*60}")
    
    total_chars = 0
    empty_pages = 0
    short_pages = 0
    
    for pg_num, (content, quality) in sorted(pages.items()):
        chars = len(content.strip()) if content else 0
        total_chars += chars
        if chars == 0:
            empty_pages += 1
        elif chars < 30:
            short_pages += 1
    
    print(f"Páginas salvas: {len(pages)}")
    print(f"Total de caracteres: {total_chars:,}")
    print(f"Média chars/página: {total_chars // len(pages) if pages else 0:,}")
    print(f"Páginas vazias: {empty_pages}")
    print(f"Páginas curtas (<30 chars): {short_pages}")
    
    # Listar páginas curtas para inspeção
    if short_pages > 0 or empty_pages > 0:
        print(f"\nPáginas problemáticas:")
        for pg_num, (content, quality) in sorted(pages.items()):
            chars = len(content.strip()) if content else 0
            if chars < 30:
                preview = (content.strip()[:80] if content else "(vazio)")
                print(f"  Pág {pg_num}: {chars} chars → {preview}")

if __name__ == "__main__":
    main()
