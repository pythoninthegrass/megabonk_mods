"""Guest TLS block: image extraction and adapter generation rules."""

import elf_shim_probe as esp
import lift_abi as abi
import pytest
from types import SimpleNamespace


def elf_with(*segments):
    return SimpleNamespace(segments=list(segments))


def tls_segment(offset, filesz, memsz):
    return esp.Segment(7, 4, offset, 0x1000, filesz, memsz, 8)


def test_tls_image_is_initialised_data_then_zeroed_bss():
    raw = b"\x00" * 16 + bytes([1, 2, 3, 4]) + b"\xff" * 8
    assert abi.tls_image(elf_with(tls_segment(16, 4, 12)), raw) == bytes([1, 2, 3, 4]) + bytes(8)


def test_an_image_without_a_tls_segment_has_no_tls_image():
    assert abi.tls_image(elf_with(esp.Segment(1, 5, 0, 0, 8, 8, 8)), bytes(8)) is None


def test_two_tls_segments_are_rejected():
    segment = tls_segment(0, 4, 4)
    with pytest.raises(abi.AbiError, match="TLS"):
        abi.tls_image(elf_with(segment, segment), bytes(8))


def test_a_tls_segment_past_the_end_of_the_file_is_rejected():
    with pytest.raises(abi.AbiError, match="TLS"):
        abi.tls_image(elf_with(tls_segment(4, 8, 8)), bytes(8))


def test_tls_getter_may_not_share_an_address_with_another_binding():
    sig = abi.Signature((), "void")
    with pytest.raises(abi.AbiError, match="duplicate"):
        abi.generate([abi.Binding(0x1000, "entry", sig)], [], tls=abi.Tls(0x1000, bytes(16)))


def test_an_empty_tls_image_is_rejected():
    with pytest.raises(abi.AbiError, match="TLS"):
        abi.Tls(0x1000, b"")
