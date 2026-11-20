"""Self-test for scripts/installer_package.py: the thin installer zip and its check."""

import installer_package as module
import os
import pytest
import stat
import subprocess
import zipfile
from installer_package import ZipError, build_zip, check_zip, zip_name
from pathlib import Path

EXPECTED = ("megabonk-installer", "README.txt")


def binary(path: Path, body: bytes = b"ELF fake installer") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    path.chmod(0o755)
    return path


def entries(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        return archive.namelist()


def test_zip_holds_exactly_the_binary_and_the_readme(tmp_path):
    binary(tmp_path / "megabonk-installer-linux-amd64")
    out = build_zip(tmp_path / "megabonk-installer-linux-amd64", tmp_path / "out.zip", platform="linux", version="0.4.2")
    assert entries(out) == list(EXPECTED)


def test_zip_name_carries_the_version_and_platform():
    assert zip_name("0.4.2", "linux") == "megabonk-installer-0.4.2-linux.zip"
    assert zip_name("dev", "windows") == "megabonk-installer-dev-windows.zip"
    assert zip_name("dev", "macos") == "megabonk-installer-dev-macos.zip"


@pytest.mark.parametrize(
    "platform,member", [("linux", "megabonk-installer"), ("windows", "megabonk-installer.exe"), ("macos", "megabonk-installer")]
)
def test_the_binary_is_named_for_its_platform(tmp_path, platform, member):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform=platform, version="dev")
    assert entries(out) == [member, "README.txt"]


def test_the_binary_keeps_its_executable_bit_and_the_readme_does_not(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    with zipfile.ZipFile(out) as archive:
        modes = {info.filename: stat.S_IMODE(info.external_attr >> 16) for info in archive.infolist()}
    assert modes["megabonk-installer"] == 0o755
    assert modes["README.txt"] == 0o644


def test_the_readme_says_how_to_run_it_and_what_it_installs(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="windows", version="0.1.0")
    with zipfile.ZipFile(out) as archive:
        readme = archive.read("README.txt").decode()
    for wanted in ["megabonk-installer.exe", "level editor mod", "megabonkmod.party", "Thunderstore"]:
        assert wanted in readme
    assert "Windows" in readme


@pytest.mark.parametrize(
    "platform,wanted", [("linux", "./megabonk-installer"), ("windows", "megabonk-installer.exe"), ("macos", "xattr")]
)
def test_each_platform_readme_names_its_own_run_command(tmp_path, platform, wanted):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform=platform, version="dev")
    with zipfile.ZipFile(out) as archive:
        assert wanted in archive.read("README.txt").decode()


def builder_code() -> str:
    """The builder's code with its README prose and links removed, so only what it reads and writes is left."""
    text = (Path(__file__).resolve().parents[1] / "scripts/installer_package.py").read_text()
    body = text.split('def readme_text', 1)[1].split("def zip_stamp", 1)[0]
    return "\n".join(line for line in (text.replace(body, "")).lower().splitlines() if "http" not in line)


def test_the_builder_never_names_content_or_vendor_inputs():
    source = builder_code()
    for forbidden in [
        "melonloader",
        "dotnet",
        "vendor",
        "thunderstore",
        "mod.dll",
        "levels/",
        "userlibs",
        "bepinex",
        "requests",
        "urllib",
        "sha256",
        "manifest.json",
    ]:
        assert forbidden not in source, f"the builder must not reference {forbidden}"


def test_the_readme_says_what_a_player_no_longer_needs():
    text = (Path(__file__).resolve().parents[1] / "scripts/installer_package.py").read_text()
    assert "no repo checkout" in text


def test_a_missing_binary_is_reported_as_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="installer binary"):
        build_zip(tmp_path / "nope", tmp_path / "out.zip", platform="linux", version="dev")


def test_an_unknown_platform_is_refused(tmp_path):
    binary(tmp_path / "installer")
    with pytest.raises(ZipError, match="Unknown package platform"):
        build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="plan9", version="dev")


def test_the_zip_is_reproducible_for_a_fixed_epoch(tmp_path):
    binary(tmp_path / "installer")
    first = build_zip(
        tmp_path / "installer", tmp_path / "a.zip", platform="linux", version="dev", env={"SOURCE_DATE_EPOCH": "1700000000"}
    )
    second = build_zip(
        tmp_path / "installer", tmp_path / "b.zip", platform="linux", version="dev", env={"SOURCE_DATE_EPOCH": "1700000000"}
    )
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert {info.date_time for info in archive.infolist()} == {(2023, 11, 14, 22, 13, 20)}


def test_a_different_epoch_changes_the_zip(tmp_path):
    binary(tmp_path / "installer")
    first = build_zip(
        tmp_path / "installer", tmp_path / "a.zip", platform="linux", version="dev", env={"SOURCE_DATE_EPOCH": "1700000000"}
    )
    second = build_zip(
        tmp_path / "installer", tmp_path / "b.zip", platform="linux", version="dev", env={"SOURCE_DATE_EPOCH": "1600000000"}
    )
    assert first.read_bytes() != second.read_bytes()


def test_no_epoch_falls_back_to_a_fixed_timestamp(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev", env={})
    with zipfile.ZipFile(out) as archive:
        assert all(info.date_time[0] >= 1980 for info in archive.infolist())


def test_the_output_directory_is_created(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "nested" / "out.zip", platform="macos", version="dev")
    assert out.is_file()


def test_check_accepts_a_built_zip(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="windows", version="dev")
    assert check_zip(out, platform="windows") == []


def test_check_reports_any_extra_entry(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    with zipfile.ZipFile(out, "a") as archive:
        archive.writestr("MegabonkLevels.Mod.dll", b"MZ")
    problems = check_zip(out, platform="linux")
    assert len(problems) == 1
    assert "MegabonkLevels.Mod.dll" in problems[0]


@pytest.mark.parametrize(
    "member",
    [
        "vendor/MelonLoader.x64.zip",
        "content/levels/thps.mblevel.json",
        "manifest.json",
        "dotnet/runtime.zip",
        "BepInEx/plugins/x.dll",
    ],
)
def test_check_reports_each_kind_of_stray_content(tmp_path, member):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    with zipfile.ZipFile(out, "a") as archive:
        archive.writestr(member, b"stray")
    problems = check_zip(out, platform="linux")
    assert problems and member in problems[0]


def test_check_reports_a_missing_member(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    rewritten = tmp_path / "stripped.zip"
    with zipfile.ZipFile(out) as source, zipfile.ZipFile(rewritten, "w") as target:
        for info in source.infolist():
            if info.filename != "README.txt":
                target.writestr(info.filename, source.read(info.filename))
    problems = check_zip(rewritten, platform="linux")
    assert problems and "README.txt" in problems[0]


def test_check_reports_a_wrong_binary_name(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="windows", version="dev")
    rewritten = tmp_path / "stripped.zip"
    with zipfile.ZipFile(out) as source, zipfile.ZipFile(rewritten, "w") as target:
        for info in source.infolist():
            name = "megabonk-installer" if info.filename == "megabonk-installer.exe" else info.filename
            target.writestr(name, source.read(info.filename))
    problems = check_zip(rewritten, platform="windows")
    assert problems and "megabonk-installer.exe" in problems[0]


def test_a_directory_entry_is_not_a_member(tmp_path):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    with zipfile.ZipFile(out, "a") as archive:
        archive.writestr("extra/", b"")
    assert check_zip(out, platform="linux") == []


def test_check_reports_a_non_zip_file(tmp_path):
    path = tmp_path / "not-a-zip.zip"
    path.write_bytes(b"hello")
    problems = check_zip(path, platform="linux")
    assert problems and str(path) in problems[0]


def test_check_reports_a_missing_zip(tmp_path):
    problems = check_zip(tmp_path / "gone.zip", platform="linux")
    assert problems and "gone.zip" in problems[0]


def test_main_reports_problems_on_stderr_and_exits_one(tmp_path, capsys):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    with zipfile.ZipFile(out, "a") as archive:
        archive.writestr("content/packs/thps/thps", b"stray")
    assert module.main([str(out), "--platform", "linux"]) == 1
    assert "content/packs/thps/thps" in capsys.readouterr().err


def test_main_reports_each_problem_on_its_own_line(tmp_path, capsys):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="linux", version="dev")
    with zipfile.ZipFile(out, "a") as archive:
        archive.writestr("a.dll", b"x")
        archive.writestr("b.dll", b"y")
    assert module.main([str(out), "--platform", "linux"]) == 1
    errors = [line for line in capsys.readouterr().err.splitlines() if line]
    assert len(errors) == 2
    assert any("a.dll" in line for line in errors) and any("b.dll" in line for line in errors)


def test_main_returns_zero_for_a_built_zip(tmp_path, capsys):
    binary(tmp_path / "installer")
    out = build_zip(tmp_path / "installer", tmp_path / "out.zip", platform="macos", version="dev")
    assert module.main([str(out), "--platform", "macos"]) == 0
    assert "megabonk-installer" in capsys.readouterr().out


def test_build_main_writes_the_named_zip_and_prints_it(tmp_path, capsys):
    source = binary(tmp_path / ".tools/installer/megabonk-installer-linux-amd64")
    code = module.main(
        [
            "build",
            "--installer-binary",
            str(source),
            "--out-dir",
            str(tmp_path / "dist"),
            "--platform",
            "linux",
            "--version",
            "0.4.2",
        ]
    )
    assert code == 0
    assert (tmp_path / "dist" / "megabonk-installer-0.4.2-linux.zip").is_file()
    assert "megabonk-installer-0.4.2-linux.zip" in capsys.readouterr().out


def test_build_main_reports_a_missing_binary_as_exit_three(tmp_path, capsys):
    code = module.main(
        ["build", "--installer-binary", str(tmp_path / "gone"), "--out-dir", str(tmp_path / "dist"), "--platform", "linux"]
    )
    assert code == 3
    assert "installer binary" in capsys.readouterr().err


def test_the_script_runs_as_a_program(tmp_path):
    script = Path(__file__).resolve().parents[1] / "scripts/installer_package.py"
    source = binary(tmp_path / "installer")
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(script),
            "build",
            "--installer-binary",
            str(source),
            "--out-dir",
            str(tmp_path / "dist"),
            "--platform",
            "linux",
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "SOURCE_DATE_EPOCH": "1700000000"},
    )
    assert result.returncode == 0, result.stderr
    zip_path = tmp_path / "dist" / "megabonk-installer-dev-linux.zip"
    assert zip_path.is_file()
    checked = subprocess.run(
        ["uv", "run", "python", str(script), str(zip_path), "--platform", "linux"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert checked.returncode == 0, checked.stderr


def test_build_main_refuses_a_directory_as_the_binary(tmp_path, capsys):
    directory = tmp_path / "installer-dir"
    directory.mkdir()
    code = module.main(
        ["build", "--installer-binary", str(directory), "--out-dir", str(tmp_path / "dist"), "--platform", "macos"]
    )
    assert code == 3
    assert "installer binary" in capsys.readouterr().err


def test_the_old_builder_and_manifest_contract_are_gone():
    root = Path(__file__).resolve().parents[1]
    assert not (root / "scripts/build_player_package.py").exists()
    assert not (root / "scripts/package_contract").exists()
    assert not (root / "tests/test_build_player_package.py").exists()
    assert not (root / "tests/test_package_manifest.py").exists()
    assert not (root / "tests/test_package_packs.py").exists()


def _package_tasks() -> dict:
    import yaml

    text = (Path(__file__).resolve().parents[1] / "taskfiles/package.yml").read_text()
    return yaml.safe_load(text)["tasks"]


@pytest.mark.parametrize(
    "task,target,binary",
    [
        ("linux", "linux/amd64", "megabonk-installer-linux-amd64"),
        ("windows", "windows/amd64", "megabonk-installer-windows-amd64.exe"),
        ("macos", "darwin/arm64", "megabonk-installer-darwin-arm64"),
    ],
)
def test_each_platform_task_builds_its_installer_and_zips_it(task, target, binary):
    tasks = _package_tasks()
    body = tasks[task]
    assert not body.get("internal"), f"package:{task} must be a public task"
    rendered = str(body)
    assert target in rendered, f"package:{task} must build {target}"
    assert "installer:build" in rendered
    assert binary in rendered, f"package:{task} must zip {binary}"
    assert "scripts/installer_package.py" in rendered
    assert "build_player_package" not in rendered
    assert "dotnet build" not in rendered


def test_the_macos_task_still_codesigns_and_notarizes():
    rendered = str(_package_tasks()["macos"])
    assert "APPLE_SIGNING_IDENTITY" in rendered
    assert "codesign" in rendered
    assert "scripts/notarize_macos.py" in rendered
    assert "megabonk-installer-{{.MOD_VERSION}}-macos.zip" in rendered


def test_the_check_task_verifies_a_zip():
    rendered = str(_package_tasks()["check"])
    assert "scripts/installer_package.py" in rendered
    assert "CHECK_PLATFORM" in rendered


def test_the_thunderstore_tasks_are_untouched():
    tasks = _package_tasks()
    for name in ("thunderstore", "thunderstore:manifest", "thunderstore:check"):
        assert name in tasks
    assert "tcli build" in str(tasks["thunderstore"])
