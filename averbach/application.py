"""
the page model:
    url VARCHAR NOT NULL, 
    page_type VARCHAR NOT NULL, 
    title VARCHAR NOT NULL UNIQUE, 
    description VARCHAR,
    date INTEGER,
    body VARCHAR NOT NULL, 
    PRIMARY KEY (url)
"""
import logging
import os
from pathlib import Path
import shutil
from socket import gethostname
import subprocess

from dotenv import load_dotenv
from flask import Flask, request
from jinja2 import Environment, FileSystemLoader
from rich import pretty

from db import do_query

load_dotenv()

TABLE_NAME = "content"
PAGE_TYPE_DEFAULT = "0.0.1"
ENGINE = None
BASE_URL = "https://zev.averba.ch"
FATHOM_UID = "LWJFWQJS"
THEME_COLOR = "#209cee"
INITIAL_SCALE = 1.0
if gethostname() == "averbachs":
    RENDERED_PUBLIC_FILES_PATH = f"/var/www/{BASE_URL.split('/')[-1]}/html"
else:
    # local on Mac
    RENDERED_PUBLIC_FILES_PATH = f"/Users/zev/{BASE_URL.split('/')[-1]}/html"


class NoPages(Exception):
    ...


GLOBALS = dict(
    BASE_URL=BASE_URL,
    THEME_COLOR=THEME_COLOR,
    fathom_uid=FATHOM_UID,
    TABLE_NAME=TABLE_NAME,
    INITIAL_SCALE=INITIAL_SCALE,
)


def create_page(**content: dict) -> None:
    if "page_type" not in content:
        content["page_type"] = PAGE_TYPE_DEFAULT  # type: ignore
    do_query(f"insert into {TABLE_NAME} {tuple(content.keys())} values {tuple(content.values())}")
    update_pages()


def update_pages():
    render_all_updated_pages()
    render_toc()
    update_sitemap()


def render_all_updated_pages():
    with open(f"templates/page_0.0.1.html") as fin:
        template_str = fin.read()
    template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
    all_pages = get_all_pages()
    for page in all_pages:
        rendered = template.render(**page, **GLOBALS)
        html_file = Path(RENDERED_PUBLIC_FILES_PATH) / (page["url"] + ".html")
        if not html_file.exists():
            if "/" in page["url"]:
                html_file.parent.mkdir(parents=True, exist_ok=True)
            with html_file.open("w") as fout:
                print(f"creating {page['url']} for the first time ({html_file})")
                fout.write(rendered)
                continue
        with html_file.open() as fin:
            if fin.read() == rendered:
                continue
            else:
                with html_file.open("w") as fout:
                    print(f"rewriting {page['url']} ({html_file})")
                    fout.write(rendered)
                    continue


def get_all_pages() -> list[dict]:
    res = do_query(f"select * from {TABLE_NAME}")
    if res is None:
        raise NoPages
    return res


def render_toc() -> None:
    all_pages = do_query(f"select url, title, description, date from {TABLE_NAME}")

    def url_for(name: str, filename: str) -> str:
        return f"{name}/{filename}"

    with open(f"templates/toc_0.0.1.html") as fin:
        template_str = fin.read()
    template = Environment(loader=FileSystemLoader("templates/")).from_string(template_str)
    rendered = template.render(
        url_for=url_for,
        all_pages=all_pages,
        url="toc",
        **GLOBALS,
    )
    html_file = Path(RENDERED_PUBLIC_FILES_PATH) / f"toc.html"
    if html_file.exists():
        with html_file.open() as fin:
            if fin.read() == rendered:
                return
    with html_file.open("w") as fout:
        fout.write(rendered)


def update_sitemap():
    subprocess.call(
        f"sitemap-generator {BASE_URL} --filepath {os.getenv('SITEMAP_PATH')}", shell=True
    )


def delete_page(url: str) -> None:
    do_query(f"delete from {TABLE_NAME} where url = '{url}'")
    remove_all_pages_which_arent_in_db()


def remove_all_pages_which_arent_in_db() -> None:
    all_pages = get_all_pages()
    urls = [p["url"] for p in all_pages]
    root_directory = Path(RENDERED_PUBLIC_FILES_PATH)
    for path_object in root_directory.glob("**/*"):
        if path_object.is_file():
            subpath = str(path_object).replace(f"{RENDERED_PUBLIC_FILES_PATH}/", "")
            if subpath.startswith("static") or any(
                subpath.endswith(i) for i in ("robots.txt", "toc.html", "sitemap.xml")
            ):
                continue
            if subpath.replace(".html", "") not in urls:
                path_object.unlink()
                print(f"removed {path_object} because it's not in DB")


def update_static_files() -> None:
    for f in Path("static").iterdir():
        if f.name in ("robots.txt", "sitemap.xml"):
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
            print(f"{f} doesn't exist in public folder, copying it there.")
            shutil.copy(f, public_path)


def update_everything():
    update_static_files()
    render_all_updated_pages()
    remove_all_pages_which_arent_in_db()
    render_toc()
    update_sitemap()
