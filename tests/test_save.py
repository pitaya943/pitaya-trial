"""Atomic save (T-004): `cli.save` writes a temp file in the same directory and renames it over the ledger."""

import io
import json
import os
import stat

import pytest

from tally.cli import load, save
from tally.ledger import Ledger


def _ledger(*names: str) -> Ledger:
    ledger = Ledger()
    for name in names:
        ledger.add_member(name)
    return ledger


class _HalfThenFail:
    """A writable file that passes on the first half of the first write, then raises OSError.

    Wraps the real file so the half really reaches the disk: a non-atomic save would leave
    the ledger truncated to that half, which is what the test must catch.
    """

    def __init__(self, real):
        self._real = real

    def write(self, data):
        self._real.write(data[: len(data) // 2])
        self._real.flush()
        raise OSError(28, "No space left on device")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._real.close()
        return False

    def __getattr__(self, name):
        return getattr(self._real, name)


def _fail_writes_in(directory, monkeypatch):
    """Make every file opened for writing in `directory` fail half-way through its first write.

    Patches `io.open`, which both `Path.write_text` and `os.fdopen` go through, so the same
    fault hits today's direct write and a temp-file write; files elsewhere are untouched.
    """
    real_open = io.open

    def fake_open(file, mode="r", *args, **kwargs):
        f = real_open(file, mode, *args, **kwargs)
        if any(c in mode for c in "wax+"):
            # `file` is a path or, through os.fdopen, a descriptor: resolve either to its directory.
            where = os.path.realpath(f"/proc/self/fd/{file}") if isinstance(file, int) else os.fspath(file)
            if os.path.dirname(os.path.realpath(where)) == os.path.realpath(directory):
                return _HalfThenFail(f)
        return f

    monkeypatch.setattr(io, "open", fake_open)


def test_failed_save_leaves_the_old_file_intact(tmp_path, monkeypatch):
    path = tmp_path / "tally.json"
    save(_ledger("Ana"), path)
    before = path.read_bytes()

    _fail_writes_in(tmp_path, monkeypatch)
    with pytest.raises(OSError) as raised:
        save(_ledger("Ana", "Bo", "Cy"), path)
    monkeypatch.undo()

    # The injected fault itself must come out, not some other OSError that save raised in its place.
    assert (raised.value.errno, raised.value.strerror) == (28, "No space left on device")

    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tally.json"]


def test_save_replaces_the_file_and_leaves_no_temp_file(tmp_path):
    # Over an existing file: full new content, the file's own mode kept. 0o640 differs from both
    # mkstemp's 0o600 and the usual umask default 0o644, so neither default can pass by accident.
    path = tmp_path / "tally.json"
    save(_ledger("Ana"), path)
    os.chmod(path, 0o640)
    new = _ledger("Ana", "Bo", "Cy")
    save(new, path)
    assert path.read_text() == json.dumps(new.to_dict(), indent=2) + "\n"
    assert load(path).to_dict() == new.to_dict()
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tally.json"]

    # To a path with no file: the file is created, and still no temp file is left.
    fresh = tmp_path / "sub" / "new.json"
    fresh.parent.mkdir()
    save(new, fresh)
    assert load(fresh).to_dict() == new.to_dict()
    assert sorted(p.name for p in fresh.parent.iterdir()) == ["new.json"]
