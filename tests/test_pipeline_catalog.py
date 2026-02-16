import argparse
import curses
import importlib.util
from pathlib import Path


def _load_pipeline_module():
    module_path = Path(__file__).resolve().parent.parent / "04_pipeline.py"
    spec = importlib.util.spec_from_file_location("pipeline04", str(module_path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _args(**overrides):
    base = {
        "doc_target": None,
        "project": None,
        "version": None,
        "doc_root": "https://www.microfocus.com/documentation/idol/",
        "refresh_catalog": False,
        "catalog_ttl_hours": 24.0,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_parse_project_version_known_patterns():
    mod = _load_pipeline_module()
    assert mod._parse_project_version("knowledge-discovery-25.4") == ("knowledge-discovery", "25.4")
    assert mod._parse_project_version("IDOL_24_4") == ("IDOL", "24.4")
    assert mod._parse_project_version("something-without-version") is None


def test_resolve_doc_url_accepts_full_url():
    mod = _load_pipeline_module()
    args = _args(doc_target="https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4")
    assert mod.resolve_doc_url(args) == "https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/"


def test_resolve_doc_url_from_project_and_version(monkeypatch):
    mod = _load_pipeline_module()
    monkeypatch.setattr(
        mod,
        "load_catalog",
        lambda **kwargs: [
            {
                "project": "knowledge-discovery",
                "project_label": "knowledge-discovery",
                "version": "25.4",
                "url": "https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/",
            }
        ],
    )
    args = _args(project="knowledge-discovery", version="25.4")
    assert mod.resolve_doc_url(args) == "https://www.microfocus.com/documentation/idol/knowledge-discovery-25.4/"


def test_resolve_doc_url_version_as_positional(monkeypatch):
    mod = _load_pipeline_module()
    monkeypatch.setattr(
        mod,
        "load_catalog",
        lambda **kwargs: [
            {
                "project": "knowledge-discovery",
                "project_label": "knowledge-discovery",
                "version": "26.1",
                "url": "https://www.microfocus.com/documentation/idol/knowledge-discovery-26.1/",
            }
        ],
    )
    args = _args(doc_target="26.1", project="knowledge-discovery")
    assert mod.resolve_doc_url(args) == "https://www.microfocus.com/documentation/idol/knowledge-discovery-26.1/"


def _catalog_entries():
    return [
        {
            "project": "knowledge-discovery",
            "project_label": "knowledge-discovery",
            "version": "26.1",
            "url": "https://example/knowledge-discovery-26.1/",
        },
        {
            "project": "knowledge-discovery",
            "project_label": "knowledge-discovery",
            "version": "25.4",
            "url": "https://example/knowledge-discovery-25.4/",
        },
    ]


def test_catalog_selector_backspace_goes_back_to_project_mode():
    mod = _load_pipeline_module()
    selector = mod.CatalogSelectorTUI(_catalog_entries(), refresh_callback=lambda: _catalog_entries())
    selector.mode = "version"
    selector.handle_input(127)  # Backspace
    assert selector.mode == "project"


def test_catalog_selector_left_arrow_goes_back_to_project_mode():
    mod = _load_pipeline_module()
    selector = mod.CatalogSelectorTUI(_catalog_entries(), refresh_callback=lambda: _catalog_entries())
    selector.mode = "version"
    selector.handle_input(curses.KEY_LEFT)
    assert selector.mode == "project"
