"""P03 tool tests part 1 (T03.020, T03.023-T03.026): registry, compute, parsers."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel

from sots.agents.tools import compute as compute_mod
from sots.agents.tools import parse_html as parse_html_mod
from sots.agents.tools import parse_pdf as parse_pdf_mod
from sots.agents.tools import parse_table as parse_table_mod
from sots.agents.tools.base import (
    ToolContext,
    clear_registry,
    get_tool,
    register_tool,
    registered_tools,
)
from sots.config import load_settings
from sots.errors import ConfigError
from sots.models.agents import Observation

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def _ctx() -> ToolContext:
    return ToolContext(
        run_id="run_1", document_id="doc_1",
        settings=load_settings(CONFIG_DIR, env_file=None),
    )


# --- T03.020: protocol + registry ---


class _Args(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    q: str = ""


class _Probe:
    name = "probe_tool"
    internet = False
    args_model = _Args

    async def run(self, args: BaseModel, ctx: ToolContext) -> Observation:
        assert isinstance(args, _Args)
        _ = ctx
        return Observation(tool=self.name, ok=True, content=args.q, truncated=False)


def test_registry_register_get_and_errors() -> None:
    snapshot = registered_tools()
    try:
        clear_registry()
        assert registered_tools() == {}
        tool = register_tool(_Probe())
        assert get_tool("probe_tool") is tool
        with pytest.raises(ValueError, match="already registered"):
            register_tool(_Probe())
        with pytest.raises(ConfigError, match="not registered"):
            get_tool("ghost")
    finally:
        clear_registry()
        for registered in snapshot.values():
            register_tool(registered)


def test_builtin_tools_registered() -> None:
    names = registered_tools()
    for expected in ("compute", "parse_html", "parse_pdf", "parse_table"):
        assert expected in names
    assert names["compute"].internet is False
    assert names["compute"].args_model is compute_mod.ComputeArgs


async def test_probe_tool_run() -> None:
    tool = get_tool("compute")
    obs = await tool.run(compute_mod.ComputeArgs(expression="1 + 1"), _ctx())
    assert obs.ok and '"result": 2.0' in obs.content


# --- T03.026: compute ---


@pytest.mark.parametrize(
    ("expression", "columns", "expected"),
    [
        ("1 + 2 * 3", {}, 7.0),
        ("(10 - 4) / 3", {}, 2.0),
        ("-5 + 2", {}, -3.0),
        ("mean(revenue)", {"revenue": [10.0, 20.0, 30.0]}, 20.0),
        ("median(x)", {"x": [3.0, 1.0, 2.0]}, 2.0),
        ("sum(x) / max(n)", {"x": [1.0, 2.0], "n": [3.0]}, 1.0),
        ("min(a) + max(a)", {"a": [4.0, 9.0]}, 13.0),
        ("pct_change(100, 115)", {}, 0.15),
        ("ratio(3, 4)", {}, 0.75),
    ],
)
def test_compute_valid(expression: str, columns: dict, expected: float) -> None:
    assert compute_mod.evaluate(expression, columns) == pytest.approx(expected)


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os')",
        "(lambda x: x)(1)",
        "x.attr",
        "x[0]",
        "mean",
        "2 ** 3",
        "7 // 2",
        "7 % 2",
        "unknown_fn(x)",
        "mean(x, y)",
        "pct_change(x)",
        "1 +",
        "'str'",
        "True",
        "x + y",
    ],
)
def test_compute_rejects(expression: str, columns: dict | None = None) -> None:
    with pytest.raises(ValueError):
        compute_mod.evaluate(expression, columns or {"x": [1.0]})


def test_compute_errors() -> None:
    with pytest.raises(ValueError, match="unknown column"):
        compute_mod.evaluate("mean(nope)", {})
    with pytest.raises(ValueError, match="empty column"):
        compute_mod.evaluate("sum(x)", {"x": []})
    with pytest.raises(ValueError, match="division by zero"):
        compute_mod.evaluate("1 / 0", {})
    with pytest.raises(ValueError, match="zero denominator"):
        compute_mod.evaluate("ratio(1, 0)", {})


async def test_compute_tool_observation() -> None:
    tool = get_tool("compute")
    bad = await tool.run(compute_mod.ComputeArgs(expression="__import__('os')"), _ctx())
    assert bad.ok is False and bad.content.startswith("error:")


# --- T03.023: parse_html (3 fixtures) ---


HTML_ARTICLE = """<html><head><title>T</title><style>.x{}</style></head><body>
<h1>Main Title</h1><p>First paragraph with <b>bold</b> text.</p>
<h2>Section</h2><ul><li>one</li><li>two</li></ul>
<script>alert(1)</script></body></html>"""

HTML_TABLE = """<html><body><h2>Data</h2>
<table><tr><th>Name</th><th>Value</th></tr>
<tr><td>A</td><td>1,234</td></tr><tr><td>B</td><td>—</td></tr></table></body></html>"""

HTML_MESSY = """<div><p>Unclosed paragraph<div>Nested <span>deep</span>
<br>line break<p>Second</p><noscript>hidden</noscript></div>"""


def test_parse_html_article() -> None:
    text, truncated = parse_html_mod.parse_html(HTML_ARTICLE)
    assert truncated is False
    assert "# Main Title" in text
    assert "First paragraph with bold text." in text
    assert "## Section" in text
    assert "- one" in text and "- two" in text
    assert "alert" not in text and ".x{}" not in text


def test_parse_html_table() -> None:
    text, truncated = parse_html_mod.parse_html(HTML_TABLE)
    assert truncated is False
    assert "## Data" in text
    assert "[table]" in text
    assert "Name | Value" in text
    assert "A | 1,234" in text


def test_parse_html_messy_and_cap() -> None:
    text, _truncated = parse_html_mod.parse_html(HTML_MESSY)
    assert "Unclosed paragraph" in text and "Second" in text
    assert "hidden" not in text
    long_html = "<p>" + ("word " * 30000) + "</p>"
    capped, was_truncated = parse_html_mod.parse_html(long_html, max_chars=100)
    assert was_truncated is True
    assert "[truncated: showing 100 of" in capped
    assert len(capped) <= 200


async def test_parse_html_tool() -> None:
    obs = await get_tool("parse_html").run(
        parse_html_mod.ParseHtmlArgs(html="<p>hi</p>"), _ctx()
    )
    assert obs.ok and obs.content == "hi"


# --- T03.025: parse_table (6 fixtures) ---


def test_table_html_basic() -> None:
    result = parse_table_mod.parse_table(
        "html",
        "<table><tr><th>Year</th><th>Sales</th></tr>"
        "<tr><td>2020</td><td>1,234</td></tr>"
        "<tr><td>2021</td><td>2,500</td></tr></table>",
    )
    assert result["columns"] == ["Year", "Sales"]
    assert result["rows"] == [{"Year": 2020, "Sales": 1234}, {"Year": 2021, "Sales": 2500}]
    assert result["dtypes"] == {"Year": "int", "Sales": "int"}
    assert result["truncated"] is False


def test_table_csv_percents_and_missing() -> None:
    result = parse_table_mod.parse_table(
        "csv", "name,share,note\nA,12.5%,—\nB,50%,ok\n"
    )
    assert result["rows"] == [
        {"name": "A", "share": 0.125, "note": None},
        {"name": "B", "share": 0.5, "note": "ok"},
    ]
    assert result["dtypes"]["share"] == "float"


def test_table_json_rows() -> None:
    result = parse_table_mod.parse_table(
        "json", '[{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]'
    )
    assert result["columns"] == ["a", "b"]
    assert result["rows"][1] == {"a": 2, "b": "y"}
    assert result["dtypes"] == {"a": "int", "b": "str"}


def test_table_messy_mixed_and_ragged() -> None:
    result = parse_table_mod.parse_table(
        "csv", "item,price\napple,1.20\n,—\norange,not a number,EXTRA\n"
    )
    assert result["rows"][0] == {"item": "apple", "price": 1.2}
    assert result["rows"][1] == {"item": None, "price": None}
    assert result["rows"][2]["price"] == "not a number"
    assert result["dtypes"]["price"] == "str"


def test_table_row_cap() -> None:
    data = "n\n" + "\n".join(str(i) for i in range(2500)) + "\n"
    result = parse_table_mod.parse_table("csv", data)
    assert result["truncated"] is True
    assert len(result["rows"]) == 2000
    assert result["note"] == "showing 2000 of 2500 rows"


def test_table_errors() -> None:
    with pytest.raises(ValueError, match="no HTML table"):
        parse_table_mod.parse_table("html", "<p>no table</p>")
    with pytest.raises(ValueError, match="no rows"):
        parse_table_mod.parse_table("csv", "\n\n")
    with pytest.raises(ValueError, match="list of row objects"):
        parse_table_mod.parse_table("json", '{"a": 1}')


async def test_table_tool_error_observation() -> None:
    obs = await get_tool("parse_table").run(
        parse_table_mod.ParseTableArgs(format="csv", data="\n"), _ctx()
    )
    assert obs.ok is False and obs.content.startswith("error:")


# --- T03.024: parse_pdf ---


def _make_pdf(pages: list[str]) -> bytes:
    """Minimal valid multi-page PDF with a correct xref table."""
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{4 + i * 2} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for text in pages:
        safe = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 72 720 Td ({safe}) Tj ET".encode()
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {len(objects) + 2} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF".encode()
    )
    return bytes(out)


def test_parse_pdf_pages_and_range(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(_make_pdf(["Page one text", "Page two text", "Page three text"]))
    full = parse_pdf_mod.parse_pdf(pdf)
    assert full["pages"] == 3 and full["capped"] is False
    assert "Page one text" in full["text"] and "Page three text" in full["text"]
    middle = parse_pdf_mod.parse_pdf(pdf, page_start=2, page_end=2)
    assert "Page two text" in middle["text"]
    assert "Page one text" not in middle["text"]
    assert (middle["page_start"], middle["page_end"]) == (2, 2)


def test_parse_pdf_errors(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not found"):
        parse_pdf_mod.parse_pdf(tmp_path / "missing.pdf")
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="cannot read PDF"):
        parse_pdf_mod.parse_pdf(bad)
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(_make_pdf(["only"]))
    with pytest.raises(ValueError, match="page_start"):
        parse_pdf_mod.parse_pdf(pdf, page_start=0)
    with pytest.raises(ValueError, match="exceeds 1 pages"):
        parse_pdf_mod.parse_pdf(pdf, page_start=2, page_end=5)


def test_parse_pdf_page_cap(tmp_path: Path) -> None:
    pdf = tmp_path / "big.pdf"
    pdf.write_bytes(_make_pdf([f"p{i}" for i in range(35)]))
    result = parse_pdf_mod.parse_pdf(pdf)
    assert result["capped"] is True
    assert (result["page_start"], result["page_end"]) == (1, 30)
    assert "p29" in result["text"] and "p30" not in result["text"]


async def test_parse_pdf_tool(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(_make_pdf(["hello pdf"]))
    obs = await get_tool("parse_pdf").run(
        parse_pdf_mod.ParsePdfArgs(path=str(pdf)), _ctx()
    )
    assert obs.ok and "hello pdf" in obs.content
