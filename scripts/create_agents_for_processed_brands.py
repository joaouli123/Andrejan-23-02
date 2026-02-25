import os
import re
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "/app/data/andreja.db")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "marca"


# Ensure agents table exists
cur.execute(
    """
    SELECT name FROM sqlite_master
    WHERE type='table' AND name='agents'
    """
)
if not cur.fetchone():
    print("ERRO: tabela 'agents' não existe neste banco.")
    conn.close()
    raise SystemExit(1)

# Pick an admin user for created_by
cur.execute("SELECT id FROM users WHERE is_admin=1 ORDER BY id LIMIT 1")
admin_row = cur.fetchone()
admin_id = admin_row[0] if admin_row else None

# Brands that actually have processed docs
cur.execute(
    """
    SELECT b.id, b.slug, b.name, COUNT(d.id) as processed_docs
    FROM brands b
    JOIN documents d ON d.brand_id = b.id
    WHERE d.status IN ('completed', 'completed_with_errors')
    GROUP BY b.id, b.slug, b.name
    HAVING processed_docs > 0
    ORDER BY b.name
    """
)
brands = cur.fetchall()

print(f"Marcas com PDFs processados: {len(brands)}")

created = []
skipped = []

for brand_id, brand_slug, brand_name, processed_docs in brands:
    # Skip if there is already an agent linked to this brand OR same name
    cur.execute(
        """
        SELECT id, name
        FROM agents
        WHERE brand_id = ? OR LOWER(name) = LOWER(?)
        LIMIT 1
        """,
        (brand_id, brand_name),
    )
    existing = cur.fetchone()
    if existing:
        skipped.append((brand_name, existing[0], existing[1]))
        continue

    safe_slug = slugify(brand_slug or brand_name)
    agent_id = f"brand-{safe_slug}"

    # Guarantee unique id if already used
    suffix = 2
    cur.execute("SELECT 1 FROM agents WHERE id=?", (agent_id,))
    while cur.fetchone():
        agent_id = f"brand-{safe_slug}-{suffix}"
        suffix += 1
        cur.execute("SELECT 1 FROM agents WHERE id=?", (agent_id,))

    role = f"Especialista {brand_name}"
    description = (
        f"Tire dúvidas técnicas da {brand_name}: falhas, códigos, placas,"
        f" parametrização, ajustes e procedimentos com base nos manuais processados."
    )
    system_instruction = (
        f"Você é um especialista técnico da marca {brand_name}. "
        f"Antes de responder diagnósticos, peça modelo/placa/código quando faltar contexto. "
        f"Use apenas conteúdo dos manuais indexados desta marca e cite fontes com página."
    )

    cur.execute(
        """
        INSERT INTO agents (
            id, name, role, description, icon, color,
            system_instruction, brand_id, is_custom, created_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            agent_id,
            brand_name,
            role,
            description,
            "Wrench",
            "blue",
            system_instruction,
            brand_id,
            1,
            admin_id,
        ),
    )
    created.append((brand_name, agent_id, processed_docs))

conn.commit()

print("\n=== CRIADOS ===")
if created:
    for name, agent_id, docs in created:
        print(f"+ {name} | agent_id={agent_id} | docs_processados={docs}")
else:
    print("Nenhum novo agente criado.")

print("\n=== JÁ EXISTIAM (IGNORADOS) ===")
if skipped:
    for brand_name, existing_id, existing_name in skipped:
        print(f"- {brand_name} | já existe: {existing_id} ({existing_name})")
else:
    print("Nenhum ignorado.")

cur.execute("SELECT COUNT(*) FROM agents")
total_agents = cur.fetchone()[0]
print(f"\nTotal de agentes no banco: {total_agents}")

conn.close()
