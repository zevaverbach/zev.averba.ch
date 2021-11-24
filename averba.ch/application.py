import logging
import sys
from uuid import uuid4

from dotenv import load_dotenv
from flask import Flask, request, render_template

from db import do_query, create_engine, push_refreshed_db

load_dotenv()

ENGINE = None
PAGE_VERSION = "0.0.1"
URL = "https://zev.averba.ch"
DEFAULT_CONTENT = {
    "page_version": PAGE_VERSION,
    "body": "<h1>Zev Averbach</h1>",
    "fathom_uid": "LWJFWQJS",
}

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)


@app.context_processor
def inject_globals():
    return dict(SITE_URL=URL)


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

    return render_template(f"page_{content['page_version']}.html", **content)


def get_content(uid):
    global ENGINE
    ENGINE = ENGINE or create_engine()
    result = ENGINE.execute(f"select * from content where uid = '{uid}'")
    if not result.returns_rows:
        raise NoContent
    return [{**dict(r), **{"fathom_uid": "LWJFWQJS"}} for r in result][0]


@app.route("/create", methods=["POST"])
def create_page():
    global ENGINE
    ENGINE = ENGINE or create_engine()
    payload = request.get_json()
    heading = ""
    if "heading" in payload and "body" in payload:
        heading, body = payload["heading"], payload["body"]
    elif "heading" in payload and "paragraphs" in payload:
        heading, paragraphs = payload["heading"], payload["paragraphs"]
        body = "".join([f"<p>{paragraph}</p>" for paragraph in paragraphs])
    elif "sections" in payload:
        sections = payload["sections"]
        body = ""
        for section in sections:
            if section["type"] == "paragraph":
                body += f"<p>{section['content']}</p>"
            elif section["type"].startswith("h"):
                h = section["type"]
                body += f"<{h}>{section['content']}</{h}>"
    else:
        return "bad args", 400

    # TODO: is this necessary?
    escaped_body = body.replace("'", "&#39;")
    uid = None
    if "uid" in payload:
        uid = payload["uid"]
        existing_content = do_query(f"select * from content where uid = '{uid}'")
        if existing_content:
            if (
                body != existing_content[0]["body"]
                and heading != existing_content[0]["heading"]
                and PAGE_VERSION != existing_content[0]["page_version"]
            ):
                do_query(
                    f"update content set heading = '{heading}', body = '{body}', "
                    f"page_version = '{PAGE_VERSION}' where uid = '{uid}'"
                )
                push_refreshed_db()
            return f"{URL}/{uid}", 200

    uid = uid or uuid4()
    ENGINE.execute(
        f"insert into content (uid, page_version, heading, body) "
        f"values ('{uid}', '{PAGE_VERSION}', '{heading}', '{escaped_body}')"
    )
    push_refreshed_db()
    return f"{URL}/{uid}", 200


class NoContent(Exception):
    pass
