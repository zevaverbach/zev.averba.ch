import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

from dotenv import load_dotenv
from flask import Flask, request, render_template
from jinja2 import Template

from db import do_query, create_engine, push_refreshed_db

load_dotenv()

ENGINE = None
BASE_URL = "https://zev.averba.ch"
FATHOM_UID = "LWJFWQJS"
THEME_COLOR = "#209cee"
DEFAULT_PAGE_TYPE = "0.0.1"
RENDERED_PUBLIC_FILES_PATH = f"/var/www/{BASE_URL.split('/')[-1]}/html"

DEFAULT_CONTENT = {
    "page_type": DEFAULT_PAGE_TYPE,
    "body": "<h1>Zev Averbach</h1>",
    "fathom_uid": FATHOM_UID,
}

app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)
GLOBALS = dict(
    BASE_URL=BASE_URL,
    THEME_COLOR=THEME_COLOR,
    SUPABASE_URL_UID="stewyikkzurffdfhwprj",
    SUPABASE_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlhdCI6MTYzODQzOTYwNSwiZXhwIjoxOTU0MDE1NjA1fQ.1QNNHL8RUSzT1YYWpyEzyeJNCFQwRd5APRT9EXXkmXM",
)


@app.context_processor
def inject_globals():
    return GLOBALS


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
    subprocess.call(
        f"sitemap-generator {BASE_URL} --filepath {os.getenv('SITEMAP_PATH')}", shell=True
    )


@app.route("/create", methods=["POST"])
def create_page():
    payload = request.get_json()
    return handle_create_page(payload)


def handle_create_page(payload: dict):
    global ENGINE
    ENGINE = ENGINE or create_engine()
    if "client_secret" not in payload or payload["client_secret"] != os.getenv("CLIENT_SECRET"):
        return "not allowed", 401

    url = payload["url"]
    if url.count("/") > 1:
        return "only one slash allowed", 401
    page_type = payload.get("page_type") or DEFAULT_PAGE_TYPE
    title = payload["title"]
    body = ""

    for section in payload["sections"]:
        if section["type"] == "paragraph":
            body += f"<p>{section['content']}</p>"
        elif section["type"].startswith("h"):
            h = section["type"]
            body += f"<{h}>{section['content']}</{h}>"

    existing_content = [
        dict(i) for i in ENGINE.execute(f"select * from content where url = ?", (url,))
    ]

    if existing_content:
        if (
            body != existing_content[0]["body"]
            or title != existing_content[0]["title"]
            or page_type != existing_content[0]["page_type"]
        ):
            ENGINE.execute(
                f"update content set title = ?, body = ?, page_type = ? where url = ?",
                (title, body, page_type, url),
            )
            update_everything(url)
        return f"{BASE_URL}/{url}", 200

    ENGINE.execute(
        "insert into content (url, page_type, title, body) values (?, ?, ?, ?)",
        (url, page_type, title, body),
    )
    update_everything(url)
    return f"{BASE_URL}/{url}", 200


def get_all_urls():
    return [i["url"] for i in do_query("select url from content")]


def get_all_titles_and_urls():
    return [(i["title"], i["url"]) for i in do_query("select title, url from content")]


def render_toc():
    titles_and_urls = get_all_titles_and_urls()

    def url_for(name, filename):
        return f"{name}/{filename}"

    with open(f"templates/toc_0.0.1.html") as fin:
        rendered = Template(fin.read()).render(url_for=url_for, titles_and_urls=titles_and_urls, **GLOBALS)
        html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"toc.html"
        try:
            with html_file.open() as fin:
                if fin.read() == rendered:
                    print(f"no change for url {url}")
                    return
                with html_file.open("w") as fout:
                    fout.write(rendered)
        except FileNotFoundError:
            with html_file.open("w") as fout:
                fout.write(rendered)


def render_all_updated_pages(url=None):
    def url_for(name, filename):
        num_slashes = url.count("/")
        dots = ""
        if num_slashes:
            dots = "../" * num_slashes
        return f"{dots}{name}/{filename}"

    urls = [url] if url else get_all_urls()

    for url in urls:
        content = get_content(url)
        with open(f"templates/page_{content['page_type']}.html") as fin:
            rendered = Template(fin.read()).render(url_for=url_for, **content, **GLOBALS)
            html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"{url}.html"
            try:
                with html_file.open() as fin:
                    if fin.read() == rendered:
                        print(f"no change for url {url}")
                        continue
                    with html_file.open("w") as fout:
                        fout.write(rendered)
            except FileNotFoundError:
                try:
                    with html_file.open("w") as fout:
                        fout.write(rendered)
                except FileNotFoundError:
                    html_file.parent.mkdir(parents=True)
                    with html_file.open("w") as fout:
                        fout.write(rendered)


def update_static_files():
    for f in Path("static").iterdir():
        if f.name == "robots.txt":
            public_path = Path(RENDERED_PUBLIC_FILES_PATH) / f.name
        else:
            public_path = Path(RENDERED_PUBLIC_FILES_PATH) / "static" / f.name
        try:
            with f.open() as fin, public_path.open() as public_fin:
                if fin.read() != public_fin.read():
                    print(f"{f} has changed, copying to public folder.")
                    shutil.copy(f, public_path)
        except UnicodeDecodeError:
            with f.open("rb") as fin, public_path.open("rb") as public_fin:
                if fin.read() != public_fin.read():
                    print(f"{f} has changed, copying to public folder.")
                    shutil.copy(f, public_path)
        except FileNotFoundError:
            print(f"{f} doesn't exist in public fodler, copying it there.")
            shutil.copy(f, public_path)


def update_everything(url=None):
    render_all_updated_pages(url=url)
    render_toc()
    update_sitemap()
    update_static_files()
    push_refreshed_db()


class NoContent(Exception):
    pass
