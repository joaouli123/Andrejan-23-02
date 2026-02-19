import sqlite3

conn = sqlite3.connect('/app/data/andreja.db')
cur = conn.cursor()
cur.execute(
    """
    UPDATE documents
    SET status='error',
        error_message='forcando reprocessamento',
        completed_at=CURRENT_TIMESTAMP
    WHERE id=2 AND status='processing'
    """
)
conn.commit()
print(cur.rowcount)
conn.close()
