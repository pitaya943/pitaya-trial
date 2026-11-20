# tally

Split shared expenses in a group and see who owes whom. A small library with a command-line front end.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
.venv/bin/python -m pytest -q
PYTHONPATH=src python3 -m tally.cli --help
```

What it does today and what it should do next: [`docs/spec.md`](docs/spec.md).
