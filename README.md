# ObsidianChaser 🏔️

Convert an [Obsidian](https://obsidian.md) Markdown chaser log into a **SOTA V2 CSV**
file ready to upload at [sotadata.org.uk][chaser-upload].

[chaser-upload]: https://www.sotadata.org.uk/en/upload/chaser

- **No dependencies** — pure Python 3.9+, stdlib only
- **Chaser logs only** — for operators who work SOTA activators from home or portable
- **Single file** — just `obsidianchaser.py`

---

## Quick Start

```bash
# SOTA V2 CSV (for sotadata upload)
python obsidianchaser.py --input "SOTA Log.md"

# ADIF (includes MY_GRIDSQUARE — for LoTW, eQSL, Cloudlog, etc.)
python obsidianchaser.py --input "SOTA Log.md" --format adif
```

This reads your Obsidian note and writes a file named
`<CALLSIGN>_ObsidianChaser_<YYYYMMDD>.<ext>` in the current directory, e.g.
`W6XYZ_ObsidianChaser_20260315.csv`. Then drag and drop the file at
[sotadata.org.uk/en/upload/chaser](https://www.sotadata.org.uk/en/upload/chaser).

---

## Obsidian Note Format

Your note needs two things: a **header block** and a **Markdown table**.

### Header block (before the table)

```text
Callsign: W6XYZ
Grid: DM04
```

| Key | Required | Notes |
| --- | --- | --- |
| `Callsign` | Yes | Also accepted: `Call`, `My Callsign` |
| `Grid` | No | Maidenhead locator — informational only, not written to CSV |

### Log table

```markdown
| Date      | Freq    | Mode | Power | Time  | Station<br>Worked | Report<br>Sent | Report<br>Rec'd | SOTA_REF  | Notes |
| --------- | ------- | ---- | ----- | ----- | ----------------- | -------------- | --------------- | --------- | ----- |
| 3/1/2026  | 146.580 | FM   | 10    | 21:48 | KE6TH             | 57             | 52              | W6/CT-025 |       |
| 3/15/2026 | 146.580 | FM   | 10    | 16:45 | kn6cqx            | 57             | 57              | W6/CT-076 | Rick  |
```

**Required columns:** `Date`, `Time`, `Freq`, `Mode`, `Station Worked`, `SOTA_REF`

Column headers are **case-insensitive** and HTML tags like `<br>` are stripped
automatically, so Obsidian's multi-line headers work out of the box.

---

## Usage

```bash
python obsidianchaser.py --input INPUT [--output OUTPUT] [--format {csv,adif}] [--quiet]
```

| Argument | Required | Description |
| --- | --- | --- |
| `--input` | Yes | Path to your Obsidian `.md` log file |
| `--output` | No | Output filename. Default: `<CALLSIGN>_ObsidianChaser_<YYYYMMDD>.<ext>` |
| `--format` | No | `csv` (default) for SOTA V2 CSV, or `adif` for ADIF `.adi` |
| `--quiet`, `-q` | No | Suppress all informational output (errors still go to stderr) |

### Examples

```bash
# SOTA V2 CSV — default output: W6XYZ_ObsidianChaser_20260315.csv
python obsidianchaser.py --input "SOTA Log.md"

# ADIF — default output: W6XYZ_ObsidianChaser_20260315.adi
python obsidianchaser.py --input "SOTA Log.md" --format adif

# Custom output path
python obsidianchaser.py --input "SOTA Log.md" --output my_chaser_log.csv

# Silent — useful in scripts
python obsidianchaser.py --input "SOTA Log.md" -q
```

---

## Output Formats

### SOTA V2 CSV (default)

Sorted chronologically, ready to upload to sotadata:

```text
V2,W6XYZ,W6/CT-025,01/03/2026,2148,146.580MHz,FM,KE6TH,,
V2,W6XYZ,W6/CT-076,15/03/2026,1645,146.580MHz,FM,KN6CQX,,Rick
```

Fields: `V2, chaser_call, summit_ref, date, time, frequency, mode,`
`activator_call, s2s_ref, notes`

### ADIF (`--format adif`)

Standard ham radio interchange format. Use this if you also want to upload
to LoTW, eQSL, Cloudlog, or any other logbook program. Includes
`MY_GRIDSQUARE` per QSO (requires `Grid:` in your note header).

```text
<ADIF_VER:5>3.1.4
<PROGRAMID:14>ObsidianChaser
<EOH>

<CALL:5>KE6TH <QSO_DATE:8>20260301 <TIME_ON:4>2148 <FREQ:7>146.580 <MODE:2>FM <SOTA_REF:9>W6/CT-025 <MY_CALL:5>W6XYZ <MY_GRIDSQUARE:4>DM04 <EOR>
<CALL:6>KN6CQX <QSO_DATE:8>20260315 <TIME_ON:4>1645 <FREQ:7>146.580 <MODE:2>FM <SOTA_REF:9>W6/CT-076 <MY_CALL:5>W6XYZ <MY_GRIDSQUARE:4>DM04 <COMMENT:4>Rick <EOR>
```

---

## Accepted Field Formats

### Date

Any of these are recognised and normalised to `DD/MM/YYYY`:

| Input | Interpretation |
| --- | --- |
| `3/15/2026` | M/D/YYYY (default — matches Obsidian's date picker) |
| `2026-03-15` | ISO 8601 |
| `15/03/2026` | DD/MM/YYYY |
| `15 Mar 2026` | DD Mon YYYY |

> **Note:** Ambiguous dates like `3/4/2026` are parsed as **March 4** (M/D/YYYY).
> If you log in DD/MM/YYYY order, edit the `formats` list in `normalise_date()`.

### Time

Accepts `21:48`, `2148`, or `214800` (seconds dropped). All times are assumed UTC.

### Frequency

Accepts MHz as a decimal (`146.580`), band names (`2m`, `40m`, `70cm`),
or kHz with `k` suffix (`14200k`).

| Band input | CSV output |
| --- | --- |
| `2m` | `144.300MHz` |
| `70cm` | `432.200MHz` |
| `40m` | `7.100MHz` |
| `146.58` | `146.580MHz` |

### Mode

| Input | CSV output |
| --- | --- |
| `SSB`, `USB`, `LSB` | `SSB` |
| `CW` | `CW` |
| `FM` | `FM` |
| `FT8`, `FT-8` | `FT8` |
| `FT4`, `FT-4` | `FT4` |
| `DIGI`, `Digital`, `Data` | `DATA` |

Anything unrecognised is passed through uppercased.

---

## Column Name Aliases

The script understands a wide range of column heading variants. If your table
uses a different heading, add it to `COLUMN_ALIASES` at the top of the script.

| Canonical | Accepted headings |
| --- | --- |
| `callsign` | callsign, call, station worked, station, dx |
| `sota_ref` | sota_ref, their summit, s2s ref, chased summit |
| `frequency` | frequency, freq, band, MHz |
| `time` | time, utc, time utc, qso time |
| `notes` | notes, comments, remarks |

---

## What Gets Written

| Column | CSV | ADIF | Notes |
| --- | --- | --- | --- |
| Date, Time, Freq, Mode | Yes | Yes | Normalised |
| Callsign (activator) | Yes | Yes | Uppercased |
| SOTA_REF | Yes | Yes | Validated for format |
| Notes | Yes | Yes | Passed through as-is |
| My callsign | Yes | Yes | From note header |
| My grid square | **No** | **Yes** (`MY_GRIDSQUARE`) | Requires `Grid:` in header |
| RST Sent / Received | **No** | **No** | Not in SOTA V2 chaser format |
| Power | **No** | **No** | Not in SOTA V2 chaser format |

---

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | Fatal error (file not found, no callsign, no valid records) |

Rows with errors (bad date, missing summit ref, etc.) are **skipped with a warning**
rather than aborting the run.

---

## Limitations

- **First table wins.** Only the first Markdown table in the note is processed.
- **No duplicate detection.** Re-running on the same file and uploading again will
  create duplicates in sotadata.
- **No automated upload.** sotadata does not offer a public write API.
  Upload is a manual drag-and-drop step.
- **Chaser only.** If you are also activating 🏔️, use a separate activator log tool.

---

## Requirements

- Python 3.9+
- No external packages

---

## License

MIT
