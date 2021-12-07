from functools import partial
import logging
import os
from pathlib import Path
import shutil
import subprocess

from dotenv import load_dotenv
from flask import Flask, request, render_template
from jinja2 import Environment, FileSystemLoader

from db import do_query, create_engine

load_dotenv()

ENGINE = None
BASE_URL = "https://zev.averba.ch"
FATHOM_UID = "LWJFWQJS"
THEME_COLOR = "#209cee"
RENDERED_PUBLIC_FILES_PATH = f"/var/www/{BASE_URL.split('/')[-1]}/html"
TABLE_NAME = "content"

app = Flask(__name__)

gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

GLOBALS = dict(
    BASE_URL=BASE_URL,
    THEME_COLOR=THEME_COLOR,
    SUPABASE_URL_UID="stewyikkzurffdfhwprj",
    SUPABASE_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlhdCI6MTYzODQzOTYwNSwiZXhwIjoxOTU0MDE1NjA1fQ.1QNNHL8RUSzT1YYWpyEzyeJNCFQwRd5APRT9EXXkmXM",
    fathom_uid=FATHOM_UID,
    TABLE_NAME=TABLE_NAME,
)


@app.context_processor
def inject_globals():
    return GLOBALS


def authorize(auth_header):
    return auth_header.replace("Bearer", "").strip() == os.getenv("AUTH_TOKEN")


@app.route("/favicon.ico")
def favicon():
    FAVICON_PATH = "static/favicon.ico"
    return app.send_static_file(FAVICON_PATH)


def get_content(url):
    global ENGINE
    ENGINE = ENGINE or create_engine()
    result = ENGINE.execute(f"select * from {TABLE_NAME} where url = '{url}'")
    if not result or not result.returns_rows:
        raise NoContent
    return [dict(r) for r in result][0]


def update_sitemap():
    subprocess.call(
        f"sitemap-generator {BASE_URL} --filepath {os.getenv('SITEMAP_PATH')}", shell=True
    )


@app.route("/create_page", methods=["POST"])
def create():
    if not authorize(request.headers.get("Authorization")):
        return "no", 400
    payload = request.get_json()
    content = payload["record"]
    render_page(content=content)
    render_toc()
    update_sitemap()
    return "ok", 200


@app.route("/delete_page", methods=["POST"])
def delete():
    if not authorize(request.headers.get("Authorization")):
        return "no", 400
    payload = request.get_json()
    url = payload["old_record"]["url"]
    delete_page(url)
    render_toc()
    update_sitemap()
    return "ok", 200


def delete_page(url):
    html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"{url}.html"
    html_file.unlink()


@app.route("/update_page", methods=["POST"])
def update():
    if not authorize(request.headers.get("Authorization")):
        return "no", 400
    payload = request.get_json()
    content, old_record = payload["record"], payload["old_record"]
    old_url = None if content["url"] == old_record["url"] else old_record["url"]
    render_page(content=content, old_url=old_url)
    render_toc()
    update_sitemap()
    return "ok", 200


def get_all_urls():
    return [i["url"] for i in do_query(f"select url from {TABLE_NAME}")]


def render_toc():
    all_pages = do_query(f"select url, title, description, body from {TABLE_NAME}")

    def url_for(name, filename):
        return f"{name}/{filename}"

    with open(f"templates/toc_0.0.1.html") as fin:
        template_str = fin.read()
    template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
    print(all_pages)
    rendered = template.render(
        url_for=url_for,
        all_pages=all_pages,
        **GLOBALS,
    )
    html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"toc.html"
    if html_file.exists():
        with html_file.open() as fin:
            if fin.read() == rendered:
                print(f"no change for toc")
                return
    with html_file.open("w") as fout:
        fout.write(rendered)


def render_page(content, old_url=None):
    url = content["url"]

    def url_for(name, filename):
        num_slashes = url.count("/")
        dots = ""
        if num_slashes:
            dots = "../" * num_slashes
        return f"{dots}{name}/{filename}"

    html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"{url}.html"
    if old_url:
        old_html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"{old_url}.html"
        gunicorn_logger.info(f"deleting {old_html_file}")
        old_html_file.unlink()

    with open(f"templates/page_{content['page_type']}.html") as fin:
        template_str = fin.read()
        template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
        rendered = template.render(url_for=url_for, **content, **GLOBALS)
    try:
        with html_file.open() as fin:
            if fin.read() == rendered:
                print(f"no change for url {url}")
                return
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


def render_all_updated_pages():
    def url_for(name, filename):
        return f"../{name}/{filename}"

    for url in get_all_urls():
        content = get_content(url)
        with open(f"templates/page_{content['page_type']}.html") as fin:
            template_str = fin.read()
        template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
        rendered = template.render(url_for=url_for, **content, **GLOBALS)
        html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"{url}.html"
        if html_file.exists():
            with html_file.open() as fin:
                if fin.read() == rendered:
                    print(f"no change for url {url}")
                    continue
        if not html_file.parent.exists():
            html_file.parent.mkdir(parents=True)
        with html_file.open("w") as fout:
            fout.write(rendered)


def update_static_files():
    updated = False
    for f in Path("static").iterdir():
        if f.name == "robots.txt":
            public_path = Path(RENDERED_PUBLIC_FILES_PATH) / f.name
        else:
            public_path = Path(RENDERED_PUBLIC_FILES_PATH) / "static" / f.name
        try:
            with f.open() as fin, public_path.open() as public_fin:
                if fin.read() != public_fin.read():
                    updated = True
                    print(f"{f} has changed, copying to public folder.")
                    shutil.copy(f, public_path)
        except UnicodeDecodeError:
            with f.open("rb") as fin, public_path.open("rb") as public_fin:
                if fin.read() != public_fin.read():
                    updated = True
                    print(f"{f} has changed, copying to public folder.")
                    shutil.copy(f, public_path)
        except FileNotFoundError:
            print(f"{f} doesn't exist in public folder, copying it there.")
            updated = True
            shutil.copy(f, public_path)
    return updated


def update_everything():
    updated = update_static_files()
    render_all_updated_pages()
    render_toc()
    update_sitemap()


class NoContent(Exception):
    pass
