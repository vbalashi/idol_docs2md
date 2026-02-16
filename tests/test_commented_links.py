import importlib.util
from pathlib import Path


def _load_converter_module():
    module_path = Path(__file__).resolve().parent.parent / "02_convert_to_md.py"
    spec = importlib.util.spec_from_file_location("converter02", str(module_path))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_unwrap_markdown_link_inside_comment():
    mod = _load_converter_module()
    src = "Header\n<!-- [OpenText](https://www.opentext.com) -->\nBody"
    out = mod.unwrap_commented_links(src)
    assert "[OpenText](https://www.opentext.com)" in out
    assert "<!-- [OpenText](https://www.opentext.com) -->" not in out


def test_clean_markdown_content_preserves_non_link_comments():
    mod = _load_converter_module()
    src = "<!-- BEGIN_FILE: Content/Page.md -->\n<!-- ... -->\nText"
    out = mod.clean_markdown_content(src)
    assert "<!-- ... -->" in out


def test_unwrap_html_anchor_inside_comment():
    mod = _load_converter_module()
    src = '<!-- <a href="https://example.com/path">Example</a> -->'
    out = mod.unwrap_commented_links(src)
    assert out == "[Example](https://example.com/path)"


def test_format_external_output_content_rewrites_begin_file_marker():
    mod = _load_converter_module()
    src = "<!-- BEGIN_FILE: Content/Upgrade/_Upgrade.md -->\n# Title [↗](https://example.com/x.htm)"
    out = mod.format_external_output_content(src)
    assert "[[BEGIN_FILE: Content/Upgrade/_Upgrade.md]]" in out
    assert "<!-- BEGIN_FILE:" not in out


def test_format_external_output_content_splits_header_and_link():
    mod = _load_converter_module()
    src = "# Upgrade from IDOL 12.x [↗](https://example.com/u.htm)"
    out = mod.format_external_output_content(src)
    assert "# Upgrade from IDOL 12.x" in out
    assert "[https://example.com/u.htm](https://example.com/u.htm)" in out
