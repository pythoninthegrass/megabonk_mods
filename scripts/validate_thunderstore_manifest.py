"""Check a manifest.json the way thunderstore.io/tools/manifest-v1-validator does, without an account.

Ported from thunderstore-io/Thunderstore's ManifestV1Serializer and the Django 4.2 / DRF 3.14
validators behind it, reproducing the upstream message text so a line printed here matches a line
the site prints. Offline by default: the checks that need the site's database -- resolving a
dependency, an already-published version, a differently-cased name, installer identifiers -- run
only with --online. The team the site asks you to pick defaults to thunderstore.toml's namespace.

    uv run scripts/validate_thunderstore_manifest.py                     # pkg/manifest.json
    uv run scripts/validate_thunderstore_manifest.py --online            # plus thunderstore.io
    uv run scripts/validate_thunderstore_manifest.py .tools/thunderstore/pythoninthegrass-*.zip
"""

import argparse
import asset_download
import ipaddress
import json
import re
import sys
import tomllib
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
THUNDERSTORE_BASE = "https://thunderstore.io"
REQUEST_TIMEOUT = 15.0
MAX_RESPONSE_BYTES = 1024 * 1024
OK, MISSING, UNREACHABLE = "ok", "missing", "unreachable"

PACKAGE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\_]+$")
PACKAGE_VERSION_REGEX = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
COMPONENT_REGEX = re.compile(r"^[a-zA-Z0-9]+([a-zA-Z0-9\_]+[a-zA-Z0-9])?$")
VERSION_REGEX = re.compile(r"^(\d+) \. (\d+) (\. (\d+))? ([ab](\d+))?$", re.VERBOSE | re.ASCII)

REQUIRED = "This field is required."
MAY_NOT_BE_NULL = "This field may not be null."
MAY_NOT_BE_BLANK = "This field may not be blank."
NOT_A_STRING = "Not a valid string."
NOT_A_LIST = 'Expected a list of items but got type "{input_type}".'
LIST_MAY_NOT_BE_EMPTY = "This list may not be empty."
INVALID_MAPPING = "Invalid data. Expected a mapping, but got {datatype}."
ENTER_A_VALID_URL = "Enter a valid URL."
TOO_MANY_CHARACTERS = "Ensure this field has no more than {max_length} characters."
TOO_MANY_ELEMENTS = "Ensure this field has no more than {max_length} elements."
TOO_FEW_ELEMENTS = "Ensure this field has at least {min_length} elements."
NULL_CHARACTERS = "Null characters are not allowed."
SURROGATE_CHARACTERS = "Surrogate characters are not allowed: U+{code_point:X}."
PACKAGE_NAME_MESSAGE = "Package names can only contain a-z A-Z 0-9 _ characters"
VERSION_NUMBER_MESSAGE = "Version numbers must follow the Major.Minor.Patch format (e.g. 1.45.320)"
COMPONENT_MESSAGE = "Author name can only contain a-z A-Z 0-9 _ characters and must not start or end with _"
NO_TEAM_SELECTED = "Unable to validate package when no team is selected"
NAMESPACE_NOT_FOUND = "Object not found"
DUPLICATE_DEPENDENCY = "Cannot depend on multiple versions of the same package"
SELF_DEPENDENCY = "Package depending on itself is not allowed"
VERSION_ALREADY_EXISTS = "Package of the same namespace, name and version already exists"
DIFFERENT_CAPITALIZATION = "Package name already exists with different capitalization"

_URL_UL = "\u00a1-\uffff"
_URL_IPV4 = r"(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)(?:\.(?:0|25[0-5]|2[0-4][0-9]|1[0-9]?[0-9]?|[1-9][0-9]?)){3}"
_URL_HOSTNAME = rf"[a-z{_URL_UL}0-9](?:[a-z{_URL_UL}0-9-]{{0,61}}[a-z{_URL_UL}0-9])?"
_URL_DOMAIN = rf"(?:\.(?!-)[a-z{_URL_UL}0-9-]{{1,63}}(?<!-))*"
_URL_TLD = rf"\.(?!-)(?:[a-z{_URL_UL}-]{{2,63}}|xn--[a-z0-9]{{1,59}})(?<!-)\.?"
URL_REGEX = re.compile(
    r"^(?:[a-z0-9.+-]*)://(?:[^\s:@/]+(?::[^\s:@/]*)?@)?"
    rf"(?:{_URL_IPV4}|\[[0-9a-f:.]+\]|({_URL_HOSTNAME}{_URL_DOMAIN}{_URL_TLD}|localhost))"
    r"(?::[0-9]{1,5})?(?:[/?#][^\s]*)?\Z",
    re.IGNORECASE,
)
URL_SCHEMES = ("http", "https", "mailto", "ipfs")
_URL_UNSAFE = frozenset("\t\r\n")


class Version:
    """``major.minor.patch`` with an optional ``aN``/``bN`` suffix, as upstream's StrictVersion clone parses it."""

    def __init__(self, vstring: str) -> None:
        """Raise ValueError unless vstring is a version this grammar accepts."""
        match = VERSION_REGEX.match(vstring or "")
        if not match:
            raise ValueError(f"invalid version number '{vstring}'")
        major, minor, patch, prerelease, prerelease_number = match.group(1, 2, 4, 5, 6)
        self.version = (int(major), int(minor), int(patch or 0))
        self.prerelease = (prerelease[0], int(prerelease_number)) if prerelease else None

    def canonical(self) -> str:
        """The three-part form upstream compares the submitted string against."""
        return ".".join(str(part) for part in self.version)


class PackageReference:
    """A ``Namespace-Name-Version`` reference, parsed backwards because a namespace may hold dashes."""

    def __init__(self, namespace: str, name: str, version: Version | None = None) -> None:
        self.namespace = namespace
        self.name = name
        self.version = version

    def __str__(self) -> str:
        return f"{self.namespace}-{self.name}" + (f"-{self.version.canonical()}" if self.version else "")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PackageReference):
            return NotImplemented
        return (self.namespace, self.name, self.version) == (other.namespace, other.name, other.version)

    def __hash__(self) -> int:
        return hash(str(self))

    @property
    def without_version(self) -> "PackageReference":
        """The same reference with the version dropped, which is how upstream compares packages."""
        return PackageReference(self.namespace, self.name) if self.version else self

    @classmethod
    def parse(cls, unparsed: str) -> "PackageReference":
        """Split a reference string, taking the version then the name from the right."""
        tail = unparsed.split("-")[-1]
        version = None
        if tail.count(".") > 0:
            if tail.count(".") != 2 or unparsed.count("-") < 2:
                raise ValueError(f"Invalid package reference string: {unparsed}")
            version, unparsed = Version(tail), unparsed[: -(len(tail) + 1)]
        name = unparsed.split("-")[-1]
        namespace = "-".join(unparsed.split("-")[:-1])
        if not (namespace and name):
            raise ValueError(f"Invalid package reference string: {unparsed}")
        return cls(namespace, name, version)


def unpack_serializer_errors(field: str, errors: Any, flattened: dict | None = None) -> dict:
    """Flatten a DRF error mapping into dotted paths, as the site's validate_manifest does."""
    flattened = {} if flattened is None else flattened
    if isinstance(errors, list) and len(errors) == 1:
        errors = errors[0]
    if isinstance(errors, dict):
        for key, value in errors.items():
            unpack_serializer_errors(f"{field} {key}", value, flattened)
    elif isinstance(errors, list):
        for index, entry in enumerate(errors):
            unpack_serializer_errors(f"{field} {index}", entry, flattened)
    else:
        flattened[field] = str(errors)
    return flattened


def _is_ipv6(candidate: str) -> bool:
    """Whether a bracketed host is an IPv6 address, as Django verifies after its regex."""
    try:
        return ipaddress.ip_address(candidate).version == 6
    except ValueError:
        return False


def _version_number_problems(value: str) -> list[str]:
    """VersionNumberValidator: a version that parses must also spell itself back exactly."""
    try:
        canonical = Version(value).canonical()
    except ValueError as exc:
        return [str(exc)]
    return [] if canonical == value else [f"Version {value} should be written as {canonical}"]


def _regex_message(pattern: re.Pattern, message: str) -> Callable[[str], list[str]]:
    """A validator that reports `message` when the value misses the pattern."""

    def check(value: str) -> list[str]:
        return [] if pattern.match(value) else [message]

    return check


def _validate_url(value: Any) -> list[str]:
    """Django 4.2's URLValidator, restricted to the schemes upstream allows."""
    if not isinstance(value, str) or len(value) > 2048 or _URL_UNSAFE.intersection(value):
        return [ENTER_A_VALID_URL]
    if value.split("://")[0].lower() not in URL_SCHEMES:
        return [ENTER_A_VALID_URL]
    try:
        parts = urlsplit(value)
    except ValueError:
        return [ENTER_A_VALID_URL]
    if not URL_REGEX.match(value):
        try:
            netloc = parts.netloc.encode("idna").decode("ascii")
        except UnicodeError:
            return [ENTER_A_VALID_URL]
        if not URL_REGEX.match(urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))):
            return [ENTER_A_VALID_URL]
    bracketed = re.match(r"^\[(.+)\](?::[0-9]{1,5})?$", parts.netloc)
    if bracketed and not _is_ipv6(bracketed[1]):
        return [ENTER_A_VALID_URL]
    return [] if parts.hostname and len(parts.hostname) <= 253 else [ENTER_A_VALID_URL]


# name, version_number, website_url, description: max length, allow_blank, extra validators.
CHAR_FIELDS = (
    ("name", 128, False, (_regex_message(PACKAGE_NAME_REGEX, PACKAGE_NAME_MESSAGE),)),
    (
        "version_number",
        16,
        False,
        (
            _regex_message(PACKAGE_VERSION_REGEX, VERSION_NUMBER_MESSAGE),
            _version_number_problems,
        ),
    ),
    ("website_url", 1024, True, (_validate_url,)),
    ("description", 256, True, ()),
)


def _char_problems(value: Any, max_length: int | None, allow_blank: bool, validators: tuple[Callable[[str], list[str]], ...] = ()) -> list[str]:
    """DRF 3.14 CharField.run_validation followed by Field.run_validation, as a message list."""
    if value is None:
        return [MAY_NOT_BE_NULL]
    if value == "" or str(value).strip() == "":
        return [] if allow_blank else [MAY_NOT_BE_BLANK]
    if isinstance(value, bool) or not isinstance(value, str):
        return [NOT_A_STRING]
    value = value.strip()
    errors = [TOO_MANY_CHARACTERS.format(max_length=max_length)] if max_length is not None and len(value) > max_length else []
    if "\x00" in value:
        errors.append(NULL_CHARACTERS)
    errors += [SURROGATE_CHARACTERS.format(code_point=ord(character)) for character in value if 0xD800 <= ord(character) <= 0xDFFF][:1]
    return errors + [message for validate in validators for message in validate(value)]


def _dependency_problems(entry: Any) -> list[str]:
    """DependencyField: parse the reference, then require a version; resolving it needs the site."""
    if entry is None:
        return [MAY_NOT_BE_NULL]
    try:
        reference = PackageReference.parse(str(entry))
    except ValueError as exc:
        return [str(exc)]
    return [] if reference.version else [f"Package reference is missing version: {reference}"]


def _installer_problems(entry: Any) -> dict:
    """PackageInstallerSerializer: a nested Serializer, so its errors stay keyed by field name."""
    if not isinstance(entry, dict):
        return {"non_field_errors": [INVALID_MAPPING.format(datatype=type(entry).__name__)]}
    if "identifier" not in entry:
        return {"identifier": [REQUIRED]}
    problems = _char_problems(entry["identifier"], None, False)
    return {"identifier": problems} if problems else {}


def _list_problems(value: Any, *, allow_empty: bool, min_length: int | None, max_length: int | None, child: Callable[[Any], Any]) -> dict | list[str]:
    """ListField.to_internal_value plus the length validators DRF appends; child errors win, as in DRF."""
    if value is None:
        return [MAY_NOT_BE_NULL]
    if isinstance(value, (str, dict)) or not hasattr(value, "__iter__"):
        return [NOT_A_LIST.format(input_type=type(value).__name__)]
    if not allow_empty and len(value) == 0:
        return [LIST_MAY_NOT_BE_EMPTY]
    errors = {index: problems for index, item in enumerate(value) if (problems := child(item))}
    if errors:
        return errors
    if min_length is not None and len(value) < min_length:
        return [TOO_FEW_ELEMENTS.format(min_length=min_length)]
    if max_length is not None and len(value) > max_length:
        return [TOO_MANY_ELEMENTS.format(max_length=max_length)]
    return []


def _duplicated_identifier(installers: list[dict]) -> str | None:
    """The first installer identifier used twice, which validate_unique_installers rejects."""
    seen: set[str] = set()
    for entry in installers:
        if entry["identifier"] in seen:
            return entry["identifier"]
        seen.add(entry["identifier"])
    return None


def _object_problems(reference: PackageReference, dependencies: list[PackageReference]) -> list[str]:
    """ManifestV1Serializer.validate, minus the checks that need the site's database."""
    if any(a.without_version == b.without_version for index, a in enumerate(dependencies) for b in dependencies[index + 1 :]):
        return [DUPLICATE_DEPENDENCY]
    if any(dependency.without_version == reference.without_version for dependency in dependencies):
        return [SELF_DEPENDENCY]
    return []


def _team_problems(namespace: str) -> list[str]:
    """Local-only: the site looks the team up in its database, so only its shape is checkable here."""
    if not namespace:
        return [NO_TEAM_SELECTED]
    return _char_problems(namespace, 64, False, (_regex_message(COMPONENT_REGEX, COMPONENT_MESSAGE),))


def serializer_problems(document: Any, *, namespace: str) -> dict:
    """The error mapping ManifestV1Serializer would produce, in field declaration order."""
    if not isinstance(document, dict):
        return {"non_field_errors": [INVALID_MAPPING.format(datatype=type(document).__name__)]}
    errors: dict[str, Any] = {
        key: [REQUIRED] if key not in document else _char_problems(document[key], max_length, allow_blank, validators)
        for key, max_length, allow_blank, validators in CHAR_FIELDS
    }
    errors["dependencies"] = (
        [REQUIRED]
        if "dependencies" not in document
        else _list_problems(document["dependencies"], allow_empty=True, min_length=None, max_length=1000, child=_dependency_problems)
    )
    if "installers" in document:
        errors["installers"] = _list_problems(document["installers"], allow_empty=False, min_length=1, max_length=100, child=_installer_problems)
        if not errors["installers"] and (duplicated := _duplicated_identifier(document["installers"])):
            errors["non_field_errors"] = [f"Duplicate use of installer {duplicated}"]
    errors = {key: value for key, value in errors.items() if value}
    if errors:
        return errors
    reference = PackageReference(namespace, document["name"], Version(document["version_number"]))
    dependencies = [PackageReference.parse(str(entry)) for entry in document["dependencies"]]
    if problems := _team_problems(namespace) or _object_problems(reference, dependencies):
        errors["non_field_errors"] = problems
    return errors


def validate_manifest_bytes(manifest_data: bytes, *, namespace: str) -> list[str]:
    """One message per problem, phrased as the site phrases them; [] means the manifest would pass."""
    try:
        document = json.loads(manifest_data)
    except UnicodeDecodeError as exc:
        return [f"Unable to parse manifest.json: {exc}\n", "Make sure the manifest.json is UTF-8 compatible"]
    except json.JSONDecodeError as exc:
        return [f"Unable to parse manifest.json: {exc}"]
    flattened = unpack_serializer_errors("manifest.json", serializer_problems(document, namespace=namespace))
    return [f"{key}: {value}" for key, value in flattened.items()]


def _get_json(url: str) -> tuple[str, Any]:
    """Fetch JSON through the repo's hardened fetcher: (ok, body), (missing, None) or (unreachable, None)."""
    try:
        body = asset_download.download(url, timeout=REQUEST_TIMEOUT, max_bytes=MAX_RESPONSE_BYTES)
    except asset_download.MissingAsset:
        return MISSING, None
    except (asset_download.DownloadError, UnicodeDecodeError):
        return UNREACHABLE, None
    try:
        return OK, json.loads(body)
    except json.JSONDecodeError:
        return UNREACHABLE, None


def package_exists(namespace: str, name: str, version_number: str | None = None, *, base: str = THUNDERSTORE_BASE) -> bool | None:
    """Whether the site has this package, or this exact version; None when it could not say."""
    parts = [base, "api", "experimental", "package", namespace, name, *([version_number] if version_number else [])]
    outcome, _ = _get_json("/".join(parts) + "/")
    if outcome == OK:
        return True
    return None if outcome == UNREACHABLE else False


def namespace_packages(namespace: str, community: str = "megabonk", *, base: str = THUNDERSTORE_BASE) -> tuple[bool | None, list[str]]:
    """Whether the site knows this team namespace, and the package names it lists under it."""
    outcome, payload = _get_json(f"{base}/api/cyberstorm/listing/{community}/{namespace}/")
    if outcome != OK or not isinstance(payload, dict):
        return (None if outcome == UNREACHABLE else False), []
    return True, [str(entry.get("name", "")) for entry in payload.get("results") or []]


def online_problems(document: Any, *, namespace: str, community: str = "megabonk", base: str = THUNDERSTORE_BASE) -> tuple[list[str], list[str]]:
    """The database-backed checks as (problems, notes); a note is something that could not be confirmed."""
    if not isinstance(document, dict):
        return [], []
    problems, notes = [], []
    for entry in document.get("dependencies") or []:
        try:
            reference = PackageReference.parse(str(entry))
        except ValueError:
            continue
        if not reference.version:
            continue
        match = package_exists(reference.namespace, reference.name, reference.version.canonical(), base=base)
        if match is False:
            problems.append(f"manifest.json dependencies: No matching package found for reference: {reference}")
        elif match is None:
            notes.append(f"thunderstore.io could not be reached to resolve {reference}")
    name, version_number = document.get("name"), document.get("version_number")
    if isinstance(name, str) and isinstance(version_number, str) and namespace:
        published = package_exists(namespace, name, version_number, base=base)
        if published:
            problems.append(f"manifest.json non_field_errors: {VERSION_ALREADY_EXISTS}")
        elif published is None:
            notes.append(f"thunderstore.io could not be reached to check {namespace}-{name}-{version_number}")
        else:
            known, names = namespace_packages(namespace, community, base=base)
            if known is None:
                notes.append(f"thunderstore.io could not be reached to list {namespace}")
            elif known is False:
                notes.append(f"no team namespace {namespace!r} on thunderstore.io yet: {NAMESPACE_NOT_FOUND} until it has a package")
            elif any(existing.casefold() == name.casefold() and existing != name for existing in names):
                problems.append(f"manifest.json non_field_errors: {DIFFERENT_CAPITALIZATION}")
    if document.get("installers"):
        notes.append("installers: the site matches each identifier against its installer table, which cannot be done offline")
    return problems, notes


def configured_namespace() -> str:
    """The team the site's validator asks you to pick, taken from thunderstore.toml."""
    try:
        config = tomllib.loads((ROOT / "thunderstore.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    return str(config.get("package", {}).get("namespace", ""))


def read_manifest(path: Path) -> bytes:
    """The manifest's bytes, from a manifest.json or from that entry inside a built package ZIP."""
    if path.suffix.lower() != ".zip":
        return path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        return archive.read("manifest.json")


def check(path: Path, namespace: str, online: bool) -> tuple[list[str], list[str]]:
    """Offline problems first; the site is consulted only once the manifest itself is sound."""
    data = read_manifest(path)
    if problems := validate_manifest_bytes(data, namespace=namespace):
        return problems, []
    if not online:
        return [], []
    try:
        document = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return [], []
    return online_problems(document, namespace=namespace)


def main() -> int:
    """Run one check over a manifest and report it the way the site's page does."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("manifest", nargs="?", type=Path, default=ROOT / "pkg" / "manifest.json", help="manifest.json or a built package ZIP")
    parser.add_argument("--team", help="namespace to validate under (default: thunderstore.toml [package].namespace)")
    parser.add_argument("--online", action="store_true", help="resolve dependencies and check for a published version against thunderstore.io")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit machine-readable output")
    args = parser.parse_args()

    namespace = args.team if args.team is not None else configured_namespace()
    try:
        problems, notes = check(args.manifest, namespace, args.online)
    except OSError as error:
        return _fail(f"Cannot read manifest: {error}")
    except KeyError:
        return _fail(f"{args.manifest} has no manifest.json entry")
    except zipfile.BadZipFile:
        return _fail(f"{args.manifest} is not a ZIP")

    if args.as_json:
        print(json.dumps({"manifest": str(args.manifest), "namespace": namespace, "problems": problems, "notes": notes}))
    elif problems:
        print(f"{args.manifest} (team {namespace or 'unset'}) is not valid:", file=sys.stderr)
        print("\n".join(f"  {problem}" for problem in problems), file=sys.stderr)
    else:
        print(f"No errors found: {args.manifest} (team {namespace})")
    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    return int(bool(problems))


def _fail(message: str) -> int:
    """Report an unusable input and exit with a code distinct from a validation failure."""
    print(message, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
