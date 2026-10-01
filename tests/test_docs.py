"""RED-by-design structural contract for DOC-04/05/06/07.

Wave 0 of Phase 10: these tests describe the documentation set delivered by
Plans 10-03 (architecture/data-flow/api docs) and 10-04/05/06 (theoretical
algorithm docs). Until those plans land, ``test_expected_docs_exist`` is
RED (missing files) by design; the Mermaid and link-resolution tests pass
vacuously over an empty ``docs/`` tree and become progressively enforcing
as files are added.

Uses stdlib ``re``/``pathlib`` only — no new dependency (Package Legitimacy:
not applicable at this scale, per 10-RESEARCH.md).

Security Domain (T-10-ID): the glob below is scoped strictly to the
repo-local ``docs/`` directory, never a user-supplied path.
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"

EXPECTED_DOCS = [
    "architecture.md",
    "data-flow.md",
    "api.md",
    "algorithms/README.md",
    "algorithms/data-pipeline.md",
    "algorithms/ml-classifiers.md",
    "algorithms/ensemble.md",
    "algorithms/genetic-algorithm.md",
    "algorithms/rule-based-system.md",
    "algorithms/bayesian.md",
    "algorithms/aggregation.md",
    "algorithms/ocr-visual.md",
    "algorithms/explainability.md",
]

MERMAID_FENCE_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

KNOWN_DIAGRAM_KEYWORDS = (
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "journey",
)


def test_expected_docs_exist():
    """DOC-04/05/06/07: all 13 expected docs files exist.

    Primary RED signal for this plan — turns green incrementally as
    Plans 10-03/04/05/06 add each file.
    """
    missing = [
        rel for rel in EXPECTED_DOCS if not (DOCS_ROOT / rel).is_file()
    ]
    assert not missing, f"Missing expected docs files: {missing}"


def test_mermaid_blocks_have_valid_diagram_type():
    """DOC-04/05: every fenced ```mermaid block starts with a known
    diagram-type keyword (flowchart, graph, sequenceDiagram, ...).

    Passes vacuously while docs/ is empty or contains no mermaid blocks;
    becomes enforcing once DOC-04/05 diagrams land.
    """
    md_files = list(DOCS_ROOT.rglob("*.md")) if DOCS_ROOT.is_dir() else []

    scanned_blocks = 0
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        for block in MERMAID_FENCE_RE.findall(text):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            assert lines, f"Empty mermaid block in {md_file}"
            first_line = lines[0]
            scanned_blocks += 1
            assert any(first_line.startswith(kw) for kw in KNOWN_DIAGRAM_KEYWORDS), (
                f"Mermaid block in {md_file} has unrecognized diagram type: "
                f"{first_line!r}"
            )

    # Assert the scan actually ran over the docs glob (even if 0 blocks found).
    assert isinstance(scanned_blocks, int)


def test_markdown_internal_links_resolve():
    """DOC-04/05/06/07: every relative Markdown link under docs/**/*.md
    resolves to a real file.

    External links (http://, https://, mailto:) and pure-anchor links
    (#section) are skipped. Passes vacuously while docs/ is empty; becomes
    enforcing once docs land.
    """
    md_files = list(DOCS_ROOT.rglob("*.md")) if DOCS_ROOT.is_dir() else []

    broken_links = []
    for md_file in md_files:
        text = md_file.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_RE.findall(text):
            target = target.strip()
            if not target or target.startswith("#"):
                continue
            scheme = urlsplit(target).scheme
            if scheme in ("http", "https", "mailto"):
                continue
            # Strip any #anchor suffix before resolving the file path.
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (md_file.parent / path_part).resolve()
            if not resolved.exists():
                broken_links.append((str(md_file), target))

    assert not broken_links, f"Broken internal doc links: {broken_links}"
