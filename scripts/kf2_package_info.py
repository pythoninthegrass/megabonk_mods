#!/usr/bin/env python3
import argparse
import struct
from dataclasses import dataclass
from pathlib import Path

PACKAGE_TAG = 0x9E2A83C1
PKG_COOKED = 0x8
FIXED_PREFIX = struct.Struct("<IHHi")
TABLES = struct.Struct("<I6i")
NAME_FLAGS = struct.Struct("<Q")
IMPORT_ENTRY = struct.Struct("<2i2ii2i")


@dataclass(frozen=True)
class PackageHeader:
    file_version: int
    licensee_version: int
    header_size: int
    folder: str
    package_flags: int
    name_count: int
    name_offset: int
    export_count: int
    export_offset: int
    import_count: int
    import_offset: int

    @property
    def cooked(self) -> bool:
        return bool(self.package_flags & PKG_COOKED)


def read_header(data: bytes) -> PackageHeader:
    if len(data) < FIXED_PREFIX.size + 4:
        raise ValueError("truncated Unreal package header")
    tag, file_version, licensee_version, header_size = FIXED_PREFIX.unpack_from(data)
    if tag != PACKAGE_TAG:
        raise ValueError(f"not an Unreal package (tag {tag:#010x})")
    offset = FIXED_PREFIX.size
    (folder_length,) = struct.unpack_from("<i", data, offset)
    offset += 4
    width = 2 if folder_length < 0 else 1
    folder_bytes = abs(folder_length) * width
    if len(data) < offset + folder_bytes + TABLES.size:
        raise ValueError("truncated Unreal package header")
    folder = data[offset : offset + folder_bytes].decode("utf-16-le" if width == 2 else "latin-1").rstrip("\0")
    offset += folder_bytes
    flags, *counts = TABLES.unpack_from(data, offset)
    return PackageHeader(file_version, licensee_version, header_size, folder, flags, *counts)


def read_names(data: bytes, header: PackageHeader) -> list[str]:
    names = []
    offset = header.name_offset
    for _ in range(header.name_count):
        if len(data) < offset + 4:
            raise ValueError("truncated Unreal package name table")
        (length,) = struct.unpack_from("<i", data, offset)
        offset += 4
        width = 2 if length < 0 else 1
        size = abs(length) * width
        if len(data) < offset + size + NAME_FLAGS.size:
            raise ValueError("truncated Unreal package name table")
        names.append(data[offset : offset + size].decode("utf-16-le" if width == 2 else "latin-1").rstrip("\0"))
        offset += size + NAME_FLAGS.size
    return names


def import_packages(data: bytes, header: PackageHeader) -> list[str]:
    names = read_names(data, header)
    packages = set()
    for index in range(header.import_count):
        offset = header.import_offset + index * IMPORT_ENTRY.size
        if len(data) < offset + IMPORT_ENTRY.size:
            raise ValueError("truncated Unreal package import table")
        _, _, class_name, _, outer, object_name, _ = IMPORT_ENTRY.unpack_from(data, offset)
        if outer == 0 and names[class_name] == "Package":
            packages.add(names[object_name])
    return sorted(packages)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print the header of an Unreal Engine 3 package.")
    parser.add_argument("package", type=Path)
    parser.add_argument("--imports", action="store_true", help="list the packages the map imports from")
    args = parser.parse_args()
    with args.package.open("rb") as handle:
        header = read_header(handle.read(4096))
        handle.seek(0)
        data = handle.read(header.header_size) if args.imports else b""
    for name, value in vars(header).items():
        print(f"{name}: {value:#x}" if name == "package_flags" else f"{name}: {value}")
    print(f"cooked: {header.cooked}")
    if args.imports:
        print("imported packages:")
        for package in import_packages(data, header):
            print(f"  {package}")


if __name__ == "__main__":
    main()
