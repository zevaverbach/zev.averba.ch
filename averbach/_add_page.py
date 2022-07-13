import pathlib as pl
import sys

from application import create_page, update_pages

VALID_ARGS = "body", "url", "title", "date", "page_type", "description", "path"
VALID_ARGS_WITH_HYPHENS = [f"--{va}" for va in VALID_ARGS]


args = {}
if len(sys.argv) < 4:
    print("please provide some arguments")
    print("they must include --url, --title, and either --body or --path")
    print("they can also include --page-type, --date, and --description")
    sys.exit()

for arg in sys.argv[1:]:
    if "=" not in arg:
        print("please provide args in --arg_name=value format")
        sys.exit()
    key_with_prepended_hyphens, value = arg.split("=")
    key = key_with_prepended_hyphens.replace("--", "")
    if key not in VALID_ARGS:
        print(f"{key} isn't valid, these are: {VALID_ARGS_WITH_HYPHENS}")
        sys.exit()
    args[key] = value

if "url" not in args:
    print("please provide a url")
    sys.exit()
if "title" not in args:
    print("please provide a title")
    sys.exit()
if "body" not in args and "path" not in args:
    print("please provide a body or a path")
    sys.exit()
if "body" in args and "EQUALS" in args["body"]:
    args["body"] = args["body"].replace("EQUALS", "=")
if "path" in args:
    path = args["path"]
    del args["path"]
    args["body"] = pl.Path(path).read_text().replace("\n", "&#10;").replace("'", "&apos;")

args["title"] = args["title"].title()

try:
    create_page(**args)
except Exception as e:
    print(f"there was an error: {e}")
    sys.exit()
else:
    title = args["title"]
    print(f"okay, added the page '{title}'!")
    update_pages()
