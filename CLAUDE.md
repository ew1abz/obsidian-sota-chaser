# ObsidianChaser — Project Specification

## Purpose

ObsidianChaser converts an Obsidian Markdown chaser log into a SOTA V2 CSV file
ready for upload to [sotadata.org.uk](https://www.sotadata.org.uk/en/upload/chaser).

It is a single-file Python CLI tool with no external dependencies. It targets
**chasers only** — operators who work SOTA activators from home or portable
locations but are not themselves on a summit.

---

## Project Structure

```text
obsidianchaser/
├── obsidianchaser.py   # Main script (single-file, no dependencies)
├── CLAUDE.md           # This file
└── README.md           # User-facing documentation (to be created)
```

---

## Domain Concepts

### SOTA (Summits on the Air)

An amateur radio award programme where **activators** operate from designated
mountain summits and **chasers** contact them from anywhere. Both earn points
based on the summit's elevation.

Key references:

- SOTA database: <https://www.sotadata.org.uk>
- Chaser upload: <https://www.sotadata.org.uk/en/upload/chaser>
- Summit reference format: `AA/RR-NNN` e.g. `W6/CT-025`
  - `AA` = ITU association prefix (e.g. `W6` for California)
  - `RR` = region code (e.g. `CT` for Channel Islands / Coastal)
  - `NNN` = zero-padded 3-digit summit number

### SOTA V2 CSV Format

Each row is one QSO (contact). Fields are comma-separated:

```text
V2, my_callsign, sota_ref, date, time, frequency, mode, activator_callsign, [s2s_ref], [notes]
```

| Field | Format | Example |
|---|---|---|
| Version tag | Literal `V2` | `V2` |
| My callsign | Uppercase, no spaces | `W6XYZ` |
| SOTA ref | `AA/RR-NNN` uppercase | `W6/CT-025` |
| Date | `DD/MM/YYYY` | `01/03/2026` |
| Time | `HHMM` UTC 24h | `2148` |
| Frequency | `X.XXXMHz` | `146.580MHz` |
| Mode | See MODE_MAP | `FM` |
| Activator callsign | Uppercase, no spaces | `KE6TH` |
| S2S ref | Optional, blank for chasers | `` |
| Notes | Optional free text | `Rick` |

Rules enforced by sotadata:

- Records must be in **chronological order** (date then time)
- Callsigns must have **no spaces**
- Summit references must **exist** in the SOTA database
- Dates should use **international format** `DD/MM/YYYY`

### Grid Square

Maidenhead grid locator (e.g. `DM04`). The SOTA V2 CSV format does not include
a grid square field — it lives in the operator's sotadata.org.uk profile.
ObsidianChaser reads it from the note header for informational purposes only.

---

## Input: Obsidian Note Format

The script reads a single `.md` file. The note must have two sections:

### 1. Header Block (key: value pairs, before the table)

```text
Callsign: W6XYZ
Grid: DM04
```

- **Callsign** (required): the chaser's callsign. Parsed case-insensitively.
  Aliases: `call`, `my callsign`, `mycallsign`
- **Grid** (optional): Maidenhead locator. Informational only — not written to CSV.
  Aliases: `grid square`, `locator`, `gridsquare`, `my grid`

### 2. Markdown Table (first table found in the file)

```markdown
| Date      | Freq    | Mode | Power | Time  | Station<br>Worked | Report<br>Sent | Report<br>Rec'd | SOTA_REF  | Notes |
| --------- | ------- | ---- | ----- | ----- | ----------------- | -------------- | --------------- | --------- | ----- |
| 3/1/2026  | 146.580 | FM   | 10    | 21:48 | KE6TH             | 57             | 52              | W6/CT-025 |       |
```

Column headers are **case-insensitive** and **HTML-stripped** before matching,
so `Station<br>Worked` matches the same as `Station Worked` or `callsign`.

#### Column Aliases (COLUMN_ALIASES dict in source)

| Canonical name | Accepted headings |
|---|---|
| `callsign` | callsign, call, station worked, station, dx |
| `date` | date, qso date, day |
| `time` | time, time (utc), utc, time utc, qso time |
| `frequency` | frequency, freq, band, frequency / band, freq/band, mhz |
| `mode` | mode |
| `sota_ref` | sota_ref, their summit, s2s, s2s ref, their sota, s2s summit, chased summit |
| `notes` | notes, comments, note, comment, remarks |
| `rst_sent` | report sent, rst sent, sent, rst_sent, tx rst |
| `rst_rcvd` | report rec'd, report recd, report rcvd, rst rcvd, rcvd, rst_rcvd, rx rst |
| `power` | power, pwr, watts, tx power |

**Required columns:** `callsign`, `date`, `time`, `frequency`, `mode`, `sota_ref`

**Parsed but not written to CSV:** `rst_sent`, `rst_rcvd`, `power`
(sotadata does not include these in V2 chaser format)

---

## Field Normalisation Rules

### Date

Accepts multiple formats; outputs `DD/MM/YYYY`:

- `M/D/YYYY` (primary — matches user's Obsidian format e.g. `3/15/2026`)
- `M/D/YY`
- `YYYY-MM-DD`
- `DD/MM/YYYY`
- `DD-MM-YYYY`
- `YYYY/MM/DD`
- `DD Mon YYYY` / `DD Month YYYY`
- `YYYYMMDD`

### Time

Accepts `HH:MM`, `HHMM`, `HHMMSS` (seconds dropped). Outputs `HHMM`.
All times are assumed UTC.

### Frequency

Accepts MHz as a decimal number (`146.580`), band names (`2m`, `70cm`, `40m`),
or kHz with `k` suffix. Outputs `X.XXXMHz`.

Band → representative frequency mapping (used when exact frequency unknown):

| Band | Output |
|---|---|
| 160m | 1.850MHz |
| 80m | 3.600MHz |
| 40m | 7.100MHz |
| 20m | 14.200MHz |
| 2m | 144.300MHz |
| 70cm | 432.200MHz |
| *(etc.)* | |

### Mode (MODE_MAP)

| Input | Output |
|---|---|
| ssb, usb, lsb | SSB |
| cw | CW |
| fm | FM |
| am | AM |
| ft8, ft-8 | FT8 |
| ft4, ft-4 | FT4 |
| digi, digital, data | DATA |
| rtty | RTTY |
| psk31, psk | PSK31 |
| js8 | JS8 |
| *(anything else)* | uppercased as-is |

### Summit Reference

Validated against regex `^[A-Z0-9]+/[A-Z]+-\d{3}$`. A warning is printed to
stderr if the format looks wrong, but the value is still passed through
(sotadata itself will reject invalid references at upload time).

---

## CLI Interface

```bash
python obsidianchaser.py --input "SOTA Log.md" [--output FILE] [--format {csv,adif}] [--quiet]
```

| Argument | Required | Description |
|---|---|---|
| `--input` | Yes | Path to Obsidian `.md` log file |
| `--output` | No | Output path. Default: `<CALLSIGN>_ObsidianChaser_<YYYYMMDD>.<ext>` |
| `--format` | No | `csv` (default, SOTA V2) or `adif` (ADIF `.adi` with `MY_GRIDSQUARE`) |
| `--quiet`, `-q` | No | Suppress informational stdout; errors still go to stderr |

Callsign and grid are read from the note header — they are **not** CLI arguments.

### Exit codes

- `0` — success
- `1` — fatal error (file not found, no callsign in header, no valid records)

---

## Output

Two formats are supported, both sorted chronologically:

- **SOTA V2 CSV** (default, `.csv`) — ready to drag-and-drop at
  <https://www.sotadata.org.uk/en/upload/chaser>
- **ADIF** (`--format adif`, `.adi`) — includes `MY_GRIDSQUARE` per QSO;
  compatible with LoTW, eQSL, Cloudlog, and other logbook programs.

Default filename: `<CALLSIGN>_ObsidianChaser_<YYYYMMDD>.<ext>`

Rows with errors (unrecognised date, missing SOTA_REF, etc.) are **skipped**
with a stderr warning rather than aborting the whole run.

---

## Design Decisions & Constraints

- **Single file, stdlib only.** No pip install required — just Python 3.9+.
- **Chaser-only.** Activator support was explicitly out-of-scope for this project.
  A separate tool or `--mode activator` flag could be added later if needed.
- **First table wins.** The script parses the first Markdown table it finds.
  Multi-table notes are not supported; put the log in a dedicated note.
- **All activations in one table.** The table may contain QSOs from different
  dates/summits — the script does not filter by summit. Upload the resulting
  CSV as a chaser log covering all contacts.
- **HTML tags in headers are stripped.** Obsidian renders `<br>` in table
  headers for line breaks; the script normalises these transparently.
- **Grid square in ADIF, not CSV.** SOTA V2 CSV has no grid field (sotadata
  reads it from the operator's profile). ADIF output writes `MY_GRIDSQUARE`
  to every QSO record for use with LoTW, eQSL, and other logbook programs.
- **Chronological sort is enforced.** sotadata rejects out-of-order logs.
  The script sorts by date then time before writing.
- **RST reports and power are not written to CSV.** The SOTA V2 chaser format
  has no fields for these. They may be kept in the Obsidian table for the
  operator's own records.

---

## Known Limitations / Future Work

- No automated upload (sotadata does not offer an open write API without a
  registered client_id). Upload remains a manual web-form step.
- Date format ambiguity: `3/4/2026` is parsed as March 4 (M/D/YYYY) not April 3.
  If the operator uses DD/MM/YYYY exclusively, the order of formats in
  `normalise_date()` should be swapped.
- No support for multiple tables in one note (e.g. one table per activation).
- No duplicate detection — re-running on the same file will produce duplicate
  records if uploaded multiple times.
- S2S (summit-to-summit) from the chaser side is not applicable and the field
  is always left blank. If a chaser is also activating (combined SOTA/POTA
  etc.), a separate activator upload workflow would be needed.

---

## Testing

Run the unit test suite (80 tests, stdlib `unittest` + `pytest`):

```bash
python -m pytest test_obsidianchaser.py -v
# or without pytest:
python -m unittest test_obsidianchaser.py -v
```

For a quick manual smoke-test:

```bash
cat > test_log.md << 'EOF'
Callsign: W6XYZ
Grid: DM04

| Date      | Freq    | Mode | Power | Time  | Station<br>Worked | Report<br>Sent | Report<br>Rec'd | SOTA_REF  | Notes |
| --------- | ------- | ---- | ----- | ----- | ----------------- | -------------- | --------------- | --------- | ----- |
| 3/1/2026  | 146.580 | FM   | 10    | 21:48 | KE6TH             | 57             | 52              | W6/CT-025 |       |
| 3/15/2026 | 146.580 | FM   | 10    | 16:45 | kn6cqx            | 57             | 57              | W6/CT-076 | Rick  |
EOF

python obsidianchaser.py --input test_log.md --output test_out.csv
cat test_out.csv
# Expected:
# V2,W6XYZ,W6/CT-025,01/03/2026,2148,146.580MHz,FM,KE6TH,,
# V2,W6XYZ,W6/CT-076,15/03/2026,1645,146.580MHz,FM,KN6CQX,,Rick

python obsidianchaser.py --input test_log.md --output test_out.adi --format adif
cat test_out.adi
# Each QSO record includes MY_GRIDSQUARE:4>DM04
```

---

## References

- SOTA V2 CSV format spec: <https://www.sotadata.org.uk/en/upload/activator/csv/info>
- SOTA chaser upload: <https://www.sotadata.org.uk/en/upload/chaser>
- SOTA Reflector (community forum): <https://reflector.sota.org.uk>
- Maidenhead grid locator: <https://www.qrz.com/gridmapper>
