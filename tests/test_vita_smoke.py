import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SMOKE_SOURCE = Path(__file__).resolve().parents[1] / "vita" / "smoke"


def test_vita_smoke_livearea_identifies_the_app():
    page = ET.parse(SMOKE_SOURCE / "livearea.xml").getroot()
    assert page.attrib["style"] == "psmobile"
    assert page.findtext("livearea-background/image") == "bg.png"
    assert page.findtext("frame[@id='frame2']/liveitem/text/str") == "Megabonk Vita Smoke"
    assert page.findtext("frame[@id='frame3']/liveitem/text/str") == "Hardware smoke test"


def test_vita_smoke_metrics(tmp_path):
    binary = tmp_path / "test_metrics"
    subprocess.run(
        [
            os.environ.get("CC", "cc"),
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            str(SMOKE_SOURCE / "test_metrics.c"),
            "-o",
            str(binary),
        ],
        check=True,
    )
    subprocess.run([binary], check=True)
