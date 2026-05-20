"""Reset A001 and A002 to preprocessed state for re-processing."""
import sqlite3

conn = sqlite3.connect("data/project.sqlite")
codes = ("A001", "A002")

for code in codes:
    # Get doc id
    row = conn.execute("SELECT id FROM documents WHERE document_code=?", (code,)).fetchone()
    if not row:
        print(f"  {code} not found, skipping")
        continue
    doc_id = row[0]

    conn.execute("UPDATE documents SET status='preprocessed', current_step=NULL WHERE id=?", (doc_id,))
    conn.execute("DELETE FROM scenarios WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM outcomes WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM article_classification WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM ai_runs WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM evidence WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM qa_log WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM building_cases WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM spaces WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM intervention_components WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM meta_readiness WHERE document_id=?", (doc_id,))
    conn.execute("DELETE FROM digitization_tasks WHERE document_id=?", (doc_id,))
    print(f"  {code} reset to preprocessed")

conn.commit()
conn.close()
print("Done.")
