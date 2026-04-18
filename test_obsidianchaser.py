#!/usr/bin/env python3
"""
Unit tests for obsidianchaser.py
Run with:  python -m pytest test_obsidianchaser.py -v
       or: python -m unittest test_obsidianchaser.py -v
"""

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

# Import the module under test
import obsidianchaser as oc


# ---------------------------------------------------------------------------
# Date normalisation
# ---------------------------------------------------------------------------

class TestNormaliseDate(unittest.TestCase):

    def test_m_d_yyyy(self):
        self.assertEqual(oc.normalise_date("3/15/2026"), "15/03/2026")

    def test_m_d_yyyy_single_digit_month(self):
        self.assertEqual(oc.normalise_date("1/5/2026"), "05/01/2026")

    def test_m_d_yy(self):
        self.assertEqual(oc.normalise_date("3/15/26"), "15/03/2026")

    def test_iso_8601(self):
        self.assertEqual(oc.normalise_date("2026-03-15"), "15/03/2026")

    def test_dd_mm_yyyy(self):
        self.assertEqual(oc.normalise_date("15/03/2026"), "15/03/2026")

    def test_dd_mon_yyyy(self):
        self.assertEqual(oc.normalise_date("15 Mar 2026"), "15/03/2026")

    def test_dd_month_yyyy(self):
        self.assertEqual(oc.normalise_date("15 March 2026"), "15/03/2026")

    def test_yyyymmdd(self):
        self.assertEqual(oc.normalise_date("20260315"), "15/03/2026")

    def test_whitespace_stripped(self):
        self.assertEqual(oc.normalise_date("  3/1/2026  "), "01/03/2026")

    def test_unrecognised_raises(self):
        with self.assertRaises(ValueError):
            oc.normalise_date("not-a-date")


# ---------------------------------------------------------------------------
# Time normalisation
# ---------------------------------------------------------------------------

class TestNormaliseTime(unittest.TestCase):

    def test_hh_mm(self):
        self.assertEqual(oc.normalise_time("21:48"), "2148")

    def test_hhmm(self):
        self.assertEqual(oc.normalise_time("2148"), "2148")

    def test_hhmmss(self):
        self.assertEqual(oc.normalise_time("214800"), "2148")

    def test_midnight(self):
        self.assertEqual(oc.normalise_time("00:00"), "0000")

    def test_with_z_suffix(self):
        self.assertEqual(oc.normalise_time("2148Z"), "2148")

    def test_with_utc_suffix(self):
        self.assertEqual(oc.normalise_time("2148UTC"), "2148")

    def test_unrecognised_raises(self):
        with self.assertRaises(ValueError):
            oc.normalise_time("9pm")


# ---------------------------------------------------------------------------
# Frequency normalisation
# ---------------------------------------------------------------------------

class TestNormaliseFrequency(unittest.TestCase):

    def test_mhz_decimal(self):
        self.assertEqual(oc.normalise_frequency("146.580"), "146.580MHz")

    def test_mhz_with_suffix(self):
        self.assertEqual(oc.normalise_frequency("146.580MHz"), "146.580MHz")

    def test_mhz_with_suffix_lower(self):
        self.assertEqual(oc.normalise_frequency("146.580mhz"), "146.580MHz")

    def test_khz_suffix(self):
        self.assertEqual(oc.normalise_frequency("14200k"), "14.200MHz")

    def test_band_2m(self):
        self.assertEqual(oc.normalise_frequency("2m"), "144.300MHz")

    def test_band_70cm(self):
        self.assertEqual(oc.normalise_frequency("70cm"), "432.200MHz")

    def test_band_40m(self):
        self.assertEqual(oc.normalise_frequency("40m"), "7.100MHz")

    def test_band_20m(self):
        self.assertEqual(oc.normalise_frequency("20m"), "14.200MHz")

    def test_band_case_insensitive(self):
        self.assertEqual(oc.normalise_frequency("2M"), "144.300MHz")

    def test_integer_mhz(self):
        self.assertEqual(oc.normalise_frequency("146"), "146.000MHz")

    def test_unrecognised_raises(self):
        with self.assertRaises(ValueError):
            oc.normalise_frequency("microwave")


# ---------------------------------------------------------------------------
# Mode normalisation
# ---------------------------------------------------------------------------

class TestNormaliseMode(unittest.TestCase):

    def test_fm(self):
        self.assertEqual(oc.normalise_mode("FM"), "FM")

    def test_fm_lower(self):
        self.assertEqual(oc.normalise_mode("fm"), "FM")

    def test_usb_to_ssb(self):
        self.assertEqual(oc.normalise_mode("USB"), "SSB")

    def test_lsb_to_ssb(self):
        self.assertEqual(oc.normalise_mode("lsb"), "SSB")

    def test_cw(self):
        self.assertEqual(oc.normalise_mode("cw"), "CW")

    def test_ft8(self):
        self.assertEqual(oc.normalise_mode("ft8"), "FT8")

    def test_ft8_hyphen(self):
        self.assertEqual(oc.normalise_mode("FT-8"), "FT8")

    def test_ft4_hyphen(self):
        self.assertEqual(oc.normalise_mode("ft-4"), "FT4")

    def test_digi_to_data(self):
        self.assertEqual(oc.normalise_mode("digi"), "DATA")

    def test_digital_to_data(self):
        self.assertEqual(oc.normalise_mode("Digital"), "DATA")

    def test_unknown_uppercased(self):
        self.assertEqual(oc.normalise_mode("olivia"), "OLIVIA")

    def test_rtty(self):
        self.assertEqual(oc.normalise_mode("rtty"), "RTTY")

    def test_psk31(self):
        self.assertEqual(oc.normalise_mode("psk31"), "PSK31")


# ---------------------------------------------------------------------------
# Summit reference normalisation
# ---------------------------------------------------------------------------

class TestNormaliseSummit(unittest.TestCase):

    def test_valid_ref(self):
        self.assertEqual(oc.normalise_summit("W6/CT-025"), "W6/CT-025")

    def test_lowercased_input(self):
        self.assertEqual(oc.normalise_summit("w6/ct-025"), "W6/CT-025")

    def test_empty_returns_empty(self):
        self.assertEqual(oc.normalise_summit(""), "")

    def test_invalid_prints_warning(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            result = oc.normalise_summit("INVALID")
        self.assertEqual(result, "INVALID")
        self.assertIn("Warning", stderr.getvalue())


# ---------------------------------------------------------------------------
# Note header parsing
# ---------------------------------------------------------------------------

class TestParseNoteHeader(unittest.TestCase):

    def test_callsign_extracted(self):
        text = "Callsign: W6XYZ\nGrid: DM04\n"
        info = oc.parse_note_header(text)
        self.assertEqual(oc.extract_callsign(info), "W6XYZ")

    def test_callsign_alias_call(self):
        info = oc.parse_note_header("Call: KN6ABC\n")
        self.assertEqual(oc.extract_callsign(info), "KN6ABC")

    def test_callsign_uppercased(self):
        info = oc.parse_note_header("Callsign: kn6abc\n")
        self.assertEqual(oc.extract_callsign(info), "KN6ABC")

    def test_grid_extracted(self):
        info = oc.parse_note_header("Callsign: W6XYZ\nGrid: DM04\n")
        self.assertEqual(oc.extract_grid(info), "DM04")

    def test_grid_alias_locator(self):
        info = oc.parse_note_header("Locator: DM04\n")
        self.assertEqual(oc.extract_grid(info), "DM04")

    def test_no_callsign_returns_none(self):
        info = oc.parse_note_header("Grid: DM04\n")
        self.assertIsNone(oc.extract_callsign(info))

    def test_stops_at_table(self):
        text = "Callsign: W6XYZ\n| Date | Time |\n| --- | --- |\nCallsign: FAKE\n"
        info = oc.parse_note_header(text)
        self.assertEqual(oc.extract_callsign(info), "W6XYZ")


# ---------------------------------------------------------------------------
# Markdown table parsing
# ---------------------------------------------------------------------------

class TestParseMarkdownTable(unittest.TestCase):

    SAMPLE = """\
Callsign: W6XYZ

| Date     | Freq    | Mode | Time  | Station Worked | SOTA_REF  | Notes |
| -------- | ------- | ---- | ----- | -------------- | --------- | ----- |
| 3/1/2026 | 146.580 | FM   | 21:48 | KE6TH          | W6/CT-025 |       |
"""

    def test_headers_parsed(self):
        headers, _ = oc.parse_markdown_table(self.SAMPLE)
        self.assertIn("Date", headers)
        self.assertIn("SOTA_REF", headers)

    def test_row_count(self):
        _, rows = oc.parse_markdown_table(self.SAMPLE)
        self.assertEqual(len(rows), 1)

    def test_cell_values(self):
        _, rows = oc.parse_markdown_table(self.SAMPLE)
        self.assertEqual(rows[0][0], "3/1/2026")

    def test_html_br_in_header(self):
        text = """\
| Station<br>Worked | SOTA_REF |
| ------------------ | -------- |
| KE6TH              | W6/CT-025 |
"""
        headers, _ = oc.parse_markdown_table(text)
        col = oc.resolve_columns(headers)
        self.assertIn("callsign", col)

    def test_missing_table_raises(self):
        with self.assertRaises(ValueError):
            oc.parse_markdown_table("No table here\n")


# ---------------------------------------------------------------------------
# Column resolution
# ---------------------------------------------------------------------------

class TestResolveColumns(unittest.TestCase):

    def test_canonical_names(self):
        headers = ["Date", "Freq", "Mode", "Time", "Callsign", "SOTA_REF", "Notes"]
        col = oc.resolve_columns(headers)
        self.assertEqual(col["date"], 0)
        self.assertEqual(col["frequency"], 1)
        self.assertEqual(col["mode"], 2)
        self.assertEqual(col["time"], 3)
        self.assertEqual(col["callsign"], 4)
        self.assertEqual(col["sota_ref"], 5)
        self.assertEqual(col["notes"], 6)

    def test_alias_station_worked(self):
        headers = ["Station Worked", "SOTA_REF", "Date", "Time", "Freq", "Mode"]
        col = oc.resolve_columns(headers)
        self.assertIn("callsign", col)
        self.assertEqual(col["callsign"], 0)

    def test_missing_column_absent(self):
        col = oc.resolve_columns(["Date", "Mode"])
        self.assertNotIn("callsign", col)


# ---------------------------------------------------------------------------
# Row → V2 CSV record
# ---------------------------------------------------------------------------

class TestRowToChaserV2(unittest.TestCase):

    HEADERS = ["Date", "Freq", "Mode", "Time", "Station Worked", "SOTA_REF", "Notes"]
    COL = oc.resolve_columns(HEADERS)

    def _row(self, date="3/1/2026", freq="146.580", mode="FM", time="21:48",
             callsign="KE6TH", sota_ref="W6/CT-025", notes=""):
        return [date, freq, mode, time, callsign, sota_ref, notes]

    def test_basic_record(self):
        r = oc.row_to_chaser_v2(self._row(), self.COL, "W6XYZ")
        self.assertEqual(r[0], "V2")
        self.assertEqual(r[1], "W6XYZ")
        self.assertEqual(r[2], "W6/CT-025")
        self.assertEqual(r[3], "01/03/2026")
        self.assertEqual(r[4], "2148")
        self.assertEqual(r[5], "146.580MHz")
        self.assertEqual(r[6], "FM")
        self.assertEqual(r[7], "KE6TH")
        self.assertEqual(r[8], "")   # S2S blank for chasers
        self.assertEqual(r[9], "")   # notes

    def test_activator_uppercased(self):
        r = oc.row_to_chaser_v2(self._row(callsign="kn6cqx"), self.COL, "W6XYZ")
        self.assertEqual(r[7], "KN6CQX")

    def test_notes_preserved(self):
        r = oc.row_to_chaser_v2(self._row(notes="Rick"), self.COL, "W6XYZ")
        self.assertEqual(r[9], "Rick")

    def test_blank_callsign_returns_empty(self):
        r = oc.row_to_chaser_v2(self._row(callsign=""), self.COL, "W6XYZ")
        self.assertEqual(r, [])

    def test_missing_sota_ref_raises(self):
        with self.assertRaises(ValueError):
            oc.row_to_chaser_v2(self._row(sota_ref=""), self.COL, "W6XYZ")


# ---------------------------------------------------------------------------
# ADIF field encoder
# ---------------------------------------------------------------------------

class TestAdifField(unittest.TestCase):

    def test_basic(self):
        self.assertEqual(oc.adif_field("CALL", "KE6TH"), "<CALL:5>KE6TH")

    def test_empty_value(self):
        self.assertEqual(oc.adif_field("COMMENT", ""), "<COMMENT:0>")

    def test_length_matches_value(self):
        value = "W6/CT-025"
        result = oc.adif_field("SOTA_REF", value)
        self.assertEqual(result, f"<SOTA_REF:{len(value)}>{value}")


# ---------------------------------------------------------------------------
# ADIF file writing
# ---------------------------------------------------------------------------

class TestWriteAdif(unittest.TestCase):

    # V2 CSV record structure:
    # [V2, my_call, sota_ref, date_DDMMYYYY, time_HHMM, freq_MHz, mode, activator, s2s, notes]
    RECORDS = [
        ["V2", "W6XYZ", "W6/CT-025", "01/03/2026", "2148", "146.580MHz", "FM", "KE6TH", "", ""],
        ["V2", "W6XYZ", "W6/CT-076", "15/03/2026", "1645", "146.580MHz", "FM", "KN6CQX", "", "Rick"],
    ]

    def _write(self, grid="DM04"):
        with tempfile.NamedTemporaryFile(suffix=".adi", delete=False, mode="w") as f:
            path = Path(f.name)
        try:
            oc.write_adif(self.RECORDS, path, "W6XYZ", grid)
            return path.read_text(encoding="utf-8")
        finally:
            path.unlink(missing_ok=True)

    def test_adif_header_present(self):
        content = self._write()
        self.assertIn("<ADIF_VER:5>3.1.4", content)
        self.assertIn("<PROGRAMID:14>ObsidianChaser", content)
        self.assertIn("<EOH>", content)

    def test_eor_per_record(self):
        content = self._write()
        self.assertEqual(content.count("<EOR>"), 2)

    def test_date_converted_to_yyyymmdd(self):
        content = self._write()
        self.assertIn("<QSO_DATE:8>20260301", content)
        self.assertIn("<QSO_DATE:8>20260315", content)

    def test_freq_no_mhz_suffix(self):
        content = self._write()
        self.assertIn("<FREQ:7>146.580", content)
        self.assertNotIn("146.580MHz", content)

    def test_my_gridsquare_present(self):
        content = self._write(grid="DM04")
        self.assertIn("<MY_GRIDSQUARE:4>DM04", content)

    def test_my_gridsquare_absent_when_no_grid(self):
        content = self._write(grid=None)
        self.assertNotIn("MY_GRIDSQUARE", content)

    def test_comment_written_for_notes(self):
        content = self._write()
        self.assertIn("<COMMENT:4>Rick", content)

    def test_comment_absent_for_empty_notes(self):
        content = self._write()
        # First record has empty notes — no COMMENT field before its EOR
        lines = [l for l in content.splitlines() if "<CALL:5>KE6TH" in l]
        self.assertEqual(len(lines), 1)
        self.assertNotIn("COMMENT", lines[0])

    def test_sota_ref_written(self):
        content = self._write()
        self.assertIn("<SOTA_REF:9>W6/CT-025", content)

    def test_my_call_written(self):
        content = self._write()
        self.assertIn("<MY_CALL:5>W6XYZ", content)


# ---------------------------------------------------------------------------
# Chronological sort
# ---------------------------------------------------------------------------

class TestChronologicalSort(unittest.TestCase):
    """Verify records sort correctly across month and year boundaries."""

    HEADERS = ["Date", "Freq", "Mode", "Time", "Station Worked", "SOTA_REF", "Notes"]
    COL = oc.resolve_columns(HEADERS)

    def _make_record(self, date, time="1200", callsign="KE6TH", sota_ref="W6/CT-025"):
        row = [date, "146.580", "FM", time, callsign, sota_ref, ""]
        return oc.row_to_chaser_v2(row, self.COL, "W6XYZ")

    def test_same_month_ordered(self):
        records = [
            self._make_record("3/15/2026"),
            self._make_record("3/1/2026"),
        ]
        records.sort(key=lambda r: (r[3][6:10] + r[3][3:5] + r[3][0:2], r[4]))
        self.assertEqual(records[0][3], "01/03/2026")
        self.assertEqual(records[1][3], "15/03/2026")

    def test_cross_month_ordered(self):
        # Feb 15 must sort before Mar 1
        records = [
            self._make_record("3/1/2026"),
            self._make_record("2/15/2026"),
        ]
        records.sort(key=lambda r: (r[3][6:10] + r[3][3:5] + r[3][0:2], r[4]))
        self.assertEqual(records[0][3], "15/02/2026")
        self.assertEqual(records[1][3], "01/03/2026")

    def test_cross_year_ordered(self):
        # Dec 31 2025 must sort before Jan 1 2026
        records = [
            self._make_record("1/1/2026"),
            self._make_record("12/31/2025"),
        ]
        records.sort(key=lambda r: (r[3][6:10] + r[3][3:5] + r[3][0:2], r[4]))
        self.assertEqual(records[0][3], "31/12/2025")
        self.assertEqual(records[1][3], "01/01/2026")

    def test_same_date_sorted_by_time(self):
        records = [
            self._make_record("3/1/2026", time="1500"),
            self._make_record("3/1/2026", time="0900"),
        ]
        records.sort(key=lambda r: (r[3][6:10] + r[3][3:5] + r[3][0:2], r[4]))
        self.assertEqual(records[0][4], "0900")
        self.assertEqual(records[1][4], "1500")


# ---------------------------------------------------------------------------
# Output filename
# ---------------------------------------------------------------------------

class TestOutputFilename(unittest.TestCase):
    """Integration-level: verify the auto-generated filename uses the new pattern."""

    def test_csv_filename_pattern(self):
        from datetime import datetime
        today = datetime.today().strftime("%Y%m%d")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write("Callsign: W6XYZ\nGrid: DM04\n\n")
            f.write("| Date | Freq | Mode | Time | Callsign | SOTA_REF |\n")
            f.write("| ---- | ---- | ---- | ---- | -------- | -------- |\n")
            f.write("| 3/1/2026 | 146.580 | FM | 21:48 | KE6TH | W6/CT-025 |\n")
            md_path = f.name

        out_path = Path(f"W6XYZ_ObsidianChaser_{today}.csv")
        try:
            with patch("sys.argv", ["obsidianchaser.py", "--input", md_path]):
                try:
                    oc.main()
                except SystemExit:
                    pass
            self.assertTrue(out_path.exists())
        finally:
            os.unlink(md_path)
            out_path.unlink(missing_ok=True)

    def test_adif_filename_pattern(self):
        from datetime import datetime
        today = datetime.today().strftime("%Y%m%d")
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write("Callsign: W6XYZ\nGrid: DM04\n\n")
            f.write("| Date | Freq | Mode | Time | Callsign | SOTA_REF |\n")
            f.write("| ---- | ---- | ---- | ---- | -------- | -------- |\n")
            f.write("| 3/1/2026 | 146.580 | FM | 21:48 | KE6TH | W6/CT-025 |\n")
            md_path = f.name

        out_path = Path(f"W6XYZ_ObsidianChaser_{today}.adi")
        try:
            with patch("sys.argv", ["obsidianchaser.py", "--input", md_path, "--format", "adif"]):
                try:
                    oc.main()
                except SystemExit:
                    pass
            self.assertTrue(out_path.exists())
        finally:
            os.unlink(md_path)
            out_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# --quiet flag
# ---------------------------------------------------------------------------

class TestQuietFlag(unittest.TestCase):

    MD = """\
Callsign: W6XYZ
Grid: DM04

| Date | Freq | Mode | Time | Callsign | SOTA_REF |
| ---- | ---- | ---- | ---- | -------- | -------- |
| 3/1/2026 | 146.580 | FM | 21:48 | KE6TH | W6/CT-025 |
"""

    def _run(self, extra_args=()):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
            f.write(self.MD)
            md_path = f.name
        out_path = Path(md_path).with_suffix(".csv")
        try:
            captured = io.StringIO()
            with patch("sys.argv", ["obsidianchaser.py", "--input", md_path,
                                    "--output", str(out_path), *extra_args]):
                with patch("sys.stdout", captured):
                    try:
                        oc.main()
                    except SystemExit:
                        pass
            return captured.getvalue()
        finally:
            os.unlink(md_path)
            out_path.unlink(missing_ok=True)

    def test_normal_mode_has_output(self):
        self.assertGreater(len(self._run()), 0)

    def test_quiet_suppresses_stdout(self):
        self.assertEqual(self._run(["--quiet"]), "")

    def test_quiet_short_flag(self):
        self.assertEqual(self._run(["-q"]), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
