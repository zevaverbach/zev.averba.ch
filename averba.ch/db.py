import os
from pathlib import Path
import sqlite3
import subprocess as sp

from dotenv import load_dotenv
from sqlalchemy import create_engine as ce, Table, Column, String, MetaData
import sqlalchemy

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
CONSTR = os.getenv("DB_CONNECTION_STRING")
ENGINE = None


def create_engine():
    global ENGINE
    ENGINE = ENGINE or ce(CONSTR)
    return ENGINE


md = MetaData()
Content = Table(
    "content",
    md,
    Column("url", String, primary_key=True),
    Column("page_type", String),
    Column("title", String),
    Column("body", String),
)


def do_query(query: str):
    global ENGINE
    ENGINE = ENGINE or create_engine()
    try:
        return [dict(i) for i in ENGINE.execute(query)]
    except sqlalchemy.exc.ResourceClosedError:
        return


def create_tables():
    global ENGINE
    ENGINE = ENGINE or ce(CONSTR)
    md.create_all(ENGINE)


def drop_tables():
    global ENGINE
    ENGINE = ENGINE or ce(CONSTR)
    md.drop_all(ENGINE)


def _reset():
    drop_tables()
    create_tables()


def _init():
    if Path(DB_PATH).exists:
        Path(DB_PATH).unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.close()
    create_tables()


def push_refreshed_db():
    sp.check_output(f"git add {DB_PATH}", shell=True)
    sp.check_output("git commit -m 'update db'", shell=True)
