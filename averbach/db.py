"""
CREATE TABLE content (
	url VARCHAR NOT NULL, 
	page_type VARCHAR NOT NULL,  # but the only valid value is '0.0.1' currently
	title VARCHAR NOT NULL UNIQUE, 
	body VARCHAR NOT NULL UNIQUE, 
    description varchar, 
    date integer NOT NULL, 
	PRIMARY KEY (url)
);
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine as ce
import sqlalchemy

load_dotenv()

DB_PATH = os.getenv("DB_PATH")
CONSTR = os.getenv("DB_CONNECTION_URL")
ENGINE = None


def create_engine():
    global ENGINE
    ENGINE = ENGINE or ce(CONSTR)
    return ENGINE


def do_query(query: str):
    global ENGINE
    ENGINE = ENGINE or create_engine()
    try:
        return [dict(i) for i in ENGINE.execute(query)]
    except sqlalchemy.exc.ResourceClosedError:
        return
