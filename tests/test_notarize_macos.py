import base64
import notarize_macos as module
import pytest
import stat
from pathlib import Path

KEY_BYTES = b"-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n"
API_ENV = {
    "APPLE_API_KEY": "KEYID12345",
    "APPLE_API_ISSUER": "11111111-2222-3333-4444-555555555555",
    "APPLE_API_KEY_B64": base64.b64encode(KEY_BYTES).decode(),
}


class Recorder:
    def __init__(self, code=0):
        self.code = code
        self.calls = []
        self.key_text = None
        self.key_mode = None

    def __call__(self, argv):
        self.calls.append(argv)
        if "--key" in argv:
            key = Path(argv[argv.index("--key") + 1])
            self.key_text = key.read_bytes()
            self.key_mode = stat.S_IMODE(key.stat().st_mode)
        return self.code


def test_a_keychain_profile_is_passed_through(tmp_path):
    run = Recorder()
    code = module.submit(tmp_path / "pkg.zip", {"NOTARY_PROFILE": "mine"}, run)
    assert code == 0
    assert run.calls == [["xcrun", "notarytool", "submit", str(tmp_path / "pkg.zip"), "--keychain-profile", "mine", "--wait"]]


def test_an_api_key_is_decoded_to_a_private_file_and_removed_afterwards(tmp_path):
    run = Recorder()
    module.submit(tmp_path / "pkg.zip", API_ENV, run)
    argv = run.calls[0]
    assert argv[:4] == ["xcrun", "notarytool", "submit", str(tmp_path / "pkg.zip")]
    assert argv[argv.index("--key-id") + 1] == "KEYID12345"
    assert argv[argv.index("--issuer") + 1] == API_ENV["APPLE_API_ISSUER"]
    assert argv[-1] == "--wait"
    assert run.key_text == KEY_BYTES
    assert run.key_mode == 0o600
    assert not Path(argv[argv.index("--key") + 1]).exists()


def test_the_key_file_is_removed_when_the_submission_fails(tmp_path):
    class Boom(Recorder):
        def __call__(self, argv):
            super().__call__(argv)
            raise RuntimeError("network")

    run = Boom()
    with pytest.raises(RuntimeError):
        module.submit(tmp_path / "pkg.zip", API_ENV, run)
    assert not Path(run.calls[0][run.calls[0].index("--key") + 1]).exists()


def test_a_profile_wins_over_an_api_key(tmp_path):
    run = Recorder()
    module.submit(tmp_path / "pkg.zip", {**API_ENV, "NOTARY_PROFILE": "mine"}, run)
    assert "--keychain-profile" in run.calls[0]
    assert "--key" not in run.calls[0]


def test_missing_credentials_name_what_to_set(tmp_path):
    with pytest.raises(module.NotarizeError, match="NOTARY_PROFILE.*APPLE_API_KEY"):
        module.submit(tmp_path / "pkg.zip", {"APPLE_API_KEY": "only-one"}, Recorder())


def test_the_exit_code_of_notarytool_is_returned(tmp_path):
    assert module.submit(tmp_path / "pkg.zip", {"NOTARY_PROFILE": "mine"}, Recorder(code=1)) == 1
