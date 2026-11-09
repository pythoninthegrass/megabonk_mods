#!/usr/bin/env -S uv run --script

# /// script
# requires-python = ">=3.13,<3.14"
# dependencies = ["python-decouple>=3.8"]
# ///

"""
Transcodes an audio file to MP3 V0 VBR, keeping the tags the source carried.

FFmpeg maps FLAC Vorbis comments (and APE/ID3 tags from other inputs) onto ID3v2.3
frames and writes an embedded cover as an APIC frame. `-q:a 0` on libmp3lame is LAME
`-V0`, the same V0 VBR target as the sox `-C -0.01` recipe used by
jparkinson1991/audio-transcoder; sox is not needed here and does not carry Vorbis
comments into MP3, so its tags would have to be copied separately.

Usage:
    uv run scripts/transcode.py <input> [output] [--force]

Args:
    input: Source audio file (anything FFmpeg reads: flac, wav, ogg, m4a, ...)
    output: Destination .mp3. Defaults to the input with a .mp3 extension, or to the
        input's name inside the given directory when a directory is supplied.

Note:
    An existing output is kept unless --force is passed. Encoding runs into a sibling
    temporary file that is renamed into place, so a failed run leaves no partial output.
    The encoder binaries, the VBR quality and the tag list checked after encoding are
    settings read through python-decouple; see .env.example for the MEGABONK_MP3_* and
    MEGABONK_FFMPEG keys.
"""

import argparse
import json
import shutil
import subprocess
import sys
from decouple import config
from pathlib import Path

# Every setting below is overridable via the environment or .env (env > .env > default).
FFMPEG = config("MEGABONK_FFMPEG", default="ffmpeg")
FFPROBE = config("MEGABONK_FFPROBE", default="ffprobe")
OUTPUT_SUFFIX = config("MEGABONK_MP3_SUFFIX", default=".mp3")
VBR_QUALITY = config("MEGABONK_MP3_VBR_QUALITY", default="0")  # libmp3lame VBR quality, 0 = LAME -V0
CORE_TAGS = config(
    "MEGABONK_MP3_CORE_TAGS",
    default="title,artist,album,album_artist,composer,date,year,track,disc,genre,lyricist",
)
MISSING_BINARY_HINT = "install FFmpeg (brew install ffmpeg)"


class TranscodeError(Exception):
    """A problem the user can act on; reported as `error: <message>` with exit 1."""


def parse_tag_list(value: str) -> list[str]:
    """Splits a comma-separated tag-name setting into lowercase names."""
    return [tag.strip().lower() for tag in value.split(",") if tag.strip()]


def validate_settings() -> None:
    """Rejects unusable settings before FFmpeg is invoked, naming the variable to fix."""
    if not OUTPUT_SUFFIX.startswith(".") or "/" in OUTPUT_SUFFIX:
        raise TranscodeError(f"MEGABONK_MP3_SUFFIX must be an extension like .mp3, got {OUTPUT_SUFFIX!r}")
    try:
        quality = float(VBR_QUALITY)
    except ValueError:
        raise TranscodeError(f"MEGABONK_MP3_VBR_QUALITY must be a number from 0 (best) to 9, got {VBR_QUALITY!r}") from None
    if not 0 <= quality <= 9:
        raise TranscodeError(f"MEGABONK_MP3_VBR_QUALITY must be from 0 (best) to 9, got {VBR_QUALITY!r}")


def run_tool(argv: list[str]) -> str:
    """Runs an FFmpeg-family command, returning stdout or raising TranscodeError."""
    if shutil.which(argv[0]) is None:
        raise TranscodeError(f"{argv[0]} not found on PATH: {MISSING_BINARY_HINT}")
    result = subprocess.run(argv, capture_output=True, text=True)
    if result.returncode != 0:
        lines = (result.stderr or result.stdout).strip().splitlines()
        raise TranscodeError(f"{argv[0]} failed: {lines[-1] if lines else f'exit code {result.returncode}'}")
    return result.stdout


def probe(path: Path) -> tuple[dict, list[dict]]:
    """Returns the format block (tags, duration, bit_rate) and stream list for path."""
    out = run_tool([FFPROBE, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)])
    data = json.loads(out or "{}")
    return data.get("format", {}), data.get("streams", [])


def first_attached_picture(streams: list[dict]) -> int | None:
    """Selector index for `-map 0:v:<n>` of the first cover-art stream, if any."""
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    for position, stream in enumerate(videos):
        if stream.get("disposition", {}).get("attached_pic") == 1:
            return position
    return None


def resolve_output(source: Path, output: str | None) -> Path:
    """Works out the .mp3 destination from the optional second argument."""
    if output is None:
        target = source.with_suffix(OUTPUT_SUFFIX)
    else:
        target = Path(output).expanduser()
        if target.is_dir():
            target = target / (source.stem + OUTPUT_SUFFIX)
        elif target.suffix == "":
            target = target.with_suffix(OUTPUT_SUFFIX)
        elif target.suffix.lower() != OUTPUT_SUFFIX.lower():
            raise TranscodeError(f"output must be a {OUTPUT_SUFFIX} file or a directory, got {target}")

    if target == source:
        raise TranscodeError(f"input is already {OUTPUT_SUFFIX}; pass an explicit output path")
    return target


def transcode_command(source: Path, target: Path, picture_index: int | None) -> list[str]:
    """Builds the FFmpeg command: first audio stream, cover art, LAME VBR, ID3v2.3."""
    picture_args = [] if picture_index is None else ["-map", f"0:v:{picture_index}", "-c:v", "copy"]
    return [
        FFMPEG,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-nostats",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        *picture_args,
        "-c:a",
        "libmp3lame",
        "-q:a",
        str(VBR_QUALITY),
        "-map_metadata",
        "0",
        "-id3v2_version",
        "3",
        str(target),
    ]


def missing_core_tags(source_tags: dict[str, str], output_tags: dict[str, str]) -> list[str]:
    """Core tags the source had that the MP3 lost; empty means nothing was dropped."""
    source_keys = {key.lower() for key in source_tags}
    output_keys = {key.lower() for key in output_tags}
    return [tag for tag in parse_tag_list(CORE_TAGS) if tag in source_keys and tag not in output_keys]


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.0f} B" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def encode(source: Path, target: Path, force: bool) -> tuple[dict, list[dict]]:
    """Encodes source into target through a temporary file; returns the output's format and streams."""
    if not source.is_file():
        raise TranscodeError(f"no such file: {source}")
    if target.exists() and not force:
        raise TranscodeError(f"{target} already exists; pass --force to overwrite")

    source_format, streams = probe(source)
    if not any(stream.get("codec_type") == "audio" for stream in streams):
        raise TranscodeError(f"no audio stream in {source}")

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.stem}.part{target.suffix}")  # keeps the .mp3 suffix: FFmpeg picks the muxer from it
    try:
        run_tool(transcode_command(source, temporary, first_attached_picture(streams)))
        output_format, output_streams = probe(temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)

    dropped = missing_core_tags(source_format.get("tags", {}), output_format.get("tags", {}))
    if dropped:
        print(f"warning: tags not carried over: {', '.join(dropped)}", file=sys.stderr)
    return output_format, output_streams


def report(source: Path, target: Path, output_format: dict, output_streams: list[dict]) -> None:
    """Prints what was written, its bitrate and length, and the tags it carries."""
    tags = {key.lower(): value for key, value in output_format.get("tags", {}).items() if key.lower() != "encoder"}
    summary = [f"{int(output_format['bit_rate']) // 1000} kb/s" if output_format.get("bit_rate") else ""]
    if output_format.get("duration"):
        seconds = int(float(output_format["duration"]))
        summary.append(f"{seconds // 60}:{seconds % 60:02d}")
    summary.append(human_size(target.stat().st_size))

    print(f"{source} -> {target} (V{VBR_QUALITY} VBR{', ' + ', '.join(part for part in summary if part)})")
    if tags:
        print("  tags: " + " | ".join(f"{key}={value}" for key, value in tags.items()))
    if any(stream.get("codec_type") == "video" for stream in output_streams):
        print("  cover art: copied")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="transcode",
        description="Transcode an audio file to MP3 V0 VBR, keeping its tags.",
        epilog="example: uv run scripts/transcode.py 'tools/Goldfinger - Superman.flac'",
    )
    parser.add_argument("input", help="source audio file")
    parser.add_argument("output", nargs="?", help="destination .mp3 (default: the input with a .mp3 extension)")
    parser.add_argument("-f", "--force", action="store_true", help="overwrite an existing output")
    args = parser.parse_args(argv)

    try:
        source = Path(args.input).expanduser()
        validate_settings()
        target = resolve_output(source, args.output)
        output_format, output_streams = encode(source, target, args.force)
        report(source, target, output_format, output_streams)
    except TranscodeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
