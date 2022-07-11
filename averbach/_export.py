import pathlib as pl
import sys

from application import TABLE_NAME
from db import do_query


try:
    url = sys.argv[1]
except IndexError:
    print("please provide a URL")
    sys.exit()

if not do_query(f"select url from {TABLE_NAME} where url = '{url}'"):
    print("no such url")
    sys.exit()

body = do_query(f"select body from {TABLE_NAME} where url = '{url}'")[0]["body"]
with open(f"{url}.html", "w") as fout:
    fout.write(body.replace("&#10;", "\n"))
