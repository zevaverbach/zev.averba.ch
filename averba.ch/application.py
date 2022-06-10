"""
the page model:
    url VARCHAR NOT NULL, 
    page_type VARCHAR, 
    title VARCHAR, 
    description VARCHAR,
    date INTEGER,
    body VARCHAR, 
    PRIMARY KEY (url)
"""
from importlib import import_module
import logging
import os
from pathlib import Path
import shutil
import subprocess

from dotenv import load_dotenv
from flask import Flask, request, render_template
from jinja2 import Environment, FileSystemLoader
from rich import pretty

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


def get_all_pages():
    return do_query(f"select * from {TABLE_NAME}")


def render_toc():
    all_pages = do_query(f"select url, title, description, date from {TABLE_NAME}")

    def url_for(name, filename):
        return f"{name}/{filename}"

    with open(f"templates/toc_0.0.1.html") as fin:
        template_str = fin.read()
    template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
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
    if html_file.exists():
        if html_file.read_text() == rendered:
            print(f"no change for url {url}")
            return
    if not html_file.parent.exists():
        html_file.parent.mkdir(parents=True)
    with html_file.open("w") as fout:
        fout.write(rendered)


def render_all_updated_pages():
    with open(f"templates/page_0.0.1.html") as fin:
        template_str = fin.read()
    template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
    all_pages = get_all_pages()
    for page in all_pages:
        pretty.pprint(page["body"])
        rendered = template.render(**page, **GLOBALS)
        html_file = Path(RENDERED_PUBLIC_FILES_PATH) / (page["url"] + ".html")
        print(html_file)
        if not html_file.exists():
            if "/" in page["url"]:
                html_file.parent.mkdir(parents=True, exist_ok=True)
            with html_file.open("w") as fout:
                print(f"creating {page['url']} for the first time ({html_file})")
                fout.write(rendered)
                continue
        with html_file.open() as fin:
            if fin.read() == rendered:
                print(f"no change for {page['url']} ({html_file})")
                continue
            else:
                with html_file.open("w") as fout:
                    print(f"rewriting {page['url']} ({html_file})")
                    fout.write(rendered)
                    continue


def remove_all_pages_which_arent_in_db() -> None:
    all_pages = get_all_pages()
    urls = [p["url"] for p in all_pages]
    root_directory = Path(RENDERED_PUBLIC_FILES_PATH)
    for path_object in root_directory.glob("**/*"):
        if path_object.is_file():
            subpath = str(path_object).replace(f"{RENDERED_PUBLIC_FILES_PATH}/", "")
            if subpath.startswith("static") or any(
                subpath.endswith(i) for i in ("robots.txt", "toc.html")
            ):
                continue
            if subpath.replace(".html", "") not in urls:
                path_object.unlink()
                print(f"removed {path_object} because it's not in DB")


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
    remove_all_pages_which_arent_in_db()
    render_toc()
    update_sitemap()


class NoContent(Exception):
    pass
