import sqlite3

conn = sqlite3.connect('/app/data/andreja.db')
cur = conn.cursor()
cur.execute(
    """
    UPDATE documents
    SET status='error',
        error_message='Processamento interrompido apos restart do backend',
        completed_at=CURRENT_TIMESTAMP
    WHERE id=1 AND status='processing'
    """
)
conn.commit()
print(cur.rowcount)
conn.close()
