import sqlite3
import os

DB_PATH = os.environ.get("DB_PATH", "/app/data/andreja.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# marcas com docs processados
cur.execute(
    """
    SELECT b.id, b.name, b.slug, COUNT(d.id) as processed_docs
    FROM brands b
    JOIN documents d ON d.brand_id = b.id
    WHERE d.status IN ('completed', 'completed_with_errors')
    GROUP BY b.id, b.name, b.slug
    HAVING processed_docs > 0
    ORDER BY b.name
    """
)
brands = cur.fetchall()

# agentes
cur.execute(
    """
    SELECT id, name, brand_id
    FROM agents
    ORDER BY name
    """
)
agents = cur.fetchall()

agents_by_brand = {}
for agent_id, agent_name, brand_id in agents:
    agents_by_brand.setdefault(brand_id, []).append((agent_id, agent_name))

missing = []
matched = []

for brand_id, brand_name, brand_slug, processed_docs in brands:
    linked = agents_by_brand.get(brand_id, [])
    if linked:
        matched.append((brand_name, processed_docs, linked))
    else:
        # tentativa por nome
        cur.execute(
            """
            SELECT id, name FROM agents
            WHERE LOWER(name)=LOWER(?)
            LIMIT 3
            """,
            (brand_name,),
        )
        by_name = cur.fetchall()
        if by_name:
            matched.append((brand_name, processed_docs, by_name))
        else:
            missing.append((brand_id, brand_name, brand_slug, processed_docs))

print("=== AUDITORIA AGENTES x MARCAS PROCESSADAS ===")
print(f"Marcas com docs processados: {len(brands)}")
print(f"Agentes totais: {len(agents)}")
print(f"Marcas cobertas por agente: {len(matched)}")
print(f"Marcas sem agente: {len(missing)}")

print("\n=== COBERTAS (marca -> agentes) ===")
for brand_name, processed_docs, linked in matched:
    names = ", ".join([f"{a_name} ({a_id})" for a_id, a_name in linked])
    print(f"OK | {brand_name} | docs={processed_docs} | agentes={names}")

print("\n=== FALTANDO ===")
if missing:
    for brand_id, brand_name, brand_slug, processed_docs in missing:
        print(f"MISSING | id={brand_id} | {brand_name} ({brand_slug}) | docs={processed_docs}")
else:
    print("Nenhuma marca faltando.")

# duplicatas por brand
print("\n=== DUPLICIDADE DE AGENTES POR MARCA ===")
cur.execute(
    """
    SELECT b.name, COUNT(a.id) as qtd
    FROM brands b
    JOIN agents a ON a.brand_id = b.id
    GROUP BY b.id, b.name
    HAVING qtd > 1
    ORDER BY qtd DESC
    """
)
dups = cur.fetchall()
if dups:
    for brand_name, qty in dups:
        print(f"DUP | {brand_name} | agentes={qty}")
else:
    print("Sem duplicidade por brand_id.")

conn.close()
