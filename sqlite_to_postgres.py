#!/usr/bin/env python3
"""
Load data directly from a SQLite .db file into an already-migrated
PostgreSQL database (e.g. created by `python manage.py migrate`).

No dump file, no Navicat, no encoding issues -- reads the SQLite file
directly using Python's built-in sqlite3 module, and matches columns by
NAME against whatever schema Django already created in Postgres, so
Django-defined booleans/dates/etc. all come out correctly typed.

Usage:
    pip install psycopg2-binary --break-system-packages
    python manage.py migrate              # creates correct schema in Postgres
    python manage.py flush --no-input      # optional: clean slate first

    python sqlite_to_postgres.py db.sqlite3 \
        --host localhost --port 5432 --dbname mydb --user myuser --password mypass

    # or preview first without touching Postgres:
    python sqlite_to_postgres.py db.sqlite3 --dry-run
"""

import argparse
import sqlite3
import sys

SKIP_TABLES = {"sqlite_sequence", "sqlite_stat1", "sqlite_stat4"}


def get_sqlite_tables(sconn):
    cur = sconn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [r[0] for r in cur.fetchall() if r[0] not in SKIP_TABLES and not r[0].startswith('sqlite_')]


def get_sqlite_columns(sconn, table):
    cur = sconn.cursor()
    cur.execute(f'PRAGMA table_info("{table}")')
    # row: (cid, name, type, notnull, dflt_value, pk)
    return [row[1] for row in cur.fetchall()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sqlite_file')
    ap.add_argument('--host', default=None)
    ap.add_argument('--port', default=None)
    ap.add_argument('--dbname', default=None)
    ap.add_argument('--user', default=None)
    ap.add_argument('--password', default=None)
    ap.add_argument('--dry-run', action='store_true',
                     help="Preview tables/row counts only, don't touch Postgres")
    args = ap.parse_args()

    sconn = sqlite3.connect(args.sqlite_file)
    tables = get_sqlite_tables(sconn)

    if args.dry_run:
        print(f"SQLite tables found: {len(tables)}")
        total = 0
        for t in tables:
            cols = get_sqlite_columns(sconn, t)
            cur = sconn.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{t}"')
            count = cur.fetchone()[0]
            total += count
            print(f"  {t}: {len(cols)} cols {cols}, {count} rows")
        print(f"\nTotal rows across all tables: {total}")
        sconn.close()
        return

    import psycopg2

    pconn = psycopg2.connect(
        host=args.host, port=args.port, dbname=args.dbname,
        user=args.user, password=args.password,
    )
    pconn.autocommit = False
    pcur = pconn.cursor()

    pg_types_cache = {}

    def get_pg_types(table):
        if table not in pg_types_cache:
            pcur.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s",
                (table,),
            )
            pg_types_cache[table] = dict(pcur.fetchall())
        return pg_types_cache[table]

    total_inserted = 0
    skipped_tables = []

    for table in tables:
        cols = get_sqlite_columns(sconn, table)
        scur = sconn.cursor()
        scur.execute(f'SELECT {", ".join(f"""\"{c}\"""" for c in cols)} FROM "{table}"')
        rows = scur.fetchall()
        if not rows:
            continue

        pg_types = get_pg_types(table)
        if not pg_types:
            print(f"[WARN] Table \"{table}\" not found in target Postgres schema, "
                  f"skipping ({len(rows)} rows not loaded)")
            skipped_tables.append(table)
            continue

        pcur.execute(f'ALTER TABLE "{table}" DISABLE TRIGGER ALL')

        col_list = ', '.join(f'"{c}"' for c in cols)
        placeholders = ', '.join(['%s'] * len(cols))
        insert_sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})'

        inserted_here = 0
        for row in rows:
            converted = []
            for col, val in zip(cols, row):
                target_type = pg_types.get(col)
                if target_type == 'boolean' and val is not None:
                    converted.append(bool(val))
                else:
                    converted.append(val)
            try:
                pcur.execute(insert_sql, converted)
                inserted_here += 1
            except Exception as e:
                pconn.rollback()
                print(f"[ERROR] {table}: failed to insert row {row}: {e}")
                pcur.execute(f'ALTER TABLE "{table}" DISABLE TRIGGER ALL')
                continue

        pcur.execute(f'ALTER TABLE "{table}" ENABLE TRIGGER ALL')
        pconn.commit()
        print(f"[OK] {table}: inserted {inserted_here}/{len(rows)} rows")
        total_inserted += inserted_here

        if 'id' in cols:
            pcur.execute("SELECT pg_get_serial_sequence(%s, 'id')", (f'"{table}"',))
            seq = pcur.fetchone()[0]
            if seq:
                pcur.execute(
                    f'SELECT setval(%s, COALESCE((SELECT MAX(id) FROM "{table}"), 1), '
                    f'(SELECT MAX(id) FROM "{table}") IS NOT NULL)',
                    (seq,),
                )
                pconn.commit()

    pcur.close()
    pconn.close()
    sconn.close()
    print(f"\nDone. Total rows inserted: {total_inserted}")
    if skipped_tables:
        print(f"Tables skipped (not found in Postgres schema): {skipped_tables}")


if __name__ == '__main__':
    main()
