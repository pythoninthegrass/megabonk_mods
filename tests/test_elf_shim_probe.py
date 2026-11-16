"""Tests for the ELF-load-and-shim spike driver.

The driver reads the shipped Linux GameAssembly.so, asks the real macOS loader what a
host could resolve, and scores four legs: import shim feasibility, glibc version-node
binding, relocation translatability, and the load strategy. Nothing launches the
runtime, so the whole contract is testable without a game process.
"""

import json
import pytest
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import elf_shim_probe as esp

SHIPPED_SO = esp.REPO / ".tools/megabonk-linux-native/Megabonk/GameAssembly.so"
requires_shipped_so = pytest.mark.skipif(
    not SHIPPED_SO.exists(), reason=f"shipped Linux runtime absent at {SHIPPED_SO}"
)
# The import legs ask the live macOS loader what it can resolve, so they can only be
# scored on macOS with a compiler present.
requires_loader = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("cc") is None,
    reason="the import legs need the macOS loader and a C compiler",
)


def sym(name, *, bind=1, shndx=0, version=0):
    return esp.Dynsym(name, bind, 2, shndx, version)


def rela(offset, type_name, sym_index=0, addend=0, section=".rela.dyn"):
    number = {v: k for k, v in esp.R_X86_64_NAMES.items()}[type_name]
    return esp.Rela(offset, number, sym_index, addend, section)


def seg(type_, flags, offset, vaddr, filesz, memsz, align=0x1000):
    return esp.Segment(type_, flags, offset, vaddr, filesz, memsz, align)


def make_elf(
    *,
    undefined=(),
    defined=(),
    relocs=(),
    verneed=None,
    segments=None,
    dynamic=None,
    sections=None,
    e_type=esp.ET_DYN,
    machine=esp.EM_X86_64,
    soname="GameAssembly.so",
):
    """Build an Elf record directly; the legs read these fields and nothing else.

    Symbol index 0 is the null entry, as in a real .dynsym, so a relocation naming
    index 1 points at the first name in ``undefined``.
    """
    dynsyms = [esp.Dynsym("", 0, 0, 0, 0)]
    dynsyms += [sym(n) for n in undefined]
    dynsyms += [sym(n, shndx=20) for n in defined]
    return esp.Elf(
        path=Path("/tmp/GameAssembly.so"),
        e_type=e_type,
        machine=machine,
        entry=0x1000,
        sections=sections or [],
        segments=segments
        or [
            seg(esp.PT_LOAD, 4, 0, 0, 0x1000, 0x1000),
            seg(esp.PT_LOAD, 5, 0x1000, 0x1000, 0x1000, 0x1000),
            seg(esp.PT_LOAD, 6, 0x2000, 0x2000, 0x1000, 0x1000),
            seg(esp.PT_TLS, 4, 0x2000, 0x2000, 0, 16),
            seg(esp.PT_DYNAMIC, 6, 0x3000, 0x3000, 0x100, 0x100),
        ],
        dynamic=dynamic or {},
        dynamic_list={"NEEDED": [1, 2]},
        dynsyms=dynsyms,
        relocs=list(relocs),
        verneed=verneed or {},
        soname=soname,
    )


def resolved_none(names):
    return {n: {"addr": None, "source": "none"} for n in names}


def resolved_default(*names):
    return {n: {"addr": "0x1000", "source": "default"} for n in names}


class TestElfReaderRejections:
    def test_a_non_elf_file_is_refused(self, tmp_path):
        p = tmp_path / "notelf.so"
        p.write_bytes(b"Cafebabe" * 64)
        with pytest.raises(esp.ElfError, match="not an ELF"):
            esp.parse_elf(p)

    def test_a_32_bit_elf_is_refused(self, tmp_path):
        p = tmp_path / "elf32.so"
        p.write_bytes(b"\x7fELF" + bytes([1, 1]) + bytes(60))
        with pytest.raises(esp.ElfError, match="64-bit"):
            esp.parse_elf(p)

    def test_a_big_endian_elf_is_refused(self, tmp_path):
        p = tmp_path / "be.so"
        p.write_bytes(b"\x7fELF" + bytes([2, 2]) + bytes(60))
        with pytest.raises(esp.ElfError, match="64-bit little-endian"):
            esp.parse_elf(p)


class TestProbeMacOsLoader:
    def test_parses_the_three_field_contract(self, monkeypatch):
        def fake_run(cmd, capture_output, text, check):
            assert cmd[0] == "/tmp/symprobe"
            return subprocess.CompletedProcess(
                cmd, 0, "malloc\t0x100\tdefault\ngettext\t0x0\tnone\n", ""
            )

        monkeypatch.setattr(esp.subprocess, "run", fake_run)
        out = esp.probe_macos_loader(Path("/tmp/symprobe"), ["malloc", "gettext"])
        assert out["malloc"] == {"addr": "0x100", "source": "default"}
        assert out["gettext"] == {"addr": None, "source": "none"}

    def test_recipe_libraries_are_passed_as_double_dash_lib_pairs(self, monkeypatch):
        seen = {}

        def fake_run(cmd, capture_output, text, check):
            seen["cmd"] = list(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        monkeypatch.setattr(esp.subprocess, "run", fake_run)
        esp.probe_macos_loader(
            Path("/tmp/symprobe"), ["iconv_open"], ("/usr/lib/libiconv.2.dylib",)
        )
        cmd = seen["cmd"]
        assert cmd[1:4] == ["--lib", "/usr/lib/libiconv.2.dylib", "iconv_open"]

    def test_a_zero_address_counts_as_absent(self, monkeypatch):
        monkeypatch.setattr(
            esp.subprocess,
            "run",
            lambda *a, **k: subprocess.CompletedProcess(a[0], 0, "foo\t0x0\tdefault\n", ""),
        )
        assert esp.probe_macos_loader(Path("/x"), ["foo"])["foo"]["addr"] is None

    def test_no_names_does_not_invoke_the_probe(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("must not spawn the probe for an empty batch")

        monkeypatch.setattr(esp.subprocess, "run", boom)
        assert esp.probe_macos_loader(Path("/x"), []) == {}


class TestSymprobeSourceHonesty:
    SOURCE = esp.SYMPROBE_SOURCE

    def test_the_source_exists_and_is_compiled_by_the_driver(self):
        assert self.SOURCE.exists()
        assert "symprobe.c" in str(self.SOURCE)

    def test_default_scope_lookups_happen_before_any_dlopen(self):
        """A dlopen pollutes the global scope, so the baseline has to precede it."""
        body = self.SOURCE.read_text()
        assert body.index("dlsym(") < body.index("dlopen(")
        assert body.count("dlsym(") >= 4

    def test_both_underscore_spellings_are_tried(self):
        body = self.SOURCE.read_text()
        assert '"_%s"' in body

    def test_unresolved_names_report_none_as_the_source(self):
        assert '"none"' in self.SOURCE.read_text()


class TestClassification:
    def test_a_loader_resolved_name_is_free(self):
        elf = make_elf(undefined=["malloc"], relocs=[rela(0x10, "JUMP_SLOT", 1)])
        cls = esp.classify(elf, {"malloc": {"addr": "0x1", "source": "default"}})
        assert cls["buckets"]["system"] == ["malloc"]
        assert cls["bucket_counts"]["unclassified"] == 0

    def test_an_unnamed_import_without_a_rule_fails_the_table(self):
        elf = make_elf(undefined=["weird_linux_only_call"],
                       relocs=[rela(8, "GLOB_DAT", 1)])
        cls = esp.classify(elf, resolved_none(["weird_linux_only_call"]))
        assert cls["buckets"]["unclassified"] == ["weird_linux_only_call"]
        assert cls["live_unclassified"] == ["weird_linux_only_call"]

    def test_only_relocations_make_an_import_live(self):
        elf = make_elf(undefined=["weird_linux_only_call"], relocs=[])
        cls = esp.classify(elf, resolved_none(["weird_linux_only_call"]))
        assert cls["live_unclassified"] == []
        assert cls["dead_unclassified"] == ["weird_linux_only_call"]

    def test_a_defined_symbol_reference_does_not_count_as_an_import(self):
        elf = make_elf(
            undefined=["malloc"], defined=["SomeLocal"], relocs=[rela(0x10, "64", 2)]
        )
        cls = esp.classify(elf, resolved_default("malloc"))
        assert cls["referenced_by_reloc"] == 0

    def test_a_64_bit_suffix_name_is_an_alias_not_a_shim(self):
        elf = make_elf(undefined=["open64"])
        cls = esp.classify(elf, resolved_none(["open64"]))
        assert cls["buckets"]["alias"] == ["open64"]

    def test_the_glibc_underscored_locale_spelling_is_a_locale_alias(self):
        elf = make_elf(undefined=["__strcoll_l"])
        cls = esp.classify(elf, resolved_none(["__strcoll_l"]))
        assert cls["buckets"]["locale-alias"] == ["__strcoll_l"]

    def test_a_transactional_memory_hook_is_an_optional_stub(self):
        elf = make_elf(undefined=["_ITM_RU1"])
        cls = esp.classify(elf, resolved_none(["_ITM_RU1"]))
        assert cls["buckets"]["weak-noop"] == ["_ITM_RU1"]

    def test_the_tls_accessor_is_loader_owned(self):
        elf = make_elf(undefined=["__tls_get_addr"])
        cls = esp.classify(elf, resolved_none(["__tls_get_addr"]))
        assert cls["buckets"]["loader-owned"] == ["__tls_get_addr"]

    def test_the_stat_family_needs_a_struct_translating_trampoline(self):
        elf = make_elf(undefined=["__xstat64", "__fxstat64", "__lxstat64"])
        cls = esp.classify(elf, resolved_none(["__xstat64", "__fxstat64", "__lxstat64"]))
        assert sorted(cls["buckets"]["compat-required"]) == [
            "__fxstat64", "__lxstat64", "__xstat64"
        ]

    def test_a_recipe_library_that_lacks_the_symbol_is_a_blocker(self):
        """The compat table may not claim a library that does not actually export it."""
        elf = make_elf(undefined=["iconv_open"], relocs=[rela(8, "GLOB_DAT", 1)])
        cls = esp.classify(elf, resolved_none(["iconv_open"]))
        assert cls["live_unclassified"] == ["iconv_open"]
        assert "libiconv" in cls["detail"]["iconv_open"]["why"]

    def test_a_recipe_library_that_does_export_the_symbol_is_accepted(self):
        elf = make_elf(undefined=["iconv_open"], relocs=[rela(8, "GLOB_DAT", 1)])
        hit = {"iconv_open": {"addr": "0x9", "source": esp.COMPAT_LIBS["iconv_open"]}}
        cls = esp.classify(elf, hit)
        assert cls["buckets"]["compat-required"] == ["iconv_open"]
        assert cls["live_unclassified"] == []
        assert cls["detail"]["iconv_open"]["live"] is True

    def test_an_unconsulted_loader_leaves_imports_unscored_not_failed(self):
        """A loader-free analysis must say it did not verify, not claim a failure."""
        elf = make_elf(undefined=["iconv_open"])
        cls = esp.classify(elf, resolved_none(["iconv_open"]), loader_probed=False)
        assert cls["live_unclassified"] == []
        assert cls["unconsulted_recipes"] == ["iconv_open"]
        assert "not consulted" in cls["detail"]["iconv_open"]["why"]

    def test_an_unscored_import_without_a_rule_lands_in_not_probed(self):
        elf = make_elf(undefined=["mystery"], relocs=[rela(8, "JUMP_SLOT", 1)])
        cls = esp.classify(elf, resolved_none(["mystery"]), loader_probed=False)
        assert cls["buckets"]["not-probed"] == ["mystery"]
        assert cls["live_not_probed"] == ["mystery"]
        leg = esp.leg_imports(elf, cls)
        assert leg["pass"] is False
        assert any("run without --skip-dyld-probe" in b for b in leg["blockers"])

    def test_an_entry_listed_as_impossible_is_a_blocker_even_when_resolvable(self):
        elf = make_elf(undefined=["syscall"], relocs=[rela(8, "GLOB_DAT", 1)])
        esp.UNIMPLEMENTABLE["syscall"] = "no Linux syscall number space on macOS"
        try:
            cls = esp.classify(elf, resolved_default("syscall"))
            assert cls["live_unclassified"] == ["syscall"]
        finally:
            del esp.UNIMPLEMENTABLE["syscall"]

    def test_underscore_only_resolution_is_counted_separately(self):
        elf = make_elf(undefined=["malloc"])
        cls = esp.classify(
            elf, {"malloc": {"addr": "0x1", "source": "underscore"}}
        )
        assert cls["resolved_by_underscore_only"] == 1
        assert cls["resolved_by_loader"] == 1

    def test_weak_entries_are_counted_apart_from_global_ones(self):
        elf = esp.Elf(
            path=Path("/tmp/x.so"), e_type=esp.ET_DYN, machine=esp.EM_X86_64, entry=0,
            sections=[], segments=[], dynamic={}, dynamic_list={},
            dynsyms=[sym("malloc", bind=1), sym("_ITM_RU1", bind=2)],
            relocs=[], verneed={}, soname="",
        )
        cls = esp.classify(elf, resolved_default("malloc"))
        assert cls["weak_entries"] == 1
        assert cls["undefined_unique"] == 2


class TestCuratedTables:
    def test_every_recipe_library_key_is_a_compat_entry(self):
        assert set(esp.COMPAT_LIBS) <= set(esp.COMPAT_REQUIRED)

    def test_the_tables_do_not_disagree_about_a_symbol(self):
        groups = {
            "alias": set(esp.ALIAS_SYMBOLS),
            "locale": set(esp.LOCALE_ALIAS_SYMBOLS),
            "compat": set(esp.COMPAT_REQUIRED),
            "abi": set(esp.ABI_DIVERGENT),
            "loader": set(esp.LOADER_OWNED),
            "weak": set(esp.WEAK_NOOP),
            "math": set(esp.MATH_SYMBOLS),
        }
        names = list(groups)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                assert not (groups[a] & groups[b]), f"{a} and {b} both claim {groups[a] & groups[b]}"

    def test_alias_targets_are_plain_c_names(self):
        for src, target in esp.ALIAS_SYMBOLS.items():
            assert target.replace("_", "").isalnum(), target
            assert not target.startswith("__"), src

    def test_every_compat_entry_says_what_the_shim_does(self):
        for name, why in esp.COMPAT_REQUIRED.items():
            assert len(why) > 20, name

    def test_every_relocation_type_with_a_handler_names_a_strategy(self):
        for name, strategy in esp.RELOC_HANDLERS.items():
            assert name in esp.R_X86_64_NAMES.values(), name
            assert len(strategy) > 10


class TestLeg1Imports:
    def test_all_named_answers_pass(self):
        elf = make_elf(undefined=["malloc", "open64"], relocs=[rela(8, "JUMP_SLOT", 1)])
        cls = esp.classify(elf, {**resolved_default("malloc"), **resolved_none(["open64"])})
        leg = esp.leg_imports(elf, cls)
        assert leg["pass"] is True
        assert leg["metrics"]["shim_work_symbols"] == 1
        assert leg["metrics"]["free_symbols"] == 1

    def test_a_live_unclassified_import_fails_and_names_it(self):
        elf = make_elf(undefined=["mystery"], relocs=[rela(8, "GLOB_DAT", 1)])
        cls = esp.classify(elf, resolved_none(["mystery"]))
        leg = esp.leg_imports(elf, cls)
        assert leg["pass"] is False
        assert leg["blockers"] == ["mystery"]

    def test_a_dead_unclassified_import_does_not_block_the_route(self):
        elf = make_elf(undefined=["mystery"])
        cls = esp.classify(elf, resolved_none(["mystery"]))
        leg = esp.leg_imports(elf, cls)
        assert leg["pass"] is True
        assert leg["dead_but_unclassified"] == ["mystery"]

    def test_a_non_dynamically_loaded_object_fails_the_leg(self):
        elf = make_elf(e_type=2)
        cls = esp.classify(elf, {})
        assert esp.leg_imports(elf, cls)["checks"]["e_type_is_dynamically_loaded"] is False

    def test_the_wrong_machine_fails_the_leg(self):
        elf = make_elf(machine=183)
        cls = esp.classify(elf, {})
        assert esp.leg_imports(elf, cls)["pass"] is False


class TestLeg2AbiNodes:
    def test_version_binding_alone_is_not_an_obstacle(self):
        elf = make_elf(
            undefined=["memcpy"], verneed={3: "GLIBC_2.14"},
            relocs=[rela(8, "JUMP_SLOT", 1)],
        )
        elf.dynsyms[1] = esp.Dynsym("memcpy", 1, 2, 0, 3)
        cls = esp.classify(elf, resolved_default("memcpy"))
        leg = esp.leg_abi_nodes(elf, cls)
        assert leg["pass"] is True
        assert leg["metrics"]["live_bound_to_a_node"] == 1

    def test_a_live_import_stranded_on_a_version_node_fails(self):
        elf = make_elf(undefined=["mystery"], verneed={3: "GLIBC_2.17"},
                       relocs=[rela(8, "JUMP_SLOT", 1)])
        elf.dynsyms[1] = esp.Dynsym("mystery", 1, 2, 0, 3)
        cls = esp.classify(elf, resolved_none(["mystery"]))
        leg = esp.leg_abi_nodes(elf, cls)
        assert leg["pass"] is False
        assert leg["blockers"] == ["mystery@GLIBC_2.17"]

    def test_an_absent_version_table_fails_the_recorded_check(self):
        elf = make_elf()
        leg = esp.leg_abi_nodes(elf, esp.classify(elf, {}))
        assert leg["checks"]["version_nodes_recorded"] is False

    def test_an_executable_stack_is_reported_not_assumed(self):
        segments = [seg(esp.PT_LOAD, 4, 0, 0, 0x1000, 0x1000),
                    seg(esp.PT_GNU_STACK, 7, 0, 0, 0, 0)]
        elf = make_elf(segments=segments)
        leg = esp.leg_abi_nodes(elf, esp.classify(elf, {}))
        assert leg["metrics"]["gnu_stack_executable"] is True


class TestLeg3Relocs:
    def test_classified_types_with_no_copy_relocs_pass(self):
        elf = make_elf(relocs=[rela(8, "RELATIVE", 0, 0x100), rela(16, "JUMP_SLOT", 1)],
                       undefined=["malloc"])
        leg = esp.leg_relocs(elf, esp.classify(elf, resolved_default("malloc")))
        assert leg["pass"] is True
        assert leg["metrics"]["by_type"]["RELATIVE"] == 1

    def test_a_copy_relocation_is_a_blocker(self):
        elf = make_elf(relocs=[rela(8, "COPY", 1)], undefined=["malloc"])
        leg = esp.leg_relocs(elf, esp.classify(elf, resolved_default("malloc")))
        assert leg["pass"] is False
        assert any("COPY" in b for b in leg["blockers"])

    def test_an_unknown_relocation_type_is_a_blocker(self):
        elf = esp.Elf(
            path=Path("/tmp/x.so"), e_type=esp.ET_DYN, machine=esp.EM_X86_64, entry=0,
            sections=[], segments=[], dynamic={}, dynamic_list={}, dynsyms=[],
            relocs=[esp.Rela(8, 4096, 0, 0, ".rela.dyn")], verneed={}, soname="",
        )
        leg = esp.leg_relocs(elf, esp.classify(elf, {}))
        assert leg["pass"] is False
        assert any("UNKNOWN_4096" in b for b in leg["blockers"])

    def test_a_reloc_referencing_an_unclassified_import_fails(self):
        elf = make_elf(undefined=["mystery"], relocs=[rela(8, "GLOB_DAT", 1)])
        cls = esp.classify(elf, resolved_none(["mystery"]))
        leg = esp.leg_relocs(elf, cls)
        assert leg["checks"]["every_referenced_import_is_classified"] is False

    def test_the_tls_types_the_shim_must_handle_have_strategies(self):
        for t in ("DTPMOD64", "DTPOFF64", "TPOFF64", "TLSGD", "TLSLD", "GOTTPOFF"):
            assert t in esp.RELOC_HANDLERS


class TestLeg4LoadStrategy:
    def test_the_default_target_maps_the_segments_directly(self):
        elf = make_elf()
        leg = esp.leg_load_strategy(elf, esp.classify(elf, {}), esp.leg_relocs(elf, esp.classify(elf, {})))
        assert leg["pass"] is True
        assert leg["strategy"].startswith("map the PT_LOAD segments")

    def test_a_target_page_beyond_the_alignment_still_maps_by_copying(self):
        segments = [seg(esp.PT_LOAD, 4, 0, 0, 0x1000, 0x1000, align=0x1000)]
        elf = make_elf(segments=segments + [seg(esp.PT_TLS, 4, 0, 0, 0, 16)])
        reloc_leg = esp.leg_relocs(elf, esp.classify(elf, {}))
        leg = esp.leg_load_strategy(elf, esp.classify(elf, {}), reloc_leg, "arm64")
        assert leg["metrics"]["target_page_size"] == 16384

    def test_incongruent_segments_are_a_blocker(self):
        segments = [seg(esp.PT_LOAD, 4, 0x100, 0, 0x1000, 0x1000)]
        elf = make_elf(segments=segments + [seg(esp.PT_TLS, 4, 0, 0, 0, 16)])
        leg = esp.leg_load_strategy(
            elf, esp.classify(elf, {}), esp.leg_relocs(elf, esp.classify(elf, {})), "x86_64"
        )
        assert leg["checks"]["segments_are_mappable_without_copying"] is False
        assert any("copied into anonymous pages" in b for b in leg["blockers"])

    def test_irelative_relocations_are_reported_as_a_bootstrap_ordering_blocker(self):
        elf = make_elf(relocs=[rela(8, "IRELATIVE", 0, 0x40)])
        cls = esp.classify(elf, {})
        leg = esp.leg_load_strategy(elf, cls, esp.leg_relocs(elf, cls))
        assert leg["metrics"]["irelative_relocs"] == 1
        assert any("IRELATIVE" in b for b in leg["blockers"])

    def test_an_oversized_tls_segment_is_a_blocker(self):
        elf = make_elf(segments=[seg(esp.PT_LOAD, 4, 0, 0, 0x1000, 0x1000),
                                 seg(esp.PT_TLS, 4, 0, 0, 0, 0x8000)])
        cls = esp.classify(elf, {})
        leg = esp.leg_load_strategy(elf, cls, esp.leg_relocs(elf, cls))
        assert leg["pass"] is False
        assert any("PT_TLS" in b for b in leg["blockers"])

    def test_a_non_position_independent_object_picks_the_dylib_strategy(self):
        elf = make_elf(e_type=2)
        cls = esp.classify(elf, {})
        leg = esp.leg_load_strategy(elf, cls, esp.leg_relocs(elf, cls))
        assert leg["strategy"] == "translate to a Mach-O dylib and dlopen"

    def test_il2cpp_exports_are_counted_for_the_translation_contract(self):
        elf = make_elf(defined=["il2cpp_string_chars", "il2cpp_domain_get", "other"])
        cls = esp.classify(elf, {})
        leg = esp.leg_load_strategy(elf, cls, esp.leg_relocs(elf, cls))
        assert leg["metrics"]["exported_il2cpp_symbols"] == 2

    def test_page_sizes_cover_both_apple_targets(self):
        assert esp.PAGE_SIZE_BY_ARCH == {"x86_64": 4096, "arm64": 16384}


@pytest.fixture(scope="module")
def analysis_report(tmp_path_factory):
    """ELF-level facts only: the import legs cannot be scored without the loader."""
    return esp.run_probe(SHIPPED_SO, tmp_path_factory.mktemp("elf-shim-analysis"),
                         skip_dyld=True)


@pytest.fixture(scope="module")
def scored_report(tmp_path_factory):
    return esp.run_probe(SHIPPED_SO, tmp_path_factory.mktemp("elf-shim-scored"))


@requires_shipped_so
class TestShippedRuntimeAnalysisOnly:
    """Structural anchors that hold on any platform, with the loader left out."""

    def test_the_relocation_census_is_the_measured_shape(self, analysis_report):
        metrics = analysis_report["legs"]["leg3_relocs"]["metrics"]
        assert metrics["total"] == 470466
        assert set(metrics["by_type"]) == {"64", "DTPMOD64", "GLOB_DAT", "JUMP_SLOT", "RELATIVE"}

    def test_the_import_count_matches_the_measured_binary(self, analysis_report):
        assert analysis_report["classification"]["undefined_unique"] == 303

    def test_the_binary_exports_the_il2cpp_surface_a_translation_must_keep(self, analysis_report):
        metrics = analysis_report["legs"]["leg4_load_strategy"]["metrics"]
        assert metrics["exported_il2cpp_symbols"] == 240
        assert metrics["code_bytes"] == 51_319_793

    def test_the_glibc_nodes_the_binary_binds_are_all_recorded(self, analysis_report):
        nodes = analysis_report["legs"]["leg2_abi_nodes"]["metrics"]["node_names"]
        assert {"GLIBC_2.2.5", "GLIBC_2.17", "GCC_4.2.0"} <= set(nodes)

    def test_the_relocation_and_strategy_legs_still_score(self, analysis_report):
        assert analysis_report["legs"]["leg3_relocs"]["pass"] is True
        assert analysis_report["legs"]["leg4_load_strategy"]["pass"] is True

    def test_the_loader_free_run_is_marked_as_such(self, analysis_report):
        assert analysis_report["dyld_probe"] == "skipped"
        assert analysis_report["legs"]["leg1_imports"]["metrics"]["loader_probed"] is False

    def test_an_unscored_run_never_claims_the_route_is_feasible(self, analysis_report):
        assert analysis_report["pass"] is False
        assert "not-scored" in analysis_report["conclusion"]


@requires_shipped_so
@requires_loader
class TestShippedRuntimeScored:
    """The route decision itself, measured against the live macOS loader."""

    def test_every_leg_passes(self, scored_report):
        assert scored_report["failed_legs"] == [], scored_report["failed_legs"]
        assert scored_report["conclusion"] == "elf-load-and-shim=feasible"

    def test_no_import_is_left_without_a_named_answer(self, scored_report):
        assert scored_report["classification"]["bucket_counts"]["unclassified"] == 0

    def test_the_free_and_shimmed_split_matches_the_measurement(self, scored_report):
        metrics = scored_report["legs"]["leg1_imports"]["metrics"]
        assert metrics["free_symbols"] == 221
        assert metrics["shim_work_symbols"] == 66
        assert metrics["referenced_by_reloc"] == 303

    def test_dyld_accepts_the_unadorned_elf_name(self, scored_report):
        metrics = scored_report["legs"]["leg1_imports"]["metrics"]
        assert metrics["resolved_by_underscore_only"] == 0
        assert metrics["resolved_by_loader"] == 247

    def test_the_iconv_recipe_is_proven_against_the_real_library(self, scored_report):
        detail = scored_report["classification"]["detail"]["iconv_open"]
        assert detail["bucket"] == "compat-required"
        assert detail["source"] == esp.COMPAT_LIBS["iconv_open"]

    def test_the_version_nodes_are_bound_but_not_stranding(self, scored_report):
        leg = scored_report["legs"]["leg2_abi_nodes"]
        assert leg["metrics"]["live_bound_to_a_node"] > 0
        assert leg["blockers"] == []


@requires_shipped_so
class TestCommandLine:
    def test_a_run_writes_the_artifact(self, tmp_path, capsys):
        code = esp.main(["--so", str(SHIPPED_SO), "--out", str(tmp_path), "--skip-dyld-probe"])
        assert code == 1  # not-scored is a non-zero, non-crashing outcome
        payload = json.loads((tmp_path / "summary.json").read_text())
        assert payload["legs"]["leg3_relocs"]["pass"] is True
        assert "not-scored" in capsys.readouterr().out

    @requires_loader
    def test_a_scored_run_reports_zero(self, tmp_path, capsys):
        code = esp.main(["--so", str(SHIPPED_SO), "--out", str(tmp_path)])
        assert code == 0
        assert "elf-load-and-shim=feasible" in capsys.readouterr().out

    def test_a_missing_binary_exits_two_without_a_traceback(self, tmp_path, capsys):
        code = esp.main(["--so", str(tmp_path / "absent.so"), "--out", str(tmp_path)])
        assert code == 2
        assert "no such ELF" in capsys.readouterr().err

    def test_the_target_arch_is_recorded_in_the_artifact(self, tmp_path):
        esp.main(["--so", str(SHIPPED_SO), "--out", str(tmp_path), "--skip-dyld-probe",
                  "--target-arch", "arm64"])
        payload = json.loads((tmp_path / "summary.json").read_text())
        assert payload["target_arch"] == "arm64"
        assert payload["legs"]["leg4_load_strategy"]["metrics"]["target_page_size"] == 16384
