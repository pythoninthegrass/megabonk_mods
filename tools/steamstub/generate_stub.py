#!/usr/bin/env python3
"""Generate the offline Steamworks stub (steamstub.c) from a real shim.

The stub lets Megabonk launch without a logged-in Steam session. It exports the
same symbol set as the game's bundled steam_api64.dll shim, so every P/Invoke
the game's Steamworks.NET runtime can already resolve still resolves. Most
interface methods return a safe default; the few the game actually needs for
init, load-level and the offline save path return real values.

Usage:
    tools/steamstub/generate_stub.py <path-to-steam_api64.dll> > tools/steamstub/steamstub.c

The shim path is resolved from the game dir when --game-dir is given; otherwise
pass the shim on the command line.
"""
import re
import struct
import sys


# --- runtime entry points the game P/Invokes, hand-authored -----------------
# These are not part of the SteamAPI_ISteamX_* wrapper family, so they are not
# generated. Each mirrors the managed signature from the Il2Cpp dump.
RUNTIME = r'''// ---- runtime entry points (Steamworks.NET init + lifecycle) ---------------
// InitEx -> this. Return 0 (k_ESteamAPIInitResult_OK) so SteamAPI.InitEx()
// reports success and the game caches interfaces instead of staying degraded.
int SteamInternal_SteamAPI_Init(const char *version, char *outErrMsg) {
    // MEGABONK_STEAM_FAIL_INIT=1 makes Init() fail exactly as it would with no
    // Steam client, so the game logs and continues into the degraded/offline
    // verdict. Without the env var, Init() succeeds and the stub stands in for
    // a logged-in session. See the #2 degraded-verdict test in docs/development.md.
    (void)version;
    const char *fail = getenv("MEGABONK_STEAM_FAIL_INIT");
    if (fail) {
        if (outErrMsg) {
            const char *msg = "Steam client not available";
            int i = 0;
            while (msg[i] && i < 31) { outErrMsg[i] = msg[i]; i++; }
            outErrMsg[i] = 0;
        }
        return 3; // k_ESteamAPIInitResult_NoSteamClient
    }
    if (outErrMsg) outErrMsg[0] = 0;
    return 0;
}

int SteamInternal_ContextInit(void *data) { (void)data; return 0; }

// CreateInterface / FindOrCreateUserInterface return a stable non-NULL pointer
// to a single fake object. The wrapper methods below ignore it, so one object
// serves every interface version the game requests.
void *SteamInternal_CreateInterface(const char *version) {
    (void)version;
    return &g_fake_interface;
}

void *SteamInternal_FindOrCreateUserInterface(void *hUser, const char *version) {
    (void)hUser; (void)version;
    return &g_fake_interface;
}

void *SteamInternal_FindOrCreateGameServerInterface(void *hUser, const char *version) {
    (void)hUser; (void)version;
    return &g_fake_interface;
}

int SteamInternal_GameServer_Init_V2(void *a, void *b, void *c, void *d,
                                     const char *e, void *f) {
    (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;
    return 0;
}

void SteamAPI_Shutdown(void) {}
void SteamAPI_RunCallbacks(void) {}
void SteamAPI_RegisterCallback(void *cb, int size) { (void)cb;(void)size; }
void SteamAPI_UnregisterCallback(void *cb) { (void)cb; }
void SteamAPI_RegisterCallResult(void *cr, unsigned long long h) { (void)cr;(void)h; }
void SteamAPI_UnregisterCallResult(void *cr, unsigned long long h) { (void)cr;(void)h; }
void SteamAPI_ReleaseCurrentThreadMemory(void) {}
void SteamAPI_WriteMiniDump(unsigned int code, void *info, unsigned int build) {
    (void)code;(void)info;(void)build;
}
void SteamAPI_SetMiniDumpComment(const char *msg) { (void)msg; }
void SteamAPI_SetBreakpadAppID(unsigned int id) { (void)id; }
void SteamAPI_SetTryCatchCallbacks(bool b) { (void)b; }
void SteamAPI_UseBreakpadCrashHandler(const char *a, const char *b, const char *c,
                                      bool d, void *e, void *f) {
    (void)a;(void)b;(void)c;(void)d;(void)e;(void)f;
}

// The game reads these to decide whether Steam is present. Report "running",
// unless MEGABONK_STEAM_FAIL_INIT is set, which also makes this report "down"
// so the degraded path is observable end-to-end.
int SteamAPI_IsSteamRunning(void) {
    return getenv("MEGABONK_STEAM_FAIL_INIT") ? 0 : 1;
}
int SteamAPI_GetHSteamPipe(void) { return 1; }
int SteamAPI_GetHSteamUser(void) { return 1; }
int SteamAPI_GetSteamInstallPath(char *buf, int size) {
    if (buf && size > 0) { buf[0] = 0; }
    return 0;
}

// Alternate init entry points the shim also exports; behave like Init.
int SteamAPI_InitAnonymousUser(void) { return 1; }
int SteamAPI_InitFlat(void) { return 1; }
int SteamAPI_InitSafe(void) { return 1; }

// RestartAppIfNecessary returns the app id to relaunch with; 0 means "no restart".
int SteamAPI_RestartAppIfNecessary(unsigned long long ownAppId) {
    (void)ownAppId;
    return 0;
}

// Global the shim exports; the game's game-server path (unused here) may read it.
void *g_pSteamClientGameServer = NULL;
'''


def main():
    shim = sys.argv[1] if len(sys.argv) > 1 else None
    if not shim:
        print("usage: generate_stub.py <steam_api64.dll>", file=sys.stderr)
        sys.exit(2)

    exports = parse_exports(shim)
    wrappers = []
    for name in exports:
        if not name.startswith("SteamAPI_"):
            continue
        rest = name[len("SteamAPI_"):]
        # Only the interface-method family: ISteamXxx_Method. Skip the runtime
        # entry points (SteamClient_, InitSafe, etc.) -- handled by hand above.
        m = re.match(r"I(Steam\w+)_(\w+)$", rest)
        if not m:
            continue
        iface, method = m.group(1), m.group(2)
        wrappers.append((name, iface, method))

    out = []
    out.append("// AUTO-GENERATED by generate_stub.py from the game's steam_api64.dll shim.")
    out.append("// Do not edit by hand; regenerate, then build with build.sh.")
    out.append("#include <windows.h>")
    out.append("#include <stdint.h>")
    out.append("#include <string.h>")
    out.append("#include <stdlib.h>")
    out.append("")
    out.append("// The running game's depot build id (matches every shipped level file's")
    out.append("// gameBuildId, so the loader records no mismatch).")
    out.append("#define STEAMBUILD_ID 21750826u")
    out.append("// The game's Steam app id.")
    out.append("#define STEAM_APP_ID 3405340u")
    out.append("")
    out.append("static char g_fake_interface[32];")
    out.append("")

    # Static strings for the string-returning getters.
    out.append("static const char g_lang[] = \"english\";")
    out.append("static const char g_empty[] = \"\";")
    out.append("static const char g_latest_client[] = \"1.0.0.0\";")
    out.append("static const char g_install_dir[] = \"Megabonk\";")
    out.append("")

    # Buffer-writing getters write their first char* argument (RDX in the x64
    # calling convention) and return the byte count.
    out.append("static long long write_buffer(void *buf, long long size, const char *s) {")
    out.append("    long long n = (long long)strlen(s);")
    out.append("    if (buf && size > 0) {")
    out.append("        long long c = n < size - 1 ? n : size - 1;")
    out.append("        memcpy(buf, s, c);")
    out.append("        ((char *)buf)[c] = 0;")
    out.append("    }")
    out.append("    return n;")
    out.append("}")
    out.append("")

    out.append(RUNTIME)
    out.append("")
    out.append("// ---- interface-method wrappers ------------------------------------------")
    out.append("// Each ignores its instance pointer and returns a safe default, except the")
    out.append("// handful the game needs for init, the loader's build-id check and saves.")
    for name, iface, method in wrappers:
        out.append(embrace_wrapper(name, method))
    out.append("")

    sys.stdout.write("\n".join(out))


def embrace_wrapper(name, method):
    # String-returning getters return a static pointer; buffer getters write
    # their second argument; GetAppBuildId/GetAppID return real values; the
    # default is a zero return (false / 0 / NULL), which the managed side reads
    # as bool false, int 0, or a CSteamID(0) for the 8-byte GetSteamID.
    if method == "GetAppBuildId":
        return f"long long {name}(void) {{ return (long long)STEAMBUILD_ID; }}"
    if method == "GetAppID":
        return f"long long {name}(void) {{ return (long long)STEAM_APP_ID; }}"
    if method == "GetSteamID":
        # CSteamID is a single ulong; 0 selects the offline (steamId 0) save path.
        return f"long long {name}(void) {{ return 0; }}"
    if method in ("GetCurrentGameLanguage", "GetSteamUILanguage"):
        return f"long long {name}(void) {{ return (long long)&g_lang[0]; }}"
    if method in ("GetCurrentBetaName", "GetAPICallErrorString", "GetLatestClientVersion"):
        return f"long long {name}(void) {{ return (long long)&g_empty[0]; }}"
    if method in ("GetAppInstallDir", "GetUserDataFolder"):
        return (f"long long {name}(void *inst, char *buf, long long size) "
                f"{{ return write_buffer(buf, size, g_install_dir); }}")
    return f"long long {name}(void) {{ return 0; }}"


def parse_exports(shim):
    data = open(shim, "rb").read()
    if data[:2] != b"MZ":
        raise SystemExit(f"{shim}: not a PE file")
    pe = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    sizeopt = struct.unpack_from("<H", data, pe + 20)[0]
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    section_hdr = opt + sizeopt
    dd_off = opt + (112 if magic == 0x20b else 96)
    rva = struct.unpack_from("<I", data, dd_off)[0]

    def to_off(rva):
        for i in range(nsec):
            sh = section_hdr + i * 40
            vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, sh + 8)
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        raise SystemExit(f"cannot locate export dir rva={rva:#x}")

    off = to_off(rva)
    num_names = struct.unpack_from("<I", data, off + 24)[0]
    addr_names = struct.unpack_from("<I", data, off + 32)[0]
    addr_ords = struct.unpack_from("<I", data, off + 36)[0]
    names = to_off(addr_names)
    ords = to_off(addr_ords)
    names_out = []
    for i in range(num_names):
        na = struct.unpack_from("<I", data, names + 4 * i)[0]
        no = struct.unpack_from("<H", data, ords + 2 * i)[0]
        nm = data[to_off(na):to_off(na) + 256].split(b"\0")[0].decode()
        names_out.append((no, nm))
    names_out.sort()
    return [nm for _, nm in names_out]


if __name__ == "__main__":
    main()
