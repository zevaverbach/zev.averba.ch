import pathlib as pl
import sys

from application import update_pages
from db import do_query, TABLE_NAME


if len(sys.argv) < 3:
    print("please provide --url, --path or --body, and optionally --description and/or --title")
    sys.exit()

for arg in sys.argv[1:]:
    if "=" not in arg:
        print("please provide args in --arg_name=value format")
        sys.exit()
    key_with_prepended_hyphens, value = arg.split("=")
    key = key_with_prepended_hyphens.replace("--", "")
    if key not in ("path", "url", "body", "title", "description"):
        print(f"{key} isn't valid, these are: --path, --url")
        sys.exit()
    args[key] = value

url = args["url"]
path = None
body = None
description = None
if "path" in args:
    path = args["path"]
else:
    body = args["body"]

if not do_query(f"select url from {TABLE_NAME} where url = '{url}'"):
    print("no such url")
    sys.exit()

if path:
    body = pl.Path(path).read_text()

# TODO: escape stuff!
do_query(f"update {TABLE_NAME} set body = '{body}' where url = '{url}'")
print(f"okay, updated body of {url}")

if args["title"]:
    do_query(f"update {TABLE_NAME} set title = '{args[\"title\"]}' where url = '{url}'")
    print(f"okay, updated title of {url}")

if args["description"]:
    do_query(f"update {TABLE_NAME} set description = '{args[\"description\"]}' where url = '{url}'")
    print(f"okay, updated description of {url}")

update_pages()
