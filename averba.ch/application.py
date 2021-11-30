import logging
import sys

from dotenv import load_dotenv
from flask import Flask, request, render_template

from db import do_query, create_engine, push_refreshed_db

load_dotenv()

ENGINE = None
BASE_URL = "https://zev.averba.ch"
FATHOM_UID = "LWJFWQJS"
THEME_COLOR = "#209cee"
DEFAULT_PAGE_TYPE = "0.0.1"

DEFAULT_CONTENT = {
    "page_type": DEFAULT_PAGE_TYPE,
    "body": "<h1>Zev Averbach</h1>",
    "fathom_uid": FATHOM_UID,
}

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)


@app.context_processor
def inject_globals():
    return dict(BASE_URL=BASE_URL, THEME_COLOR=THEME_COLOR)


@app.route("/favicon.ico")
def favicon():
    FAVICON_PATH = "static/favicon.ico"
    return app.send_static_file(FAVICON_PATH)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def page(path):
    """
    Supports arbitrary numbers of slashes!
    """
    if not path or path == "/":
        content = DEFAULT_CONTENT
    else:
        try:
            content = get_content(path)
        except NoContent:
            return "no content!", 400

    return render_template(f"page_{content['page_type']}.html", **content)


def get_content(url):
    global ENGINE
    ENGINE = ENGINE or create_engine()
    result = ENGINE.execute(f"select * from content where url = '{url}'")
    if not result.returns_rows:
        raise NoContent
    return [{**dict(r), **{"fathom_uid": FATHOM_UID}} for r in result][0]


def update_sitemap():
    # TODO: implement this using sitemap-generator-cli, and upload to Google
    pass


@app.route("/create", methods=["POST"])
def create_page():
    global ENGINE
    ENGINE = ENGINE or create_engine()
    payload = request.get_json()

    url = payload["url"]
    page_type = payload.get("page_type") or DEFAULT_PAGE_TYPE
    title = payload["title"]
    body = ""

    for section in payload["sections"]:
        if section["type"] == "paragraph":
            body += f"<p>{section['content']}</p>"
        elif section["type"].startswith("h"):
            h = section["type"]
            body += f"<{h}>{section['content']}</{h}>"

    existing_content = do_query(f"select * from content where url = '{url}'")

    if existing_content:
        if (
            body != existing_content[0]["body"]
            and title != existing_content[0]["title"]
            and page_type != existing_content[0]["page_type"]
        ):
            do_query(
                f"update content set title = '{title}', body = '{body}', "
                f"page_type = '{page_type}' where url = '{url}'"
            )
            update_sitemap()
            push_refreshed_db()
        return f"{BASE_URL}/{url}", 200

    ENGINE.execute(
        "insert into content (url, page_type, title, body) values (?, ?, ?, ?)", 
        (url, page_type, title, body),
    )
    update_sitemap()
    push_refreshed_db()
    return f"{BASE_URL}/{url}", 200


class NoContent(Exception):
    pass
