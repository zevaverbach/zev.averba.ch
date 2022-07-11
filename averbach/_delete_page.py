import sys

from application import delete_page


if len(sys.argv) != 2:
    print("please provide a url of a page to delete")
    sys.exit()

url = sys.argv[1]
delete_page(url)
print(f"Okay, deleted the page at '{url}'")
