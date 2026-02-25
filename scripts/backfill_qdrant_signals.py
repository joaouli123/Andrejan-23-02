import os
import sys
from typing import Any

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from ingestion.embedder import get_qdrant_client, _extract_domain_signals  # type: ignore


def _iter_brand_collections(client):
    collections = client.get_collections().collections
    for collection in collections:
        name = collection.name
        if name.startswith('brand_'):
            yield name


def _needs_update(payload: dict[str, Any]) -> bool:
    signals = payload.get('signals')
    if not isinstance(signals, dict):
        return True
    return not any(signals.get(key) for key in ('topics', 'controller_tokens', 'fault_tokens'))


def main():
    client = get_qdrant_client()
    total_seen = 0
    total_updated = 0

    for collection_name in _iter_brand_collections(client):
        print(f'\n== Collection: {collection_name} ==')
        next_offset = None
        collection_seen = 0
        collection_updated = 0

        while True:
            points, next_offset = client.scroll(
                collection_name=collection_name,
                limit=200,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )

            if not points:
                break

            update_ops = []
            for point in points:
                payload = point.payload or {}
                text = str(payload.get('text') or '').strip()
                if not text:
                    continue

                collection_seen += 1
                if not _needs_update(payload):
                    continue

                signals = _extract_domain_signals(text)
                new_payload = dict(payload)
                new_payload['signals'] = signals
                update_ops.append((point.id, new_payload))

            for point_id, new_payload in update_ops:
                client.set_payload(
                    collection_name=collection_name,
                    payload=new_payload,
                    points=[point_id],
                )
                collection_updated += 1

            if not next_offset:
                break

        total_seen += collection_seen
        total_updated += collection_updated
        print(f'Points lidos: {collection_seen}')
        print(f'Points atualizados com signals: {collection_updated}')

    print('\n==== BACKFILL FINALIZADO ====')
    print(f'Total de points lidos: {total_seen}')
    print(f'Total de points atualizados: {total_updated}')


if __name__ == '__main__':
    main()
