import json
import subprocess
import sys
from pathlib import Path

from arm64nsd.infrastructure.arm64.parser_adapter import Arm64AssemblyParser
from arm64nsd.infrastructure.arm64.tokenizer import Arm64Tokenizer
from arm64nsd.infrastructure.filesystem.source_repository import FileSystemSourceRepository


ROOT = Path(__file__).resolve().parent.parent


def test_tokenizer_parses_simple_function() -> None:
    tokenizer = Arm64Tokenizer()
    source = (ROOT / "tests" / "fixtures" / "simple.s").read_text(encoding="utf-8")
    lines = tokenizer.tokenize(source)

    # Should find instructions
    instructions = [line for line in lines if line.is_instruction]
    assert len(instructions) >= 3  # mov, add, ret

    mnemonics = [line.mnemonic for line in instructions if line.mnemonic]
    assert "mov" in mnemonics
    assert "add" in mnemonics
    assert "ret" in mnemonics


def test_tokenizer_parses_control_flow() -> None:
    tokenizer = Arm64Tokenizer()
    source = (ROOT / "tests" / "fixtures" / "control_flow.s").read_text(encoding="utf-8")
    lines = tokenizer.tokenize(source)

    # Should find labels
    labels = [line.label for line in lines if line.label is not None]
    assert "_score" in labels
    assert "_normalize" in labels

    # Should find directives
    directives = [line.directive for line in lines if line.directive is not None]
    assert ".text" in directives
    assert ".global" in directives


def test_parser_extracts_structure() -> None:
    parser = Arm64AssemblyParser()
    from arm64nsd.domain.model import SourceUnit, SourceUnitId

    source = (ROOT / "tests" / "fixtures" / "simple.s").read_text(encoding="utf-8")
    source_unit = SourceUnit(
        identifier=SourceUnitId("/tmp/simple.s"),
        location="/tmp/simple.s",
        content=source,
    )

    outcome = parser.parse(source_unit)

    assert outcome.status.value in ("succeeded", "succeeded_with_diagnostics")
    element_kinds = {element.kind.value for element in outcome.structural_elements}
    assert "section" in element_kinds  # .text
    assert "directive" in element_kinds  # .global _main
    assert "label" in element_kinds  # _main:


def test_parser_handles_control_flow_fixture() -> None:
    parser = Arm64AssemblyParser()
    from arm64nsd.domain.model import SourceUnit, SourceUnitId

    source = (ROOT / "tests" / "fixtures" / "control_flow.s").read_text(encoding="utf-8")
    source_unit = SourceUnit(
        identifier=SourceUnitId("/tmp/control_flow.s"),
        location="/tmp/control_flow.s",
        content=source,
    )

    outcome = parser.parse(source_unit)

    assert outcome.status.value in ("succeeded", "succeeded_with_diagnostics")
    labels = {
        element.name
        for element in outcome.structural_elements
        if element.kind.value == "label"
    }
    assert "_score" in labels
    assert "_normalize" in labels


def test_source_repository_lists_asm_files() -> None:
    repo = FileSystemSourceRepository()
    sources = repo.list_asm_sources(str(ROOT / "tests" / "fixtures"))

    assert len(sources) == 3  # simple.s, control_flow.s, invalid.s
    suffixes = {Path(s.location).suffix for s in sources}
    assert suffixes == {".s"}


def test_cli_nassi_file_produces_html(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arm64nsd.presentation.cli.main",
            "nassi-file",
            str(ROOT / "tests" / "fixtures" / "simple.s"),
            "--out",
            str(tmp_path / "simple.nassi.html"),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["function_count"] >= 1
    output_path = tmp_path / "simple.nassi.html"
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "ARM64" in html
    assert "Nassi-Shneiderman" in html
