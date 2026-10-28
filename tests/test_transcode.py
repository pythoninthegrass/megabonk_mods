"""
Self-test for scripts/transcode.py.
"""

import pytest
import transcode
from pathlib import Path


def flac_streams() -> list[dict]:
    return [{"index": 0, "codec_type": "audio", "codec_name": "flac"}]


def test_resolve_output_swaps_the_extension_when_no_output_is_given() -> None:
    assert transcode.resolve_output(Path("tools/Goldfinger - Superman.flac"), None) == Path("tools/Goldfinger - Superman.mp3")


def test_resolve_output_only_replaces_the_final_extension() -> None:
    assert transcode.resolve_output(Path("tracks/Queen.24bit.flac"), None) == Path("tracks/Queen.24bit.mp3")


def test_resolve_output_uses_the_input_name_inside_a_directory(tmp_path: Path) -> None:
    assert transcode.resolve_output(Path("a/Song.flac"), str(tmp_path)) == tmp_path / "Song.mp3"


def test_resolve_output_adds_the_missing_extension(tmp_path: Path) -> None:
    assert transcode.resolve_output(Path("a/Song.flac"), str(tmp_path / "song")) == tmp_path / "song.mp3"


def test_resolve_output_rejects_a_destination_of_another_format(tmp_path: Path) -> None:
    with pytest.raises(transcode.TranscodeError, match="must be a .mp3"):
        transcode.resolve_output(Path("a/Song.flac"), str(tmp_path / "song.ogg"))


def test_resolve_output_refuses_to_overwrite_the_input() -> None:
    with pytest.raises(transcode.TranscodeError, match="already"):
        transcode.resolve_output(Path("a/Song.mp3"), None)


def test_transcode_command_encodes_v0_with_id3v2_3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcode, "VBR_QUALITY", "0")
    argv = transcode.transcode_command(Path("in.flac"), Path("out.mp3"), None)

    assert argv[:2] == [transcode.FFMPEG, "-hide_banner"]
    assert argv[-1] == "out.mp3"
    assert argv[argv.index("-map") + 1] == "0:a:0"
    assert argv[argv.index("-c:a") + 1 :] == ["libmp3lame", "-q:a", "0", "-map_metadata", "0", "-id3v2_version", "3", "out.mp3"]


def test_transcode_command_maps_cover_art_as_a_video_stream() -> None:
    without = transcode.transcode_command(Path("in.flac"), Path("out.mp3"), None)
    with_cover = transcode.transcode_command(Path("in.flac"), Path("out.mp3"), 1)

    assert "-c:v" not in without
    after_audio_map = with_cover[with_cover.index("-map", with_cover.index("0:a:0") + 1) + 1 :]
    assert after_audio_map[:4] == ["0:v:1", "-c:v", "copy", "-c:a"]


def test_first_attached_picture_counts_only_video_streams() -> None:
    streams = [
        {"index": 0, "codec_type": "video", "disposition": {"attached_pic": 0}},
        {"index": 1, "codec_type": "audio", "disposition": {"attached_pic": 0}},
        {"index": 2, "codec_type": "video", "disposition": {"attached_pic": 1}},
    ]

    assert transcode.first_attached_picture(streams) == 1


def test_first_attached_picture_is_none_without_a_cover() -> None:
    assert transcode.first_attached_picture(flac_streams()) is None


def test_parse_tag_list_splits_trims_and_lowercases() -> None:
    assert transcode.parse_tag_list(" Title , ALBUM ,,artist ") == ["title", "album", "artist"]


def test_settings_come_from_the_environment_through_decouple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEGABONK_MP3_VBR_QUALITY", "2")
    monkeypatch.setenv("MEGABONK_FFMPEG", "/opt/ffmpeg-7/bin/ffmpeg")

    assert transcode.config("MEGABONK_MP3_VBR_QUALITY", default="0") == "2"
    assert transcode.config("MEGABONK_FFMPEG", default="ffmpeg") == "/opt/ffmpeg-7/bin/ffmpeg"
    assert transcode.config("MEGABONK_MP3_UNSET_KEY", default="fallback") == "fallback"


def test_parse_tag_list_reads_the_core_tag_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcode, "CORE_TAGS", "artist, mood ")

    assert transcode.missing_core_tags({"artist": "X", "mood": "fast"}, {}) == ["artist", "mood"]


def test_missing_core_tags_is_empty_when_everything_survived() -> None:
    source = {"ARTIST": "Goldfinger", "TITLE": "Superman", "MOOD": "fast"}
    output = {"artist": "Goldfinger", "title": "Superman", "encoder": "Lavf"}

    assert transcode.missing_core_tags(source, output) == []


def test_missing_core_tags_names_a_dropped_tag_but_ignores_extra_ones() -> None:
    source = {"artist": "Goldfinger", "title": "Superman", "track": "01", "catalog_number": "XX-1"}
    output = {"artist": "Goldfinger", "title": "Superman"}

    assert transcode.missing_core_tags(source, output) == ["track"]


@pytest.mark.parametrize("quality", ["0", "0.5", "9"])
def test_validate_settings_accepts_a_libmp3lame_quality(quality: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcode, "VBR_QUALITY", quality)
    transcode.validate_settings()


@pytest.mark.parametrize("quality", ["", "v0", "10", "-1"])
def test_validate_settings_rejects_a_quality_ffmpeg_cannot_use(quality: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcode, "VBR_QUALITY", quality)

    with pytest.raises(transcode.TranscodeError, match="MEGABONK_MP3_VBR_QUALITY"):
        transcode.validate_settings()


def test_validate_settings_rejects_a_suffix_that_is_not_an_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(transcode, "OUTPUT_SUFFIX", "mp3")

    with pytest.raises(transcode.TranscodeError, match="MEGABONK_MP3_SUFFIX"):
        transcode.validate_settings()


def test_human_size_formats_bytes_upwards() -> None:
    assert transcode.human_size(512) == "512 B"
    assert transcode.human_size(6_363_292) == "6.1 MB"
    assert transcode.human_size(5 * 1024**3) == "5.0 GB"


def test_encode_writes_through_a_temporary_file_and_renames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "Song.flac"
    source.write_bytes(b"fLaC")
    calls: list[list[str]] = []

    def fake_run(argv: list[str]) -> str:
        calls.append(argv)
        Path(argv[-1]).write_bytes(b"ID3")
        return ""

    monkeypatch.setattr(transcode, "run_tool", fake_run)
    monkeypatch.setattr(transcode, "probe", lambda path: ({"tags": {"artist": "Goldfinger"}}, flac_streams()))

    target = tmp_path / "Song.mp3"
    transcode.encode(source, target, force=False)

    assert calls[0][-1] == str(tmp_path / ".Song.part.mp3")
    assert target.read_bytes() == b"ID3"
    assert list(tmp_path.glob(".Song.part*")) == []


def test_encode_warns_about_a_tag_the_mp3_lost(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "Song.flac"
    source.write_bytes(b"fLaC")

    def fake_run(argv: list[str]) -> str:
        Path(argv[-1]).write_bytes(b"ID3")
        return ""

    def fake_probe(path: Path) -> tuple[dict, list[dict]]:
        tags = {"artist": "Goldfinger"} if Path(path).name.startswith(".") else {"artist": "Goldfinger", "title": "Superman"}
        return {"tags": tags}, flac_streams()

    monkeypatch.setattr(transcode, "run_tool", fake_run)
    monkeypatch.setattr(transcode, "probe", fake_probe)

    transcode.encode(source, tmp_path / "Song.mp3", force=False)

    assert "tags not carried over: title" in capsys.readouterr().err


def test_encode_leaves_no_output_when_ffmpeg_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "Song.flac"
    source.write_bytes(b"fLaC")

    def fake_run(argv: list[str]) -> str:
        Path(argv[-1]).write_bytes(b"partial")
        raise transcode.TranscodeError("ffmpeg failed: bad thing")

    monkeypatch.setattr(transcode, "run_tool", fake_run)
    monkeypatch.setattr(transcode, "probe", lambda path: ({"tags": {}}, flac_streams()))

    target = tmp_path / "Song.mp3"
    with pytest.raises(transcode.TranscodeError):
        transcode.encode(source, target, force=False)

    assert not target.exists()
    assert list(tmp_path.glob(".Song.part*")) == []


def test_encode_refuses_an_existing_output_without_force(tmp_path: Path) -> None:
    source = tmp_path / "Song.flac"
    source.write_bytes(b"fLaC")
    target = tmp_path / "Song.mp3"
    target.write_bytes(b"keep me")

    with pytest.raises(transcode.TranscodeError, match="--force"):
        transcode.encode(source, target, force=False)

    assert target.read_bytes() == b"keep me"


def test_encode_rejects_a_file_without_an_audio_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("hello")
    monkeypatch.setattr(transcode, "probe", lambda path: ({"tags": {}}, [{"codec_type": "video"}]))

    with pytest.raises(transcode.TranscodeError, match="no audio stream"):
        transcode.encode(source, tmp_path / "notes.mp3", force=False)


def test_main_reports_errors_on_stderr_with_exit_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert transcode.main([str(tmp_path / "missing.flac")]) == 1
    assert "no such file" in capsys.readouterr().err


def test_main_rejects_a_bad_vbr_quality_before_calling_ffmpeg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "Song.flac"
    source.write_bytes(b"fLaC")
    monkeypatch.setattr(transcode, "VBR_QUALITY", "v0")

    def fail_run(argv: list[str]) -> str:
        raise AssertionError("ffmpeg must not run")

    monkeypatch.setattr(transcode, "run_tool", fail_run)

    assert transcode.main([str(source)]) == 1
    assert "MEGABONK_MP3_VBR_QUALITY" in capsys.readouterr().err


def test_main_transcodes_and_prints_the_tags_it_kept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "Goldfinger - Superman.flac"
    source.write_bytes(b"fLaC")
    monkeypatch.setattr(transcode, "VBR_QUALITY", "0")
    format_block = {
        "tags": {"ARTIST": "Goldfinger", "TITLE": "Superman", "encoder": "Lavf"},
        "bit_rate": "275000",
        "duration": "185",
    }

    def fake_run(argv: list[str]) -> str:
        Path(argv[-1]).write_bytes(b"x" * 2048)
        return ""

    monkeypatch.setattr(transcode, "run_tool", fake_run)
    monkeypatch.setattr(transcode, "probe", lambda path: (format_block, flac_streams()))

    assert transcode.main([str(source)]) == 0

    out = capsys.readouterr().out
    assert "-> " in out and "Goldfinger - Superman.mp3" in out
    assert "V0 VBR, 275 kb/s, 3:05, 2.0 KB" in out
    assert "artist=Goldfinger | title=Superman" in out
    assert "encoder" not in out
