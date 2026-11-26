# Scientific figures

Install the optional plotting dependencies in a project-local environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-figures.txt
./bin/dramdpnd figures RUN_ID
```

The tested environment uses Matplotlib 3.11.2. Figure generation requires `VALID` version 2 evidence and writes a new directory under `runs/derived/RUN_ID/`. It leaves the original run and previous figure directories untouched.

The generator exports command distribution and logical bank activity in SVG, PDF and PNG. CSV files retain the full counts. `measurements.json` and `figure_metadata.json` record the measurement definitions, source metadata hash and SHA-256 hashes of the outputs. The count axes use integer ticks. The bank plot shows at most 20 categories; its CSV includes every observed logical bank. Bank labels are logical identifiers, not physical die positions.

For example, WMB run `20261125T015002Z-8747a8` contains 96 issued-command records, including 32 ACT records. Its local figures are in `runs/derived/20261125T015002Z-8747a8/20261125T020329Z-5100bb/`. These are exploratory measurements from a recorded run, not synthetic figures or published paper results. The output remains ignored until reviewed for publication.
