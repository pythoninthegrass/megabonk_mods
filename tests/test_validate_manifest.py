import json
import pytest
import validate_thunderstore_manifest as vtm
import zipfile
from pathlib import Path
from validate_thunderstore_manifest import online_problems, serializer_problems, validate_manifest_bytes

ROOT = Path(__file__).resolve().parents[1]
TEAM = "pythoninthegrass"
DEP = ("BepInEx", "BepInExPack_IL2CPP", "6.0.788")
REPO_MANIFEST = ROOT / "pkg" / "manifest.json"
REPO_CONFIG = ROOT / "thunderstore.toml"

# A manifest the site accepts, so the characterization suite stands on its own.
BASELINE = {
    "name": "Megabonk_Level_Editor",
    "version_number": "0.0.1",
    "website_url": "https://megabonkmod.party",
    "description": "Play and build custom Megabonk levels with an in-game map editor, custom music and a drop-down console.",
    "dependencies": ["BepInEx-BepInExPack_IL2CPP-6.0.788"],
}

needs_repo_manifest = pytest.mark.skipif(not REPO_MANIFEST.exists(), reason="pkg/manifest.json is not committed yet")
needs_team_config = pytest.mark.skipif(not REPO_CONFIG.exists(), reason="thunderstore.toml is not committed yet")


def manifest(**changes):
    document = json.loads(json.dumps(BASELINE))
    for key, value in changes.items():
        if value is Ellipsis:
            del document[key]
        else:
            document[key] = value
    return document


def check(**changes) -> list[str]:
    return validate_manifest_bytes(json.dumps(manifest(**changes)).encode("utf-8"), namespace=TEAM)


def problems(document, team: str = TEAM) -> list[str]:
    return validate_manifest_bytes(json.dumps(document).encode("utf-8"), namespace=team)


@needs_repo_manifest
def test_repo_manifest_is_valid():
    assert validate_manifest_bytes(REPO_MANIFEST.read_bytes(), namespace=TEAM) == []


def test_tcli_extra_identity_keys_are_ignored():
    data = json.dumps({**manifest(), "namespace": TEAM, "FullName": f"{TEAM}-Megabonk_Level_Editor"}).encode()
    assert validate_manifest_bytes(data, namespace=TEAM) == []


@pytest.mark.parametrize("field", ("name", "version_number", "website_url", "description", "dependencies"))
def test_missing_required_field(field):
    assert check(**{field: Ellipsis}) == [f"manifest.json {field}: This field is required."]


@pytest.mark.parametrize("field", ("description", "website_url"))
@pytest.mark.parametrize("value", (42, 42.432, False, True))
def test_number_in_char_field_fails(field, value):
    assert check(**{field: value}) == [f"manifest.json {field}: Not a valid string."]


def test_invalid_json_is_reported_by_the_parser():
    assert validate_manifest_bytes(b"{this is not valid json", namespace=TEAM) == [
        "Unable to parse manifest.json: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
    ]


def test_non_utf8_manifest_is_reported_as_encoding():
    assert validate_manifest_bytes(bytes.fromhex("8081"), namespace=TEAM) == [
        "Unable to parse manifest.json: 'utf-8' codec can't decode byte 0x80 in position 0: invalid start byte\n",
        "Make sure the manifest.json is UTF-8 compatible",
    ]


@pytest.mark.parametrize("document", ([], "text", 42, None))
def test_document_must_be_a_mapping(document):
    expected = f"manifest.json non_field_errors: Invalid data. Expected a mapping, but got {type(document).__name__}."
    assert problems(document) == [expected]


@pytest.mark.parametrize(("name", "message"), [("", "This field may not be blank."), ("   ", "This field may not be blank.")])
def test_blank_names(name, message):
    assert check(name=name) == [f"manifest.json name: {message}"]


@pytest.mark.parametrize("name", ("Bad Name!", "nonsense!", "dash-name", "x" * 129))
def test_bad_names(name):
    expected = (
        "Ensure this field has no more than 128 characters."
        if len(name) > 128
        else "Package names can only contain a-z A-Z 0-9 _ characters"
    )
    assert check(name=name) == [f"manifest.json name: {expected}"]


@pytest.mark.parametrize(
    ("version", "messages"),
    [
        ("1.2", ["Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)", "Version 1.2 should be written as 1.2.0"]),
        ("01.2.3", ["Version 01.2.3 should be written as 1.2.3"]),
        ("1.2.3.4", ["Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)", "invalid version number '1.2.3.4'"]),
        ("v1.2.3", ["Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)", "invalid version number 'v1.2.3'"]),
        ("", ["This field may not be blank."]),
    ],
)
def test_bad_version_numbers(version, messages):
    indexed = len(messages) > 1
    expected = [
        f"manifest.json version_number {index}: {message}" if indexed else f"manifest.json version_number: {message}"
        for index, message in enumerate(messages)
    ]
    assert check(version_number=version) == expected


@pytest.mark.parametrize(
    "url",
    (
        "",
        "https://megabonkmod.party",
        "https://example.com:8443/a/b?c=d#e",
        "mailto://a@b.com",
        "http://localhost/x",
        "https://user:pass@sub.example.com/",
    ),
)
def test_accepted_urls(url):
    assert check(website_url=url) == []


@pytest.mark.parametrize("url", ("not a url", "ftp://example.com/", "mailto:a@b.com", "//example.com", "https://example", "https://exa mple.com", "https://exa\tmple.com"))
def test_rejected_urls(url):
    assert check(website_url=url) == ["manifest.json website_url: Enter a valid URL."]


def test_long_description_is_limited():
    assert check(description="x" * 257) == ["manifest.json description: Ensure this field has no more than 256 characters."]


@pytest.mark.parametrize(
    ("dependency", "message"),
    [
        ("Mythic-TestMod-1.1.0", None),
        ("Dash-Ed-Team-Mythic-TestMod-1.1.0", None),
        ("Mythic-TestMod", "Package reference is missing version: Mythic-TestMod"),
        ("nonsense", "Invalid package reference string: nonsense"),
        ("Mythic-TestMod-1.2", "Invalid package reference string: Mythic-TestMod-1.2"),
        ("Mythic-TestMod-1.2.3.4", "Invalid package reference string: Mythic-TestMod-1.2.3.4"),
    ],
)
def test_dependency_references(dependency, message):
    expected = [] if message is None else [f"manifest.json dependencies 0: {message}"]
    assert check(dependencies=[dependency]) == expected


def test_dependency_list_shape():
    assert check(dependencies="Mythic-TestMod-1.1.0") == ['manifest.json dependencies: Expected a list of items but got type "str".']
    assert check(dependencies=None) == ["manifest.json dependencies: This field may not be null."]
    assert check(dependencies=[]) == []
    assert check(dependencies=[None]) == ["manifest.json dependencies 0: This field may not be null."]


def test_dependencies_are_capped():
    too_many = [f"Team-Package{index}-1.0.0" for index in range(1001)]
    assert check(dependencies=too_many) == ["manifest.json dependencies: Ensure this field has no more than 1000 elements."]


def test_self_dependency_is_rejected():
    assert check(dependencies=[f"{TEAM}-Megabonk_Level_Editor-0.0.1"]) == [
        "manifest.json non_field_errors: Package depending on itself is not allowed"
    ]


def test_two_versions_of_one_dependency_are_rejected():
    assert check(dependencies=["Mythic-TestMod-1.0.0", "Mythic-TestMod-2.0.0"]) == [
        "manifest.json non_field_errors: Cannot depend on multiple versions of the same package"
    ]


def test_field_errors_short_circuit_the_object_checks():
    assert check(name="Bad Name!", dependencies=["Mythic-TestMod-1.0.0", "Mythic-TestMod-2.0.0"]) == [
        "manifest.json name: Package names can only contain a-z A-Z 0-9 _ characters"
    ]


def test_installers_are_optional_and_checked_for_shape():
    assert check(installers=[{"identifier": "r2modman"}]) == []
    assert check(installers=[]) == ["manifest.json installers: This list may not be empty."]
    assert check(installers=[{}]) == ["manifest.json installers 0 identifier: This field is required."]
    assert check(installers=["r2modman"]) == ["manifest.json installers 0 non_field_errors: Invalid data. Expected a mapping, but got str."]
    assert check(installers=[{"identifier": 7}]) == ["manifest.json installers 0 identifier: Not a valid string."]
    assert check(installers=[{"identifier": "a"}, {"identifier": "a"}]) == ["manifest.json non_field_errors: Duplicate use of installer a"]


def test_too_many_installers():
    assert check(installers=[{"identifier": f"i{index}"} for index in range(101)]) == [
        "manifest.json installers: Ensure this field has no more than 100 elements."
    ]


def test_no_team_selected():
    assert problems(manifest(), team="") == ["manifest.json non_field_errors: Unable to validate package when no team is selected"]


@pytest.mark.parametrize("team", ("_leading", "trailing_", "has space", "x" * 65))
def test_team_name_shape_is_checked_locally(team):
    assert problems(manifest(), team=team) != []


def test_serializer_errors_keep_the_drf_field_nesting():
    errors = serializer_problems({**manifest(), "installers": [{}]}, namespace=TEAM)
    assert errors["installers"] == {0: {"identifier": ["This field is required."]}}


def test_reference_parses_from_the_right():
    # Upstream cannot tell where a dashed namespace ends, so the name is always the last component.
    reference = vtm.PackageReference.parse("Dash-Ed-Team-Mythic-TestMod-1.1.0")
    assert (reference.namespace, reference.name, str(reference)) == ("Dash-Ed-Team-Mythic", "TestMod", "Dash-Ed-Team-Mythic-TestMod-1.1.0")


@pytest.mark.parametrize(("given", "canonical"), [("1.2.3", "1.2.3"), ("1.2", "1.2.0"), ("0.0.0", "0.0.0"), ("10.20.30", "10.20.30")])
def test_version_canonical_form(given, canonical):
    assert vtm.Version(given).canonical() == canonical


@pytest.fixture
def site(monkeypatch):
    """Stub thunderstore.io: the versions it publishes and the names its team already owns."""

    class Site:
        def __init__(self) -> None:
            self.versions: set[tuple[str, str, str]] = set()
            self.packages: set[tuple[str, str]] = set()
            self.names: list[str] = []
            self.reachable = True

        def package_exists(self, namespace, name, version_number=None, *, base=None):
            if not self.reachable:
                return None
            if version_number is None:
                return (namespace, name) in self.packages
            return (namespace, name, version_number) in self.versions

        def namespace_packages(self, namespace, community="megabonk", *, base=None):
            return (True, list(self.names)) if self.names else (False, [])

    stub = Site()
    monkeypatch.setattr(vtm, "package_exists", stub.package_exists)
    monkeypatch.setattr(vtm, "namespace_packages", stub.namespace_packages)
    return stub


def test_online_mode_passes_a_real_dependency(site):
    site.versions.add(DEP)
    site.names.append("Megabonk_Level_Editor")
    assert online_problems(manifest(), namespace=TEAM) == ([], [])


def test_online_mode_reports_unresolvable_dependencies(site):
    site.names.append("Megabonk_Level_Editor")
    problems, notes = online_problems(manifest(dependencies=["BepInEx-BepInExPack_IL2CPP-9.9.9"]), namespace=TEAM)
    assert problems == ["manifest.json dependencies: No matching package found for reference: BepInEx-BepInExPack_IL2CPP-9.9.9"]
    assert notes == []


def test_online_mode_reports_an_already_published_version(site):
    site.versions.update({DEP, (TEAM, "Megabonk_Level_Editor", "0.0.1")})
    problems, _ = online_problems(manifest(), namespace=TEAM)
    assert problems == ["manifest.json non_field_errors: Package of the same namespace, name and version already exists"]


def test_online_mode_reports_a_differently_cased_name(site):
    site.versions.add(DEP)
    site.names.append("megabonk_level_editor")
    problems, _ = online_problems(manifest(), namespace=TEAM)
    assert problems == ["manifest.json non_field_errors: Package name already exists with different capitalization"]


def test_unknown_team_namespace_is_only_a_note(site):
    site.versions.add(DEP)
    problems, notes = online_problems(manifest(), namespace=TEAM)
    assert problems == []
    assert notes == ["no team namespace 'pythoninthegrass' on thunderstore.io yet: Object not found until it has a package"]


def test_unreachable_site_becomes_a_note_not_a_failure(site):
    site.reachable = False
    problems, notes = online_problems(manifest(), namespace=TEAM)
    assert problems == []
    assert len(notes) == 2
    assert all("could not be reached" in note for note in notes)


def test_unreachable_listing_is_a_note(site, monkeypatch):
    site.versions.add(DEP)
    monkeypatch.setattr(vtm, "namespace_packages", lambda *args, **kwargs: (None, []))
    problems, notes = online_problems(manifest(), namespace=TEAM)
    assert problems == []
    assert notes == ["thunderstore.io could not be reached to list pythoninthegrass"]


def test_installers_get_a_note_online(site):
    site.versions.add(DEP)
    site.names.append("Megabonk_Level_Editor")
    _, notes = online_problems(manifest(installers=[{"identifier": "r2modman"}]), namespace=TEAM)
    assert notes == ["installers: the site matches each identifier against its installer table, which cannot be done offline"]


def test_online_checks_need_a_valid_document(site):
    assert online_problems([], namespace=TEAM) == ([], [])


@needs_team_config
def test_cli_reads_the_team_from_thunderstore_toml():
    assert vtm.configured_namespace() == TEAM


@needs_repo_manifest
def test_cli_accepts_the_repo_manifest():
    assert vtm.check(REPO_MANIFEST, TEAM, online=False) == ([], [])


def test_cli_reads_the_manifest_from_a_zip(tmp_path):
    archive = tmp_path / "pythoninthegrass-Megabonk_Level_Editor-0.0.1.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("manifest.json", json.dumps(manifest(name="Bad Name!")))
    problems, _ = vtm.check(archive, TEAM, online=False)
    assert problems == ["manifest.json name: Package names can only contain a-z A-Z 0-9 _ characters"]


def test_cli_online_checks_only_run_after_the_offline_ones_pass(monkeypatch, tmp_path):
    calls: list[int] = []
    monkeypatch.setattr(vtm, "online_problems", lambda *args, **kwargs: calls.append(1) or ([], []))
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest()), encoding="utf-8")
    assert vtm.check(path, "bad team!", online=True)[0] != []
    assert calls == []
    assert vtm.check(path, TEAM, online=True) == ([], [])
    assert calls == [1]
    assert vtm.check(path, TEAM, online=False) == ([], [])
    assert calls == [1]
