import json
import re
import subprocess
import sys
from pathlib import Path

from arm64nsd.domain.control_flow import (
    ActionFlowStep,
    ControlFlowDiagram,
    FunctionControlFlow,
    IfFlowStep,
    SwitchCaseFlow,
    SwitchFlowStep,
    WhileFlowStep,
)
from arm64nsd.infrastructure.arm64.control_flow_extractor import Arm64AsmControlFlowExtractor
from arm64nsd.infrastructure.filesystem.source_repository import FileSystemSourceRepository
from arm64nsd.infrastructure.rendering.nassi_html_renderer import HtmlNassiDiagramRenderer


ROOT = Path(__file__).resolve().parent.parent


def _build_extractor() -> Arm64AsmControlFlowExtractor:
    return Arm64AsmControlFlowExtractor()


def _build_renderer() -> HtmlNassiDiagramRenderer:
    return HtmlNassiDiagramRenderer()


# ---------------------------------------------------------------------------
# Basic rendering tests
# ---------------------------------------------------------------------------


def test_renderer_produces_html_with_arm64_branding() -> None:
    renderer = _build_renderer()
    diagram = ControlFlowDiagram(
        source_location="test.s",
        functions=(
            FunctionControlFlow(
                name="_main",
                signature="_main:",
                container=None,
                steps=(ActionFlowStep(label="mov x0, #0"),),
            ),
        ),
    )
    html = renderer.render(diagram)

    assert "ARM64" in html
    assert "NSD Viewer" in html
    assert "mov x0, #0" in html


def test_renderer_renders_if_else() -> None:
    renderer = _build_renderer()
    diagram = ControlFlowDiagram(
        source_location="if_test.s",
        functions=(
            FunctionControlFlow(
                name="_test",
                signature="_test:",
                container=None,
                steps=(
                    IfFlowStep(
                        condition="cmp x0, #0 / b.gt",
                        then_steps=(ActionFlowStep(label="add x0, x0, #1"),),
                        else_steps=(ActionFlowStep(label="mov x0, #0"),),
                    ),
                ),
            ),
        ),
    )
    html = renderer.render(diagram)

    assert "ns-if-cap" in html
    assert "ns-branch-yes" in html
    assert "ns-branch-no" in html
    assert "add x0, x0, #1" in html


def test_renderer_renders_while_loop() -> None:
    renderer = _build_renderer()
    diagram = ControlFlowDiagram(
        source_location="while_test.s",
        functions=(
            FunctionControlFlow(
                name="_loop",
                signature="_loop:",
                container=None,
                steps=(
                    WhileFlowStep(
                        condition="cmp x1, #10 / b.lt",
                        body_steps=(
                            ActionFlowStep(label="add x1, x1, #1"),
                        ),
                    ),
                ),
            ),
        ),
    )
    html = renderer.render(diagram)

    assert "ns-loop" in html
    assert "add x1, x1, #1" in html


def test_renderer_renders_switch() -> None:
    renderer = _build_renderer()
    diagram = ControlFlowDiagram(
        source_location="switch_test.s",
        functions=(
            FunctionControlFlow(
                name="_switch",
                signature="_switch:",
                container=None,
                steps=(
                    SwitchFlowStep(
                        expression="cmp x4, ...",
                        cases=(
                            SwitchCaseFlow(label="case_zero", steps=(ActionFlowStep(label="mov x0, #0"),)),
                            SwitchCaseFlow(label="case_one", steps=(ActionFlowStep(label="mov x0, #1"),)),
                        ),
                    ),
                ),
            ),
        ),
    )
    html = renderer.render(diagram)

    assert "ns-switch" in html
    assert "case_zero" in html
    assert "case_one" in html


# ---------------------------------------------------------------------------
# If depth rendering tests
# ---------------------------------------------------------------------------


class TestIfDepthRendering:
    def test_depth_badge_zero_is_empty(self) -> None:
        renderer = _build_renderer()
        assert renderer._depth_badge(0) == ""

    def test_depth_badges_1_to_10_use_circled_digits(self) -> None:
        renderer = _build_renderer()
        assert renderer._depth_badge(1) == " \u2460"
        assert renderer._depth_badge(5) == " \u2464"
        assert renderer._depth_badge(10) == " \u2469"

    def test_depth_badges_21_to_35(self) -> None:
        renderer = _build_renderer()
        assert renderer._depth_badge(21) == " \u3251"
        assert renderer._depth_badge(35) == " \u325f"

    def test_depth_css_generates_51_levels(self) -> None:
        renderer = _build_renderer()
        css = renderer._depth_css()
        assert ".ns-if-depth-0-triangle" in css
        assert ".ns-if-depth-50-triangle" in css

    def test_render_if_cap_at_depth_zero(self) -> None:
        renderer = _build_renderer()
        html = renderer._render_if_cap("cmp x0, #0", depth=0)
        assert 'class="ns-if-cap ns-if-depth-0"' in html
        assert '<svg class="ns-if-svg"' in html

    def test_render_if_cap_at_depth_five(self) -> None:
        renderer = _build_renderer()
        html = renderer._render_if_cap("cmp x0, #0", depth=5)
        assert 'class="ns-if-cap ns-if-depth-5"' in html

    def test_render_if_cap_at_depth_fifty(self) -> None:
        renderer = _build_renderer()
        html = renderer._render_if_cap("cmp x0, #0", depth=50)
        assert 'class="ns-if-cap ns-if-depth-50"' in html

    def test_render_if_cap_clips_at_max_depth(self) -> None:
        renderer = _build_renderer()
        html = renderer._render_if_cap("cmp x0, #0", depth=100)
        assert 'class="ns-if-cap ns-if-depth-50"' in html


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------


def test_nassi_cli_writes_html_file(tmp_path: Path) -> None:
    output_path = tmp_path / "simple.html"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arm64nsd.presentation.cli.main",
            "nassi-file",
            str(ROOT / "tests" / "fixtures" / "simple.s"),
            "--out",
            str(output_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["function_count"] >= 1
    assert output_path.exists()
    html = output_path.read_text(encoding="utf-8")
    assert "Nassi-Shneiderman" in html


def test_nassi_dir_cli_writes_html_bundle(tmp_path: Path) -> None:
    output_dir = tmp_path / "nassi-bundle"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "arm64nsd.presentation.cli.main",
            "nassi-dir",
            str(ROOT / "tests" / "fixtures"),
            "--out",
            str(output_dir),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["document_count"] == 3
    assert (output_dir / "index.html").exists()
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "ARM64 NSD Index" in html


# ---------------------------------------------------------------------------
# Control flow extraction from ARM64 assembly
# ---------------------------------------------------------------------------


class TestArm64ControlFlowExtraction:
    def test_simple_function_extracted(self) -> None:
        extractor = _build_extractor()
        from arm64nsd.domain.model import SourceUnit, SourceUnitId

        source = SourceUnit(
            identifier=SourceUnitId("simple.s"),
            location="simple.s",
            content=(
                "    .text\n"
                "    .global _main\n"
                "_main:\n"
                "    mov x0, #0\n"
                "    add x0, x0, #1\n"
                "    ret\n"
            ),
        )
        diagram = extractor.extract(source)

        assert len(diagram.functions) >= 1
        assert diagram.functions[0].name == "_main"
        assert len(diagram.functions[0].steps) >= 2  # mov + add (ret is excluded)

    def test_if_else_pattern_detected(self) -> None:
        extractor = _build_extractor()
        from arm64nsd.domain.model import SourceUnit, SourceUnitId

        source = SourceUnit(
            identifier=SourceUnitId("if_else.s"),
            location="if_else.s",
            content=(
                "    .text\n"
                "    .global _check\n"
                "_check:\n"
                "    cmp x0, #0\n"
                "    b.le _check_else\n"
                "    add x0, x0, #1\n"
                "    b _check_end\n"
                "_check_else:\n"
                "    mov x0, #0\n"
                "_check_end:\n"
                "    ret\n"
            ),
        )
        diagram = extractor.extract(source)

        assert len(diagram.functions) >= 1
        func = diagram.functions[0]
        # Should have an IfFlowStep somewhere in the steps
        has_if = any(isinstance(step, IfFlowStep) for step in func.steps)
        assert has_if, f"Expected IfFlowStep in {[type(s).__name__ for s in func.steps]}"

    def test_while_loop_detected(self) -> None:
        extractor = _build_extractor()
        from arm64nsd.domain.model import SourceUnit, SourceUnitId

        source = SourceUnit(
            identifier=SourceUnitId("while.s"),
            location="while.s",
            content=(
                "    .text\n"
                "    .global _count\n"
                "_count:\n"
                "    mov x1, #0\n"
                "_count_loop:\n"
                "    cmp x1, #10\n"
                "    b.ge _count_done\n"
                "    add x1, x1, #1\n"
                "    b _count_loop\n"
                "_count_done:\n"
                "    ret\n"
            ),
        )
        diagram = extractor.extract(source)

        assert len(diagram.functions) >= 1
        func = diagram.functions[0]
        has_while = any(isinstance(step, WhileFlowStep) for step in func.steps)
        assert has_while, f"Expected WhileFlowStep in {[type(s).__name__ for s in func.steps]}"
