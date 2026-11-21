"""Decide from the macOS SDK whether an imported Linux function may be forwarded to the host.

A name that `dlsym` resolves can still disagree with Linux on structure layout, and a scalar argument can still
carry a Linux-only number (an errno, a flag, a clock id). So a function is bound only when the SDK declares it in
one of the value-only libc headers with a prototype of scalars that fits the register file; everything else is
refused with a fixed reason.
"""

from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

CLANG = os.environ.get("CC", "clang")
QUALIFIERS = re.compile(r"\b(const|volatile|restrict|_Nonnull|_Nullable|__restrict|__const|__volatile)\b")
INTEGER_KINDS = {
    "_Bool": "u8",
    "char": "i8",
    "signed char": "i8",
    "unsigned char": "u8",
    "short": "i16",
    "unsigned short": "u16",
    "int": "i32",
    "unsigned int": "u32",
    "long": "i64",
    "unsigned long": "u64",
    "long long": "i64",
    "unsigned long long": "u64",
}
FLOAT_KINDS = {"float": "f32", "double": "f64"}
NARROW_KINDS = {"u8", "i8", "u16", "i16"}
FLOAT_CLASS = {"f32", "f64"}
# A va_list is the caller's register save area, not the host's: forwarding one reads the wrong window.
VA_LIST_SPELLINGS = {"va_list", "__builtin_va_list", "__darwin_va_list", "__va_list_tag"}
MAX_INTEGER_ARGUMENTS = 6
MAX_FLOAT_ARGUMENTS = 8
# Headers whose functions take values and buffers, not numbers the operating system defines (flags, clock ids, errnos).
VALUE_ONLY_HEADERS = frozenset({"string", "strings", "ctype", "wctype", "wchar", "math", "stdlib", "stdio", "malloc"})
# Functions in those headers whose argument is nevertheless an OS-defined number space.
OS_DEFINED_ARGUMENTS = frozenset({"strerror", "strerror_r", "strsignal", "mkostemp", "mkostemps", "posix_openpt"})

# One translation unit per family, so a header that errors under the feature macros still leaves the others.
UMBRELLAS = (
    """
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <wchar.h>
#include <wctype.h>
#include <ctype.h>
#include <math.h>
#include <float.h>
#include <limits.h>
""",
    """
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>
#include <signal.h>
#include <setjmp.h>
#include <time.h>
#include <sched.h>
#include <pthread.h>
#include <errno.h>
#include <assert.h>
""",
    """
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>
#include <unistd.h>
#include <fcntl.h>
#include <utime.h>
#include <spawn.h>
#include <grp.h>
#include <pwd.h>
#include <dirent.h>
#include <poll.h>
#include <semaphore.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/uio.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <sys/times.h>
#include <sys/utsname.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <sys/file.h>
#include <sys/ioctl.h>
#include <sys/select.h>
#include <syslog.h>
""",
    """
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <net/if.h>
#include <ifaddrs.h>
#include <dlfcn.h>
#include <locale.h>
#include <langinfo.h>
#include <xlocale.h>
#include <iconv.h>
#include <termios.h>
#include <ucontext.h>
""",
)
FEATURE_MACROS = ("-D_DARWIN_C_SOURCE", "-D_XOPEN_SOURCE=700")
ABSENT = "not declared in the SDK"
OUTSIDE = "outside the value-only libc headers"
OS_DEFINED = "OS-defined argument values"


class _Files:
    """The file a declaration came from. Clang prints `file` only when it changes between locations, in dump order."""

    def __init__(self):
        self.current = ""

    def see(self, location) -> None:
        if not isinstance(location, dict):
            return
        for key, value in location.items():
            if key == "file" and isinstance(value, str):
                self.current = value
            elif key in ("spellingLoc", "expansionLoc", "begin", "end"):
                self.see(value)


def _declarations(node, files: _Files):
    """Every node of the dump with the file that declares it, visiting nodes in the order clang printed them."""
    files.see(node.get("loc"))
    here = files.current
    files.see(node.get("range"))
    yield node, here
    for child in node.get("inner") or []:
        yield from _declarations(child, files)


def _strip(qual: str) -> str:
    return " ".join(QUALIFIERS.sub(" ", qual).split())


def _argument_list(text: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _split_prototype(qual: str):
    """The result, the parameter list and whether the function is variadic, from a canonical `ret (args)`."""
    open_ = qual.index("(")
    depth, close = 0, None
    for index in range(open_, len(qual)):
        if qual[index] == "(":
            depth += 1
        elif qual[index] == ")":
            depth -= 1
            if depth == 0:
                close = index
                break
    if close is None:
        return None
    return _strip(qual[:open_]), qual[open_ + 1 : close], "..." in qual[open_ + 1 : close]


def _header_family(path: str) -> str:
    return Path(path).name.lstrip("_").removesuffix(".h")


@dataclass(frozen=True)
class Decision:
    """`bound` with the register kind of each argument and of the result, or refused with the reason."""

    bound: bool
    reason: str = ""
    args: tuple[str, ...] = ()
    result: str = "void"
    prototype: str = ""


class Sdk:
    """Every function the macOS SDK declares, with the header that declares it, decided by canonical type."""

    def __init__(self, asts: list[dict]):
        self.typedefs: dict[str, dict] = {}
        self.funcs: dict[str, list[tuple[dict, str]]] = collections.defaultdict(list)
        self.records: set[str] = set()
        for ast in asts:
            for node, header in _declarations(ast, _Files()):
                kind, name = node.get("kind"), node.get("name")
                if not name:
                    continue
                if kind == "TypedefDecl":
                    self.typedefs.setdefault(name, node)
                elif kind == "FunctionDecl" and (node.get("type") or {}).get("qualType"):
                    self.funcs[name].append((node, header))
                elif kind in ("RecordDecl", "CXXRecordDecl", "UnionDecl"):
                    self.records.add(name)
        self._typedef_cache: dict[str, tuple[str | None, str]] = {}

    def declared(self, name: str) -> bool:
        return name in self.funcs

    def kind(self, spelling: str, depth: int = 0) -> tuple[str | None, str]:
        """(register kind, "") for a type that may pass through the register file, else (None, why not)."""
        qual = _strip(spelling)
        if qual in INTEGER_KINDS:
            return INTEGER_KINDS[qual], ""
        if qual in FLOAT_KINDS:
            return FLOAT_KINDS[qual], ""
        if qual == "long double":
            return None, "long double"
        if qual == "void":
            return "void", ""
        if qual in VA_LIST_SPELLINGS or (qual.endswith("*") and _strip(qual[:-1]) in VA_LIST_SPELLINGS):
            return None, "va_list"
        if depth > 12:
            return None, "unclassified"
        if qual.endswith("*"):
            pointee, why = self.kind(qual[:-1], depth + 1)
            return ("ptr", "") if pointee else (None, why)
        if qual.endswith("]"):
            return None, "array"
        if "(" in qual and qual.endswith(")"):
            return None, "function pointer"
        if qual.startswith(("struct ", "union ")) or qual in self.records:
            return None, "record"
        if qual.startswith("enum "):
            return None, "enumerated"
        if qual in self.typedefs:
            return self._typedef(qual, depth)
        return None, "unclassified"

    def _typedef(self, name: str, depth: int) -> tuple[str | None, str]:
        if name in self._typedef_cache:
            return self._typedef_cache[name]
        self._typedef_cache[name] = (None, "unclassified")
        underlying = _strip((self.typedefs[name].get("type") or {}).get("qualType", ""))
        result = self.kind(underlying, depth + 1) if underlying else (None, "unclassified")
        self._typedef_cache[name] = result
        return result

    def decide(self, name: str) -> Decision:
        """Bound when some declaration passes the header and prototype rules, otherwise every refusal reason."""
        declarations = self.funcs.get(name)
        if not declarations:
            return Decision(False, ABSENT)
        reasons = []
        for node, header in declarations:
            decision = self._decide_one(name, node, header)
            if decision.bound:
                return decision
            reasons.append(decision.reason)
        return Decision(False, "; ".join(sorted(set(reasons))))

    def _decide_one(self, name: str, node: dict, header: str) -> Decision:
        if _header_family(header) not in VALUE_ONLY_HEADERS:
            return Decision(False, OUTSIDE)
        if name in OS_DEFINED_ARGUMENTS:
            return Decision(False, OS_DEFINED)
        split = _split_prototype((node.get("type") or {}).get("qualType", ""))
        if split is None:
            return Decision(False, "unclassified parameter")
        result_spelling, parameters, variadic = split
        if variadic:
            return Decision(False, "variadic")
        spellings = [] if parameters.strip() in ("", "void") else _argument_list(parameters)
        kinds = []
        for spelling in spellings:
            kind, why = self.kind(spelling)
            if kind is None:
                return Decision(False, f"{why} parameter")
            if kind == "void":
                return Decision(False, "void parameter")
            if kind in NARROW_KINDS:
                return Decision(False, "narrow integer parameter")
            kinds.append(kind)
        result, why = self.kind(result_spelling)
        if result is None:
            return Decision(False, f"{why} result")
        if sum(kind not in FLOAT_CLASS for kind in kinds) > MAX_INTEGER_ARGUMENTS:
            return Decision(False, "more than six integer-class arguments")
        if sum(kind in FLOAT_CLASS for kind in kinds) > MAX_FLOAT_ARGUMENTS:
            return Decision(False, "more than eight floating-point-class arguments")
        return Decision(True, "", tuple(kinds), result, f"{result_spelling} ({parameters})")


def _dump(ast_source, timeout: int = 300) -> dict:
    """One clang AST dump of one umbrella translation unit, from its text or the path holding it."""
    if isinstance(ast_source, Path) or (isinstance(ast_source, str) and ast_source.endswith(".c")):
        source = Path(ast_source)
    else:
        directory = Path(tempfile.mkdtemp(prefix="lift-sdk-"))
        source = directory / "umbrella.c"
        source.write_text(ast_source)
    language = "c++" if source.suffix in {".cpp", ".cc", ".cxx", ".hpp"} else "c"
    command = [
        CLANG,
        *FEATURE_MACROS,
        "-Xclang",
        "-ast-dump=json",
        "-fsyntax-only",
        "-x",
        language,
        str(source),
    ]
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, start_new_session=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"clang is not available ({CLANG}): {exc}") from None
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"clang timed out after {timeout}s over the SDK umbrella") from None
    if proc.returncode:
        detail = (proc.stderr or "").strip().splitlines()
        raise RuntimeError(f"the SDK umbrella did not compile: {detail[-1] if detail else proc.returncode}")
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise RuntimeError(f"clang did not emit a readable AST dump: {exc}") from None


def load(timeout: int = 300) -> Sdk:
    """The SDK view of every function declaration in the umbrella headers, read by clang over the SDK."""
    return Sdk([_dump(source, timeout) for source in UMBRELLAS])
