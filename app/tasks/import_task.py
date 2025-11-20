import logging
from pathlib import Path

from app.tasks.celery_app import celery
from app.database import engine

logger = logging.getLogger(__name__)


@celery.task(bind=True, name="app.tasks.import_task.import_csv_task", autoretry_for=(), retry_backoff=True, retry_kwargs={'max_retries': 3})
def import_csv_task(self, path: str):
    try:
        self.update_state(state="STARTED", meta={"stage": "parsing", "message": "Parsing CSV / copying to temporary table"})
    except Exception:
        logger.exception("Could not set STARTED state")

    pathp = Path(path)
    if not pathp.exists():
        msg = f"CSV file not found: {path}"
        logger.error(msg)
        try:
            self.update_state(state="FAILURE", meta={"stage": "error", "exc_type": "FileNotFoundError", "exc": msg})
        except Exception:
            logger.exception("Could not set FAILURE meta for missing file")
        raise FileNotFoundError(msg)

    # Ensure PostgreSQL for this fast path
    try:
        dialect_name = engine.dialect.name
    except Exception:
        dialect_name = None

    if dialect_name != "postgresql":
        msg = "Fast COPY import requires PostgreSQL. Fallback import for other DBs is not implemented."
        logger.error(msg)
        try:
            self.update_state(state="FAILURE", meta={"stage": "error", "exc_type": "RuntimeError", "exc": msg})
        except Exception:
            logger.exception("Could not set FAILURE meta")
        raise RuntimeError(msg)

    raw_conn = None
    cur = None
    created = 0
    updated = 0
    total_rows = 0

    try:
        raw_conn = engine.raw_connection()
        cur = raw_conn.cursor()

        # create temp table
        cur.execute("""
            CREATE TEMP TABLE tmp_products (
                name TEXT,
                sku TEXT,
                description TEXT
            ) ON COMMIT DROP;
        """)

        # COPY CSV into temp table, detect header
        with open(pathp, "r", encoding="utf-8") as fh:
            copy_sql = """
                COPY tmp_products(name, sku, description)
                FROM STDIN
                WITH (FORMAT csv, HEADER true)
            """
            cur.copy_expert(copy_sql, fh)

        # Count total rows in tmp table
        cur.execute("SELECT count(*) FROM tmp_products;")
        total_rows = cur.fetchone()[0] or 0

        try:
            self.update_state(state="PROGRESS", meta={"stage": "parsed", "message": "File parsed", "total": total_rows})
        except Exception:
            logger.exception("Failed to update state: parsed")

        if total_rows == 0:
            raw_conn.commit()
            result = {"created": 0, "updated": 0, "total": 0}
            try:
                self.update_state(state="SUCCESS", meta=result)
            except Exception:
                logger.exception("Failed to set SUCCESS meta for empty file")
            return result

        # 1) Update existing products (case-insensitive)
        try:
            self.update_state(state="PROGRESS", meta={"stage": "updating", "message": "Updating existing products", "total": total_rows})
        except Exception:
            logger.exception("Failed to update state: updating")

        update_sql = """
            WITH up AS (
                UPDATE products p
                SET name = t.name,
                    description = t.description,
                    sku = t.sku
                FROM tmp_products t
                WHERE lower(p.sku) = lower(t.sku)
                RETURNING p.id
            )
            SELECT count(*) FROM up;
        """
        cur.execute(update_sql)
        updated = cur.fetchone()[0] or 0

        try:
            percent_after_update = int((updated / total_rows) * 100) if total_rows else 0
            self.update_state(state="PROGRESS", meta={
                "stage": "updating",
                "message": "Updated existing products",
                "total": total_rows,
                "updated": updated,
                "percentage": percent_after_update
            })
        except Exception:
            logger.exception("Failed to update state after update stage")

        # 2) Insert new rows — deduplicate tmp_products by lower(sku) to avoid multiple inserts for same SKU
        try:
            self.update_state(state="PROGRESS", meta={"stage": "inserting", "message": "Inserting new products (deduped)", "total": total_rows, "updated": updated})
        except Exception:
            logger.exception("Failed to update state: inserting")

        # Deduped subquery: pick one row per lower(sku). DISTINCT ON chooses the first row for each lower(sku).
        # Ordering determines which duplicate is kept; here we use ORDER BY lower(sku) (keeps first encountered).
        insert_sql = """
            INSERT INTO products (sku, name, description)
            SELECT q.sku, q.name, q.description
            FROM (
                SELECT DISTINCT ON (lower(sku)) sku, name, description
                FROM tmp_products
                ORDER BY lower(sku)
            ) q
            WHERE NOT EXISTS (
                SELECT 1 FROM products p WHERE lower(p.sku) = lower(q.sku)
            )
            RETURNING id;
        """

        # Execute insert — since we deduped by lower(sku) inside the subquery, UNIQUE violations should not occur
        cur.execute(insert_sql)
        inserted_rows = cur.fetchall() or []
        created = len(inserted_rows)

        processed_total = updated + created
        final_percent = int((processed_total / total_rows) * 100) if total_rows else 100

        raw_conn.commit()

        result = {"created": created, "updated": updated, "total": total_rows}
        try:
            self.update_state(state="SUCCESS", meta={**result, "percentage": final_percent})
        except Exception:
            logger.exception("Failed to set SUCCESS meta")

        return result

    except Exception as exc:
        logger.exception("Import via COPY failed: %s", exc)
        try:
            if raw_conn is not None:
                raw_conn.rollback()
        except Exception:
            logger.exception("Failed to rollback connection after exception")

        exc_type = type(exc).__name__
        exc_message = str(exc)
        try:
            self.update_state(state="FAILURE", meta={"stage": "error", "exc_type": exc_type, "exc": exc_message})
        except Exception:
            logger.exception("Could not set FAILURE meta")

        raise

    finally:
        try:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass
        except Exception:
            logger.exception("Error closing cursor")

        try:
            if raw_conn is not None:
                try:
                    raw_conn.close()
                except Exception:
                    pass
        except Exception:
            logger.exception("Error closing raw connection")