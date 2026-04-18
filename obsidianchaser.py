#!/usr/bin/env python3
"""
ObsidianChaser
Converts an Obsidian Markdown chaser log to SOTA V2 CSV for upload to sotadata.org.uk

Your Obsidian note should have a header section at the top, then a Markdown table:

    Callsign: W6XYZ
    Grid: DM04

    | Date      | Freq    | Mode | Power | Time  | Station<br>Worked | ... | SOTA_REF  | Notes |
    | --------- | ------- | ---- | ----- | ----- | ----------------- | ... | --------- | ----- |
    | 3/1/2026  | 146.580 | FM   | 10    | 21:48 | KE6TH             | ... | W6/CT-025 |       |

Usage:
    python obsidianchaser.py --input "SOTA Log.md"
    python obsidianchaser.py --input "SOTA Log.md" --output my_chaser_log.csv

Upload the resulting CSV at:
    https://www.sotadata.org.uk/en/upload/chaser
"""

import argparse
import csv
import re
import sys
from pathlib import Path
from datetime import datetime


# ---------------------------------------------------------------------------
# Column name aliases
# Headers are lowercased and HTML-stripped before matching, so
# "Station<br>Worked" → "station worked", "Report<br>Sent" → "report sent", etc.
# Add your own heading variants here if needed.
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    "callsign":  ["callsign", "call", "station worked", "station", "dx"],
    "date":      ["date", "qso date", "day"],
    "time":      ["time", "time (utc)", "utc", "time utc", "qso time"],
    "frequency": ["frequency", "freq", "band", "frequency / band", "freq/band", "mhz"],
    "mode":      ["mode"],
    "sota_ref":  ["sota_ref", "their summit", "s2s", "s2s ref", "their sota",
                  "s2s summit", "chased summit"],
    "notes":     ["notes", "comments", "note", "comment", "remarks"],
    "rst_sent":  ["report sent", "rst sent", "sent", "rst_sent", "tx rst"],
    "rst_rcvd":  ["report rec'd", "report recd", "report rcvd", "rst rcvd",
                  "rcvd", "rst_rcvd", "rx rst"],
    "power":     ["power", "pwr", "watts", "tx power"],
}

REQUIRED_CANONICAL = ["callsign", "date", "time", "frequency", "mode", "sota_ref"]

MODE_MAP = {
    "ssb": "SSB", "usb": "SSB", "lsb": "SSB",
    "cw":  "CW",
    "fm":  "FM",
    "am":  "AM",
    "ft8": "FT8", "ft-8": "FT8",
    "ft4": "FT4", "ft-4": "FT4",
    "digi": "DATA", "digital": "DATA", "data": "DATA",
    "rtty": "RTTY",
    "psk31": "PSK31", "psk": "PSK31",
    "js8": "JS8",
}


# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

def parse_note_header(text: str) -> dict:
    """
    Parse key: value pairs from the top of the note (before the Markdown table).
    Recognises:
        Callsign: W6XYZ
        Grid: DM04
    Keys are case-insensitive. Stops at the first table row.
    """
    info = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            break  # reached the table
        m = re.match(r"^([A-Za-z _]+?)\s*:\s*(.+)$", stripped)
        if m:
            key = m.group(1).strip().lower()
            val = m.group(2).strip()
            info[key] = val
    return info


def extract_callsign(info: dict) -> str:
    for key in ("callsign", "call", "my callsign", "mycallsign"):
        if key in info:
            return info[key].upper()
    return None


def extract_grid(info: dict) -> str:
    for key in ("grid", "grid square", "locator", "gridsquare", "my grid"):
        if key in info:
            return info[key].upper()
    return None


# ---------------------------------------------------------------------------
# Markdown table parsing
# ---------------------------------------------------------------------------

def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def normalise_header(h: str) -> str:
    return re.sub(r"\s+", " ", strip_html(h).lower()).strip()


def resolve_columns(headers: list) -> dict:
    normalised = [normalise_header(h) for h in headers]
    resolved = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                resolved[canonical] = normalised.index(alias)
                break
    return resolved


def parse_markdown_table(text: str):
    lines = text.splitlines()
    table_lines = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            in_table = True
            table_lines.append(stripped)
        elif in_table:
            break

    if len(table_lines) < 3:
        raise ValueError(
            "Could not find a Markdown table with header, separator, and at least one data row."
        )

    def split_row(line):
        return [cell.strip() for cell in line.strip("|").split("|")]

    headers = split_row(table_lines[0])
    rows = [split_row(line) for line in table_lines[2:] if line.strip("|").strip()]
    return headers, rows


# ---------------------------------------------------------------------------
# Field normalisation
# ---------------------------------------------------------------------------

def normalise_date(raw: str) -> str:
    raw = raw.strip()
    formats = [
        "%m/%d/%Y",   # 3/15/2026  ← your format
        "%m/%d/%y",   # 3/15/26
        "%Y-%m-%d",   # 2026-03-15
        "%d/%m/%Y",   # 15/03/2026
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
        "%Y%m%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date format: '{raw}'")


def normalise_time(raw: str) -> str:
    raw = raw.strip().replace(":", "").replace("Z", "").replace("UTC", "").strip()
    if len(raw) == 4 and raw.isdigit():
        return raw
    if len(raw) == 6 and raw.isdigit():
        return raw[:4]
    raise ValueError(f"Unrecognised time format: '{raw}'")


def normalise_frequency(raw: str) -> str:
    raw = raw.strip().lower().replace("mhz", "").replace("khz", "k").strip()
    band_to_freq = {
        "160m": "1.850",  "80m":  "3.600",   "60m":  "5.355",
        "40m":  "7.100",  "30m":  "10.120",  "20m":  "14.200",
        "17m":  "18.100", "15m":  "21.200",  "12m":  "24.900",
        "10m":  "28.500", "6m":   "50.200",  "4m":   "70.200",
        "2m":   "144.300","70cm": "432.200", "23cm": "1296.200",
    }
    raw_clean = raw.replace(" ", "")
    if raw_clean in band_to_freq:
        return band_to_freq[raw_clean] + "MHz"
    try:
        val = float(raw_clean.replace("k", ""))
        if "k" in raw:
            val /= 1000
        return f"{val:.3f}MHz"
    except ValueError:
        pass
    raise ValueError(f"Unrecognised frequency/band: '{raw}'")


def normalise_mode(raw: str) -> str:
    return MODE_MAP.get(raw.strip().lower(), raw.strip().upper())


def normalise_summit(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if not re.match(r"^[A-Z0-9]+/[A-Z]+-\d{3}$", raw, re.IGNORECASE):
        print(f"  Warning: summit reference '{raw}' may be invalid", file=sys.stderr)
    return raw.upper()


# ---------------------------------------------------------------------------
# Record builder
# ---------------------------------------------------------------------------

def row_to_chaser_v2(row: list, col: dict, my_callsign: str) -> list:
    """
    Chaser V2 record:
    V2, chaser_call, summit_chased, date, time, freq, mode, activator_call, [s2s], [notes]
    """
    def get(canonical, default=""):
        idx = col.get(canonical)
        if idx is None or idx >= len(row):
            return default
        return row[idx].strip()

    activator = get("callsign")
    if not activator or activator in ("-", ""):
        return []  # skip blank rows

    sota_ref = normalise_summit(get("sota_ref"))
    if not sota_ref:
        raise ValueError(f"Missing SOTA_REF for contact with {activator}")

    return [
        "V2",
        my_callsign,
        sota_ref,
        normalise_date(get("date")),
        normalise_time(get("time")),
        normalise_frequency(get("frequency")),
        normalise_mode(get("mode")),
        activator.upper(),
        "",           # S2S ref (chaser logs don't use this)
        get("notes"),
    ]


# ---------------------------------------------------------------------------
# ADIF writer
# ---------------------------------------------------------------------------

def adif_field(name: str, value: str) -> str:
    """Encode a single ADIF field: <NAME:len>value"""
    return f"<{name}:{len(value)}>{value}"


def write_adif(records: list, out_path: Path, my_callsign: str, my_grid: str) -> None:
    """
    Write records as an ADIF ADI file (.adi).

    Records are the same list used for V2 CSV:
      [V2, my_callsign, sota_ref, date_DDMMYYYY, time_HHMM, freq_MHz, mode,
       activator, s2s, notes]

    ADIF fields written per QSO:
      CALL, QSO_DATE, TIME_ON, FREQ, MODE, SOTA_REF, MY_CALL,
      MY_GRIDSQUARE (if available), COMMENT (if non-empty)
    """
    lines = []

    # File header
    lines.append(adif_field("ADIF_VER", "3.1.4"))
    lines.append(adif_field("PROGRAMID", "ObsidianChaser"))
    lines.append("<EOH>")
    lines.append("")

    for r in records:
        # r[3] = DD/MM/YYYY  →  YYYYMMDD
        d = r[3]
        qso_date = d[6:10] + d[3:5] + d[0:2]

        # r[5] = "146.580MHz"  →  "146.580"
        freq = r[5].replace("MHz", "")

        fields = [
            adif_field("CALL",      r[7]),        # activator callsign
            adif_field("QSO_DATE",  qso_date),
            adif_field("TIME_ON",   r[4]),
            adif_field("FREQ",      freq),
            adif_field("MODE",      r[6]),
            adif_field("SOTA_REF",        r[2]),    # summit being chased
            adif_field("STATION_CALLSIGN", my_callsign),
        ]
        if my_grid:
            fields.append(adif_field("MY_GRIDSQUARE", my_grid))
        if r[9]:
            fields.append(adif_field("COMMENT", r[9]))
        fields.append("<EOR>")

        lines.append(" ".join(fields))
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ObsidianChaser — convert Obsidian chaser log to SOTA V2 CSV"
    )
    parser.add_argument("--input",  required=True,
                        help="Path to your Obsidian .md log file")
    parser.add_argument("--output", default=None,
                        help="Output filename (default: auto-generated from callsign)")
    parser.add_argument("--format", dest="fmt", choices=["csv", "adif"], default="csv",
                        help="Output format: csv (SOTA V2, default) or adif")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress all informational output")
    args = parser.parse_args()

    def log(*a, **kw):
        if not args.quiet:
            print(*a, **kw)

    md_path = Path(args.input)
    if not md_path.exists():
        print(f"Error: file not found: {md_path}", file=sys.stderr)
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")

    # --- Parse note header for callsign + grid ---
    info = parse_note_header(text)
    my_callsign = extract_callsign(info)
    my_grid     = extract_grid(info)

    if not my_callsign:
        print(
            "Error: could not find your callsign in the note header.\n"
            "Add a line like:  Callsign: W6XYZ",
            file=sys.stderr,
        )
        sys.exit(1)

    log(f"ObsidianChaser")
    log(f"  Callsign : {my_callsign}")
    log(f"  Grid     : {my_grid or '(not found — add Grid: DM04 to your note header)'}")
    log(f"  Input    : {md_path}")

    # --- Parse table ---
    try:
        headers, rows = parse_markdown_table(text)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    normalised_headers = [normalise_header(h) for h in headers]
    log(f"  QSOs     : {len(rows)}")
    log(f"  Columns  : {normalised_headers}")

    col = resolve_columns(headers)
    log(f"  Mapped   : {list(col.keys())}")

    missing = [c for c in REQUIRED_CANONICAL if c not in col]
    if missing:
        print(f"\nWarning: missing required columns: {missing}", file=sys.stderr)
        print("  Edit COLUMN_ALIASES at the top of this script to add your heading names.\n",
              file=sys.stderr)

    # --- Convert rows ---
    records = []
    errors  = []
    for i, row in enumerate(rows, start=1):
        try:
            record = row_to_chaser_v2(row, col, my_callsign)
            if record:
                records.append(record)
        except ValueError as e:
            errors.append((i, str(e)))

    if errors:
        print(f"\n{len(errors)} row(s) skipped due to errors:", file=sys.stderr)
        for row_num, msg in errors:
            print(f"  Row {row_num}: {msg}", file=sys.stderr)

    if not records:
        print("No valid records to write. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Sort chronologically — sotadata requires this
    # Sort chronologically. r[3] is DD/MM/YYYY — reorder to YYYYMMDD for correct
    # lexicographic comparison, then r[4] (HHMM) as tiebreaker.
    records.sort(key=lambda r: (r[3][6:10] + r[3][3:5] + r[3][0:2], r[4]))

    # --- Write output ---
    today = datetime.today().strftime("%Y%m%d")
    ext = "adi" if args.fmt == "adif" else "csv"
    default_name = f"{my_callsign}_ObsidianChaser_{today}.{ext}"

    out_path = Path(args.output) if args.output else Path(default_name)

    if args.fmt == "adif":
        write_adif(records, out_path, my_callsign, my_grid)
        log(f"\n  Wrote {len(records)} QSOs → {out_path}  (ADIF)")
        if my_grid:
            log(f"  MY_GRIDSQUARE: {my_grid} written to every QSO record.")
        else:
            log(f"  Note: no grid square found — add 'Grid: DM04' to your note header")
            log(f"  to have MY_GRIDSQUARE included in each ADIF record.")
        log(f"\n  Upload at: https://www.sotadata.org.uk/en/upload/chaser")
    else:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(records)
        log(f"\n  Wrote {len(records)} QSOs → {out_path}  (SOTA V2 CSV)")
        if my_grid:
            log(f"  Note: SOTA V2 CSV has no grid field — {my_grid} is already in")
            log(f"  your sotadata.org.uk profile. Use --format adif to embed it per QSO.")
        log(f"\n  Upload at: https://www.sotadata.org.uk/en/upload/chaser")
        log(f"\n  Sample output:")
        for r in records[:3]:
            log(f"    {','.join(r)}")


if __name__ == "__main__":
    main()
