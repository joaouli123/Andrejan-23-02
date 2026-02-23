"""Rename brand LG Otis -> Otis, rename Qdrant collection, fix file paths."""
import sqlite3, os
from qdrant_client import QdrantClient

DB = "/app/data/andreja.db"

c = sqlite3.connect(DB)
cur = c.cursor()

# 1. Check if there's already a brand with slug "otis"
cur.execute("SELECT id, name, slug FROM brands WHERE slug='otis'")
existing_otis = cur.fetchone()

cur.execute("SELECT id, name, slug FROM brands WHERE slug='lg'")
lg_brand = cur.fetchone()

print(f"Existing 'otis' brand: {existing_otis}")
print(f"Existing 'lg' brand: {lg_brand}")

if existing_otis and lg_brand:
    # There's already an "Otis" brand (id=1) and "LG Otis" (id=8, slug=lg)
    # Move docs from brand 8 to brand 1
    lg_id = lg_brand[0]
    otis_id = existing_otis[0]
    
    cur.execute("UPDATE documents SET brand_id=? WHERE brand_id=?", (otis_id, lg_id))
    print(f"Moved {cur.rowcount} docs from brand {lg_id} to brand {otis_id}")
    
    # Update filename paths from lg/ to otis/
    cur.execute("SELECT id, filename FROM documents WHERE filename LIKE 'lg/%'")
    for row in cur.fetchall():
        new_name = row[1].replace("lg/", "otis/", 1)
        cur.execute("UPDATE documents SET filename=? WHERE id=?", (new_name, row[0]))
        print(f"  Renamed: {row[1]} -> {new_name}")
    
    # Rename upload dir
    old_dir = "/app/data/uploads/lg"
    new_dir = "/app/data/uploads/otis"
    if os.path.exists(old_dir):
        if not os.path.exists(new_dir):
            os.makedirs(new_dir, exist_ok=True)
        for f in os.listdir(old_dir):
            os.rename(os.path.join(old_dir, f), os.path.join(new_dir, f))
            print(f"  Moved file: {f}")
    
    # Delete the old LG Otis brand (now has no docs)
    cur.execute("DELETE FROM brands WHERE id=?", (lg_id,))
    print(f"Deleted brand {lg_id} (LG Otis)")

elif lg_brand and not existing_otis:
    # Just rename the brand
    cur.execute("UPDATE brands SET name='Otis', slug='otis' WHERE slug='lg'")
    print(f"Renamed brand to Otis/otis")

c.commit()

# 2. Rename Qdrant collection brand_lg -> brand_otis
qc = QdrantClient(host="qdrant", port=6333)
collections = [col.name for col in qc.get_collections().collections]
print(f"\nQdrant collections: {collections}")

if "brand_lg" in collections and "brand_otis" not in collections:
    # Get info from old collection
    info = qc.get_collection("brand_lg")
    print(f"brand_lg has {info.points_count} points")
    
    # Create new collection with same config
    from qdrant_client.models import VectorParams, Distance
    qc.create_collection(
        collection_name="brand_otis",
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )
    
    # Copy all points
    offset = None
    total = 0
    while True:
        results = qc.scroll(
            collection_name="brand_lg",
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        points, next_offset = results
        if not points:
            break
        
        from qdrant_client.models import PointStruct
        qc.upsert(
            collection_name="brand_otis",
            points=[
                PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                for p in points
            ],
        )
        total += len(points)
        offset = next_offset
        if next_offset is None:
            break
    
    print(f"Copied {total} points to brand_otis")
    
    # Delete old collection
    qc.delete_collection("brand_lg")
    print("Deleted brand_lg collection")

elif "brand_lg" in collections and "brand_otis" in collections:
    # Merge: copy brand_lg into brand_otis
    offset = None
    total = 0
    while True:
        results = qc.scroll(
            collection_name="brand_lg",
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        points, next_offset = results
        if not points:
            break
        from qdrant_client.models import PointStruct
        qc.upsert(
            collection_name="brand_otis",
            points=[
                PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                for p in points
            ],
        )
        total += len(points)
        offset = next_offset
        if next_offset is None:
            break
    print(f"Merged {total} points from brand_lg into brand_otis")
    qc.delete_collection("brand_lg")
    print("Deleted brand_lg")

# 3. Verify
c2 = sqlite3.connect(DB)
cur2 = c2.cursor()
cur2.execute("SELECT id, name, slug FROM brands ORDER BY id")
print("\nFinal brands:")
for r in cur2.fetchall():
    print(f"  {r}")
cur2.execute("SELECT id, brand_id, filename, file_size, status FROM documents")
print("\nFinal docs:")
for r in cur2.fetchall():
    print(f"  {r}")

cols = [col.name for col in qc.get_collections().collections]
print(f"\nFinal Qdrant collections: {cols}")
for cn in cols:
    info = qc.get_collection(cn)
    print(f"  {cn}: {info.points_count} points")

c2.close()
print("\nDone!")
