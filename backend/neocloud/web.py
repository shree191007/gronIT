"""Serves the static site in site/ next to the API, so one server runs everything."""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from .config import ROOT

SITE = ROOT.parent / "site"
router = APIRouter()


@router.get("/", include_in_schema=False)
def home():
    return FileResponse(SITE / "index.html", media_type="text/html")


@router.get("/{page}", include_in_schema=False)
def page(page: str):
    path = SITE / (page if page.endswith(".html") else page + ".html")
    if path.parent != SITE or not path.is_file():
        raise HTTPException(404, "not found")
    return FileResponse(path, media_type="text/html")
