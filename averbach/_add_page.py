import sys

from application import create_page

VALID_ARGS = "body", "url", "title", "date", "page_type", "description"


args = {}
if len(sys.argv) < 4:
    print("please provide some arguments")
    print("they must include --url, --title, and --body")
    print("they can also include --page-type, --description, and --date")
    sys.exit()

for arg in sys.argv[1:]:
    if "=" not in arg:
        print("please provide args in --arg_name=value format")
        sys.exit()
    key_with_prepended_hyphens, value = arg.split("=")
    key = key_with_prepended_hyphens.replace("--", "")
    if key not in VALID_ARGS:
        print(f"{key} isn't valid, these are: {VALID_ARGS}")
        sys.exit()
    args[key] = value

if "url" not in args:
    print("please provide a url")
    sys.exit()
if "title" not in args:
    print("please provide a title")
    sys.exit()
if "body" not in args:
    print("please provide a body")
    sys.exit()
if "EQUALS" in args["body"]:
    args["body"] = args["body"].replace("EQUALS", "=")

try:
    create_page(**args)
except Exception as e:
    print(f"there was an error: {e}")
    sys.exit()
else:
    print("okay, added the page!")
