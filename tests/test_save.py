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
    with pytest.raises(OSError):
        save(_ledger("Ana", "Bo", "Cy"), path)
    monkeypatch.undo()

    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["tally.json"]
