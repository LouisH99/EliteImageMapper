#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import queue
import re
import shutil
import sys
import threading
import time
import webbrowser
from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

SUPPORTED_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".webp"}
IMAGE_DIR_CANDIDATES = ["images", "screenshots", "screens", "bilder"]
JOURNAL_DIR_CANDIDATES = ["journals", "journal", "logs", "jurnals", "jurnal", "journale"]
OUTPUT_DIR_NAME = "output"
REPORT_FILE_NAME = "mapping_report.csv"
APP_VERSION = "0.9.2"
GITHUB_REPO_URL = "https://github.com/LouisH99/EliteImageMapper"


def get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

SCREENSHOT_FILENAME_MATCH_MAX_SEC = 15 * 60
SCREENSHOT_TIME_MATCH_MAX_SEC = 2 * 60
NEXT_SCREENSHOT_FALLBACK_MAX_SEC = 30
BODY_STALE_AFTER_SEC = 6 * 60 * 60
SYSTEM_STALE_AFTER_SEC = 36 * 60 * 60
JOURNAL_RANGE_TOLERANCE_SEC = 24 * 60 * 60

try:
    from PIL import Image, ExifTags  # type: ignore
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False
    Image = None
    ExifTags = None

TRANSLATIONS = {
    "de": {
        "app_title": "Elite Image Mapper",
        "about": "Über",
        "about_title": "Über Elite Image Mapper",
        "version": "Version",
        "repository": "Repository",
        "open_repo": "Repository öffnen",
        "copy_link": "Link kopieren",
        "close": "Schließen",
        "github_copied": "GitHub-Link wurde in die Zwischenablage kopiert.",
        "about_text": "Ordnet Elite Dangerous Screenshots Journaldaten zu und benennt sie um. Optional können Bilder auch konvertiert werden.",
        "language": "Sprache",
        "theme": "Design",
        "theme_dark": "Dunkel",
        "theme_light": "Hell",
        "folders": "Ordner",
        "screenshots_1": "Screenshot-Ordner 1",
        "screenshots_2": "Screenshot-Ordner 2 (optional)",
        "screenshots_2_hint": "z. B. Steam-Screenshots",
        "journals": "Journal-Ordner",
        "output_folder": "Ausgabe-Ordner",
        "open_output": "Ausgabeordner öffnen",
        "output_fixed": "Ausgabe-Ordner liegt immer neben dem Skript",
        "browse": "Auswählen...",
        "conversion": "Bildkonvertierung",
        "conversion_disabled": "Konvertierung ist deaktiviert.",
        "enable_conversion": "Bilder konvertieren",
        "target_format": "Zielformat",
        "jpeg_quality": "JPEG-Qualität",
        "jpeg_optimize": "JPEG optimieren",
        "webp_quality": "WEBP-Qualität",
        "webp_lossless": "WEBP lossless",
        "png_compression": "PNG-Kompression",
        "delete_originals": "Originalbilder nach erfolgreicher Verarbeitung löschen",
        "run": "Verarbeitung starten",
        "stop": "Stopp",
        "status": "Status",
        "progress": "Fortschritt",
        "ready": "Bereit.",
        "running": "Verarbeitung läuft...",
        "stopping": "Verarbeitung wird gestoppt...",
        "canceled": "Verarbeitung gestoppt.",
        "done": "Verarbeitung abgeschlossen.",
        "log": "Protokoll",
        "browse_title": "Ordner auswählen",
        "select_image_folder": "Bitte mindestens einen Screenshot-Ordner wählen.",
        "select_journal_folder": "Bitte einen Journal-Ordner wählen.",
        "missing_folder": "Ordner nicht gefunden",
        "missing_pillow": "Für die Bildkonvertierung wird Pillow benötigt. Bitte 'pip install pillow' in der venv ausführen.",
        "confirm_delete_title": "Originale löschen",
        "confirm_delete": "Originalbilder werden nach erfolgreicher Verarbeitung gelöscht.\n\nFortfahren?",
        "processing_started": "Verarbeitung gestartet...",
        "processing_finished": "Verarbeitung abgeschlossen.",
        "processing_failed": "Verarbeitung fehlgeschlagen",
        "images_found": "Bilder gefunden",
        "journal_range": "Zeitraum Journals",
        "output": "Ausgabe",
        "report": "Report",
        "kept_originals": "Originale blieben unverändert erhalten.",
        "deleted_original": "Original gelöscht",
        "delete_warning": "Original konnte nicht gelöscht werden",
        "open_output_failed": "Ausgabeordner konnte nicht geöffnet werden",
        "images_processed": "Bilder verarbeitet",
        "action_copied": "kopiert",
        "action_converted": "konvertiert",
        "yes": "ja",
        "no": "nein",
    },
    "en": {
        "app_title": "Elite Image Mapper",
        "about": "About",
        "about_title": "About Elite Image Mapper",
        "version": "Version",
        "repository": "Repository",
        "open_repo": "Open repository",
        "copy_link": "Copy link",
        "close": "Close",
        "github_copied": "GitHub link copied to clipboard.",
        "about_text": "Maps Elite Dangerous screenshots to journal data and renames them. Images can also be converted optionally.",
        "language": "Language",
        "theme": "Theme",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "folders": "Folders",
        "screenshots_1": "Screenshot folder 1",
        "screenshots_2": "Screenshot folder 2 (optional)",
        "screenshots_2_hint": "e.g. Steam screenshots",
        "journals": "Journal folder",
        "output_folder": "Output folder",
        "open_output": "Open output folder",
        "output_fixed": "The output folder is always stored next to the script",
        "browse": "Browse...",
        "conversion": "Image conversion",
        "conversion_disabled": "Conversion is disabled.",
        "enable_conversion": "Convert images",
        "target_format": "Target format",
        "jpeg_quality": "JPEG quality",
        "jpeg_optimize": "Optimize JPEG",
        "webp_quality": "WEBP quality",
        "webp_lossless": "WEBP lossless",
        "png_compression": "PNG compression",
        "delete_originals": "Delete original images after successful processing",
        "run": "Start processing",
        "stop": "Stop",
        "status": "Status",
        "progress": "Progress",
        "ready": "Ready.",
        "running": "Processing...",
        "stopping": "Stopping...",
        "canceled": "Processing stopped.",
        "done": "Processing completed.",
        "log": "Log",
        "browse_title": "Select folder",
        "select_image_folder": "Please select at least one screenshot folder.",
        "select_journal_folder": "Please select a journal folder.",
        "missing_folder": "Folder not found",
        "missing_pillow": "Pillow is required for image conversion. Please run 'pip install pillow' inside the venv.",
        "confirm_delete_title": "Delete originals",
        "confirm_delete": "Original images will be deleted after successful processing.\n\nContinue?",
        "processing_started": "Processing started...",
        "processing_finished": "Processing completed.",
        "processing_failed": "Processing failed",
        "images_found": "Images found",
        "journal_range": "Journal range",
        "output": "Output",
        "report": "Report",
        "kept_originals": "Originals were kept unchanged.",
        "deleted_original": "Original deleted",
        "delete_warning": "Could not delete original",
        "open_output_failed": "Could not open output folder",
        "images_processed": "images processed",
        "action_copied": "copied",
        "action_converted": "converted",
        "yes": "yes",
        "no": "no",
    },
}


@dataclass(slots=True)
class JournalScreenshotEvent:
    ts_utc: datetime
    filename_key: str
    system: Optional[str]
    body: Optional[str]
    journal_file: str


@dataclass(slots=True)
class StatePoint:
    ts_utc: datetime
    system: Optional[str]
    body: Optional[str]
    source_event: str
    journal_file: str


@dataclass(slots=True)
class ImageTimeCandidate:
    source: str
    local_dt: datetime
    utc_dt: datetime
    precision: str
    base_date_only: Optional[date] = None


@dataclass(slots=True)
class MatchResult:
    image_path: Path
    image_ts_local: datetime
    image_ts_utc: datetime
    chosen_time_source: str
    chosen_time_precision: str
    system: Optional[str]
    body: Optional[str]
    method: str
    confidence: str
    matched_event_ts_utc: Optional[datetime]
    age_seconds: Optional[int]
    score: int = -10**9


@dataclass(slots=True)
class ConversionSettings:
    enabled: bool = False
    target_format: str = "png"
    jpeg_quality: int = 92
    jpeg_optimize: bool = True
    webp_quality: int = 90
    webp_lossless: bool = False
    png_compression: int = 6
    delete_originals: bool = False


def t(lang: str, key: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["de"]).get(key, key)


def parse_journal_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def sanitize_component(text: Optional[str], fallback: str) -> str:
    text = (text or fallback).strip()
    if not text:
        text = fallback
    for ch in '<>:"/\\|?*':
        text = text.replace(ch, "-")
    text = "".join(c for c in text if ord(c) >= 32)
    text = " ".join(text.split()).strip(" .")
    return text or fallback


def normalize_filename_key(value: str) -> str:
    value = value.replace("\\", "/")
    value = value.split("/")[-1]
    return value.strip().lower()


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for i in range(2, 100000):
        candidate = path.with_name(f"{stem}__{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"No free filename for {path}")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def detect_existing_dir(base: Path, candidates: list[str]) -> Optional[Path]:
    for name in candidates:
        p = base / name
        if p.exists() and p.is_dir():
            return p
    return None


def get_default_image_dir(base_dir: Path) -> Path:
    if os.name == "nt":
        pictures = Path.home() / "Pictures" / "Frontier Developments" / "Elite Dangerous"
        if pictures.exists():
            return pictures
    return detect_existing_dir(base_dir, IMAGE_DIR_CANDIDATES) or (base_dir / "images")


def get_default_journal_dir(base_dir: Path) -> Path:
    if os.name == "nt":
        saved_games = Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous"
        if saved_games.exists():
            return saved_games
    return detect_existing_dir(base_dir, JOURNAL_DIR_CANDIDATES) or (base_dir / "journals")


def localize_naive_local_datetime(naive_dt: datetime) -> datetime:
    ts = time.mktime(naive_dt.timetuple()) + (naive_dt.microsecond / 1_000_000)
    return datetime.fromtimestamp(ts).astimezone()


def get_exif_local_datetime(path: Path) -> Optional[datetime]:
    if not PIL_AVAILABLE or path.suffix.lower() not in {".jpg", ".jpeg", ".webp", ".png"}:
        return None
    try:
        assert Image is not None and ExifTags is not None
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None
            tag_map = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif.items()}
            for tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                value = tag_map.get(tag_name)
                if not value:
                    continue
                naive_dt = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                return localize_naive_local_datetime(naive_dt)
    except Exception:
        return None
    return None


def iter_image_files(folders: list[Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for folder in folders:
        if not folder.exists() or not folder.is_dir():
            continue
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    files.append(p)
    return sorted(files, key=lambda p: str(p).lower())


def iter_journal_files(folder: Path) -> list[Path]:
    files = [p for p in folder.rglob("Journal*.log")]
    files += [p for p in folder.rglob("journal*.log") if p not in files]
    return sorted(files, key=lambda p: p.name.lower())


def choose(value1: Optional[str], value2: Optional[str] = None, value3: Optional[str] = None) -> Optional[str]:
    for value in (value1, value2, value3):
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def get_filesystem_time_candidates(path: Path) -> list[ImageTimeCandidate]:
    stat = path.stat()
    candidates: list[tuple[str, float]] = []
    if hasattr(stat, "st_birthtime"):
        candidates.append(("filesystem_birthtime", stat.st_birthtime))
    if os.name == "nt":
        candidates.append(("filesystem_ctime_windows", stat.st_ctime))
    else:
        candidates.append(("filesystem_ctime", stat.st_ctime))
    candidates.append(("filesystem_mtime", stat.st_mtime))

    unique: dict[tuple[str, int], ImageTimeCandidate] = {}
    for source, ts in candidates:
        local_dt = datetime.fromtimestamp(ts).astimezone()
        unique[(source, int(ts))] = ImageTimeCandidate(source, local_dt, local_dt.astimezone(timezone.utc), "full")
    return sorted(unique.values(), key=lambda item: item.utc_dt)


def parse_filename_datetime_candidates(path: Path, reference_time: Optional[dt_time]) -> list[ImageTimeCandidate]:
    stem = path.stem
    candidates: list[ImageTimeCandidate] = []
    seen: set[tuple[str, int]] = set()

    def add_candidate(source: str, naive_dt: datetime, precision: str, base_date_only: Optional[date] = None) -> None:
        try:
            local_dt = localize_naive_local_datetime(naive_dt)
        except Exception:
            return
        key = (source, int(local_dt.timestamp()))
        if key in seen:
            return
        seen.add(key)
        candidates.append(ImageTimeCandidate(source, local_dt, local_dt.astimezone(timezone.utc), precision, base_date_only))

    full_patterns = [
        re.compile(r"(?P<y>20\d{2})[-_ .]?(?P<m>\d{2})[-_ .]?(?P<d>\d{2})[-_ T.]?(?P<h>\d{2})[-_.:]?(?P<mi>\d{2})[-_.:]?(?P<s>\d{2})"),
        re.compile(r"\b0(?P<yy>\d{2})(?P<m>\d{2})(?P<d>\d{2})(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})\b"),
        re.compile(r"\b(?P<yy>\d{2})(?P<m>\d{2})(?P<d>\d{2})(?P<h>\d{2})(?P<mi>\d{2})(?P<s>\d{2})\b"),
    ]
    for pattern in full_patterns:
        for match in pattern.finditer(stem):
            gd = match.groupdict()
            try:
                year = int(gd.get("y") or f"20{gd['yy']}")
                naive_dt = datetime(year, int(gd["m"]), int(gd["d"]), int(gd["h"]), int(gd["mi"]), int(gd["s"]))
            except Exception:
                continue
            add_candidate("filename_datetime", naive_dt, "full")

    date_pattern = re.compile(r"(?P<y>20\d{2})[-_ .]?(?P<m>\d{2})[-_ .]?(?P<d>\d{2})")
    for match in date_pattern.finditer(stem):
        try:
            parsed_date = date(int(match.group("y")), int(match.group("m")), int(match.group("d")))
        except Exception:
            continue
        if reference_time is not None:
            add_candidate("filename_date_plus_filesystem_time", datetime.combine(parsed_date, reference_time), "date_only_derived", parsed_date)
        add_candidate("filename_date_midday", datetime.combine(parsed_date, dt_time(12, 0, 0)), "date_only_derived", parsed_date)

    return sorted(candidates, key=lambda item: item.utc_dt)


def get_time_candidates(path: Path) -> tuple[list[ImageTimeCandidate], Optional[ImageTimeCandidate], Optional[date]]:
    candidates: list[ImageTimeCandidate] = []
    fs_candidates = get_filesystem_time_candidates(path)
    oldest_fs = fs_candidates[0] if fs_candidates else None

    exif_local = get_exif_local_datetime(path)
    if exif_local is not None:
        candidates.append(ImageTimeCandidate("exif", exif_local, exif_local.astimezone(timezone.utc), "full"))
    if oldest_fs is not None:
        candidates.append(oldest_fs)

    ref_time = oldest_fs.local_dt.timetz().replace(tzinfo=None) if oldest_fs is not None else None
    candidates.extend(parse_filename_datetime_candidates(path, ref_time))

    dedup: dict[tuple[str, int], ImageTimeCandidate] = {}
    for cand in candidates:
        dedup[(cand.source, int(cand.utc_dt.timestamp()))] = cand
    all_candidates = sorted(dedup.values(), key=lambda item: item.utc_dt)
    filename_date_only = next((c.base_date_only for c in all_candidates if c.base_date_only is not None), None)
    return all_candidates, oldest_fs, filename_date_only


def build_journal_indexes(journal_dir: Path) -> tuple[dict[str, list[JournalScreenshotEvent]], list[JournalScreenshotEvent], list[StatePoint], datetime, datetime]:
    screenshot_by_filename: dict[str, list[JournalScreenshotEvent]] = defaultdict(list)
    screenshot_events: list[JournalScreenshotEvent] = []
    timeline: list[StatePoint] = []
    records: list[tuple[datetime, dict, str]] = []

    journal_files = iter_journal_files(journal_dir)
    if not journal_files:
        raise FileNotFoundError(f"No journal files found in '{journal_dir}'.")

    for journal_file in journal_files:
        with journal_file.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                ts = record.get("timestamp")
                ev = record.get("event")
                if not ts or not ev:
                    continue
                try:
                    ts_utc = parse_journal_timestamp(str(ts))
                except Exception:
                    continue
                records.append((ts_utc, record, journal_file.name))

    if not records:
        raise RuntimeError("No readable entries found in the journal files.")

    records.sort(key=lambda item: item[0])
    current_system: Optional[str] = None
    current_body: Optional[str] = None
    state_events = {"Location", "FSDJump", "CarrierJump", "ApproachBody", "SupercruiseEntry", "SupercruiseExit", "Touchdown", "Liftoff", "LeaveBody", "Screenshot", "Docked", "Undocked", "StartJump"}

    for ts_utc, record, journal_name in records:
        event_name = str(record.get("event"))
        star_system = choose(record.get("StarSystem"), record.get("Starsystem"), record.get("System"))
        body = choose(record.get("Body"), record.get("BodyName"))

        if event_name == "Screenshot":
            filename_key = normalize_filename_key(str(record.get("Filename", "")))
            ss = JournalScreenshotEvent(
                ts_utc=ts_utc,
                filename_key=filename_key,
                system=choose(record.get("System"), record.get("StarSystem"), current_system),
                body=choose(record.get("Body"), current_body),
                journal_file=journal_name,
            )
            screenshot_events.append(ss)
            if filename_key:
                screenshot_by_filename[filename_key].append(ss)

        if event_name in state_events or star_system or body:
            if star_system:
                current_system = star_system
            if body:
                current_body = body
            elif event_name in {"FSDJump", "CarrierJump", "StartJump", "SupercruiseEntry", "Undocked", "LeaveBody"}:
                current_body = None
            timeline.append(StatePoint(ts_utc, current_system, current_body, event_name, journal_name))

    for values in screenshot_by_filename.values():
        values.sort(key=lambda x: x.ts_utc)
    screenshot_events.sort(key=lambda x: x.ts_utc)
    timeline.sort(key=lambda x: x.ts_utc)
    return screenshot_by_filename, screenshot_events, timeline, records[0][0], records[-1][0]


def method_rank(method: str) -> int:
    if method == "journal_screenshot_dateiname":
        return 4
    if method == "journal_screenshot_zeit":
        return 3
    if method == "journal_screenshot_zeit_vorlauf":
        return 2
    if method.startswith("timeline_"):
        return 1
    return 0


def confidence_rank(confidence: str) -> int:
    return {"hoch": 3, "mittel": 2, "niedrig": 1, "keine": 0}.get(confidence, 0)


def source_bonus(source: str) -> int:
    return {
        "exif": 80,
        "filesystem_birthtime": 30,
        "filesystem_ctime_windows": 25,
        "filesystem_ctime": 10,
        "filesystem_mtime": 15,
        "filename_datetime": 40,
        "filename_date_plus_filesystem_time": 25,
        "filename_date_midday": 15,
    }.get(source, 0)


def in_journal_range(image_ts_utc: datetime, journal_min_utc: datetime, journal_max_utc: datetime) -> bool:
    return journal_min_utc - timedelta(seconds=JOURNAL_RANGE_TOLERANCE_SEC) <= image_ts_utc <= journal_max_utc + timedelta(seconds=JOURNAL_RANGE_TOLERANCE_SEC)


def score_match(method: str, confidence: str, age_seconds: Optional[int], source: str, is_in_range: bool) -> int:
    score = method_rank(method) * 10_000 + confidence_rank(confidence) * 1_000 + source_bonus(source)
    if age_seconds is not None:
        score -= min(age_seconds, 9_999)
    if not is_in_range:
        score -= 2_500
    return score


def build_empty_match(path: Path, cand: ImageTimeCandidate) -> MatchResult:
    return MatchResult(path, cand.local_dt, cand.utc_dt, cand.source, cand.precision, None, None, "keine_zuordnung", "keine", None, None)


def find_best_by_filename(path: Path, image_ts_utc: datetime, screenshot_by_filename: dict[str, list[JournalScreenshotEvent]], cand: ImageTimeCandidate, journal_min_utc: datetime, journal_max_utc: datetime) -> Optional[MatchResult]:
    key = normalize_filename_key(path.name)
    candidates = screenshot_by_filename.get(key, [])
    if not candidates:
        return None
    best = min(candidates, key=lambda item: abs((item.ts_utc - image_ts_utc).total_seconds()))
    delta = abs(int((best.ts_utc - image_ts_utc).total_seconds()))
    if len(candidates) > 1 and delta > SCREENSHOT_FILENAME_MATCH_MAX_SEC:
        return None
    confidence = "hoch" if delta <= 120 else ("mittel" if delta <= SCREENSHOT_FILENAME_MATCH_MAX_SEC or len(candidates) == 1 else "niedrig")
    result = MatchResult(path, cand.local_dt, image_ts_utc, cand.source, cand.precision, best.system, best.body, "journal_screenshot_dateiname", confidence, best.ts_utc, delta)
    result.score = score_match(result.method, result.confidence, result.age_seconds, cand.source, in_journal_range(image_ts_utc, journal_min_utc, journal_max_utc))
    return result


def find_best_by_screenshot_time(path: Path, image_ts_utc: datetime, screenshot_events: list[JournalScreenshotEvent], screenshot_timestamps: list[datetime], cand: ImageTimeCandidate, journal_min_utc: datetime, journal_max_utc: datetime) -> Optional[MatchResult]:
    if not screenshot_events:
        return None
    pos = bisect_left(screenshot_timestamps, image_ts_utc)
    candidates: list[JournalScreenshotEvent] = []
    if pos < len(screenshot_events):
        candidates.append(screenshot_events[pos])
    if pos > 0:
        candidates.append(screenshot_events[pos - 1])
    if not candidates:
        return None
    best = min(candidates, key=lambda item: abs((item.ts_utc - image_ts_utc).total_seconds()))
    delta = int((best.ts_utc - image_ts_utc).total_seconds())
    abs_delta = abs(delta)
    if abs_delta <= SCREENSHOT_TIME_MATCH_MAX_SEC:
        confidence = "hoch" if abs_delta <= 15 else "mittel"
        result = MatchResult(path, cand.local_dt, image_ts_utc, cand.source, cand.precision, best.system, best.body, "journal_screenshot_zeit", confidence, best.ts_utc, abs_delta)
        result.score = score_match(result.method, result.confidence, result.age_seconds, cand.source, in_journal_range(image_ts_utc, journal_min_utc, journal_max_utc))
        return result
    if 0 < delta <= NEXT_SCREENSHOT_FALLBACK_MAX_SEC:
        result = MatchResult(path, cand.local_dt, image_ts_utc, cand.source, cand.precision, best.system, best.body, "journal_screenshot_zeit_vorlauf", "mittel", best.ts_utc, abs_delta)
        result.score = score_match(result.method, result.confidence, result.age_seconds, cand.source, in_journal_range(image_ts_utc, journal_min_utc, journal_max_utc))
        return result
    return None


def find_best_by_timeline(path: Path, image_ts_utc: datetime, timeline: list[StatePoint], timeline_timestamps: list[datetime], cand: ImageTimeCandidate, journal_min_utc: datetime, journal_max_utc: datetime) -> Optional[MatchResult]:
    if not timeline:
        return None
    pos = bisect_right(timeline_timestamps, image_ts_utc) - 1
    if pos < 0:
        next_state = timeline[0]
        age = int((next_state.ts_utc - image_ts_utc).total_seconds())
        if age < 0 or age > 15 * 60:
            return None
        result = MatchResult(path, cand.local_dt, image_ts_utc, cand.source, cand.precision, next_state.system, None, f"timeline_naechster_zustand:{next_state.source_event}", "niedrig", next_state.ts_utc, age)
        result.score = score_match(result.method, result.confidence, result.age_seconds, cand.source, in_journal_range(image_ts_utc, journal_min_utc, journal_max_utc))
        return result
    state = timeline[pos]
    age = int((image_ts_utc - state.ts_utc).total_seconds())
    if age < 0:
        return None
    system = state.system if age <= SYSTEM_STALE_AFTER_SEC else None
    body = state.body if age <= BODY_STALE_AFTER_SEC else None
    if not system and not body:
        return None
    confidence = "mittel" if age <= 10 * 60 else "niedrig"
    result = MatchResult(path, cand.local_dt, image_ts_utc, cand.source, cand.precision, system, body, f"timeline_letzter_zustand:{state.source_event}", confidence, state.ts_utc, age)
    result.score = score_match(result.method, result.confidence, result.age_seconds, cand.source, in_journal_range(image_ts_utc, journal_min_utc, journal_max_utc))
    return result


def evaluate_candidate(path: Path, cand: ImageTimeCandidate, screenshot_by_filename: dict[str, list[JournalScreenshotEvent]], screenshot_events: list[JournalScreenshotEvent], screenshot_timestamps: list[datetime], timeline: list[StatePoint], timeline_timestamps: list[datetime], journal_min_utc: datetime, journal_max_utc: datetime) -> MatchResult:
    best = build_empty_match(path, cand)
    for result in (
        find_best_by_filename(path, cand.utc_dt, screenshot_by_filename, cand, journal_min_utc, journal_max_utc),
        find_best_by_screenshot_time(path, cand.utc_dt, screenshot_events, screenshot_timestamps, cand, journal_min_utc, journal_max_utc),
        find_best_by_timeline(path, cand.utc_dt, timeline, timeline_timestamps, cand, journal_min_utc, journal_max_utc),
    ):
        if result is not None and result.score > best.score:
            best = result
    if best.method == "keine_zuordnung":
        best.score = score_match(best.method, best.confidence, best.age_seconds, cand.source, in_journal_range(cand.utc_dt, journal_min_utc, journal_max_utc))
    return best


def pick_best_match(path: Path, candidates: list[ImageTimeCandidate], oldest_fs: Optional[ImageTimeCandidate], screenshot_by_filename: dict[str, list[JournalScreenshotEvent]], screenshot_events: list[JournalScreenshotEvent], screenshot_timestamps: list[datetime], timeline: list[StatePoint], timeline_timestamps: list[datetime], journal_min_utc: datetime, journal_max_utc: datetime) -> MatchResult:
    if not candidates:
        now_local = datetime.now().astimezone()
        return MatchResult(path, now_local, now_local.astimezone(timezone.utc), "none", "none", None, None, "keine_zuordnung", "keine", None, None)
    results = [evaluate_candidate(path, cand, screenshot_by_filename, screenshot_events, screenshot_timestamps, timeline, timeline_timestamps, journal_min_utc, journal_max_utc) for cand in candidates]
    best = max(results, key=lambda r: r.score)
    fs_results = [r for r in results if r.chosen_time_source.startswith("filesystem") or r.chosen_time_source == "exif"]
    name_results = [r for r in results if r.chosen_time_source.startswith("filename")]
    best_fs = max(fs_results, key=lambda r: r.score) if fs_results else None
    best_name = max(name_results, key=lambda r: r.score) if name_results else None
    if best_fs is not None and best_name is not None:
        date_diff_days = abs((best_fs.image_ts_local.date() - best_name.image_ts_local.date()).days)
        if date_diff_days > 30 and best_fs.method.startswith("timeline_") and best_name.method != "keine_zuordnung":
            best = best_name
        elif date_diff_days > 2:
            fs_strength = (method_rank(best_fs.method), confidence_rank(best_fs.confidence), -(best_fs.age_seconds or 10**9))
            name_strength = (method_rank(best_name.method), confidence_rank(best_name.confidence), -(best_name.age_seconds or 10**9))
            if name_strength >= fs_strength:
                best = best_name
    if best.matched_event_ts_utc is not None and best.method in {"journal_screenshot_dateiname", "journal_screenshot_zeit", "journal_screenshot_zeit_vorlauf"}:
        best.image_ts_utc = best.matched_event_ts_utc
        best.image_ts_local = best.matched_event_ts_utc.astimezone()
    return best


def has_highres_marker(path: Path) -> bool:
    return "highresscreenshot" in path.stem.lower()


def strip_duplicate_system_from_body(system: Optional[str], body: Optional[str]) -> Optional[str]:
    if not body:
        return body
    if not system:
        return body
    norm_system = " ".join(system.split()).strip()
    norm_body = " ".join(body.split()).strip()
    if not norm_system or not norm_body:
        return body
    if norm_body.casefold() == norm_system.casefold():
        return None
    prefix = norm_system + " "
    if norm_body.casefold().startswith(prefix.casefold()):
        trimmed = norm_body[len(norm_system):].strip()
        return trimmed or None
    return body


def build_new_filename(result: MatchResult, original_suffix: str, is_highres: bool) -> str:
    date_part = result.image_ts_local.strftime("%Y-%m-%d")
    time_part = result.image_ts_local.strftime("%H-%M-%S")
    parts = [date_part, time_part, sanitize_component(result.system, "UNKNOWN_SYSTEM")]
    body = strip_duplicate_system_from_body(result.system, result.body)
    if body:
        parts.append(sanitize_component(body, ""))
    if is_highres:
        parts.append("HR")
    return "__".join(parts) + original_suffix.lower()


def get_conversion_suffix(settings: ConversionSettings, source_path: Path) -> str:
    if not settings.enabled:
        return source_path.suffix.lower()
    mapping = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}
    return mapping.get(settings.target_format.lower(), source_path.suffix.lower())


def save_converted_image(source_path: Path, destination: Path, settings: ConversionSettings) -> None:
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for image conversion.")
    assert Image is not None
    with Image.open(source_path) as img:
        fmt = settings.target_format.lower()
        save_kwargs: dict = {}
        image_to_save = img

        if fmt == "jpeg":
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (0, 0, 0))
                alpha = img.convert("RGBA")
                background.paste(alpha, mask=alpha.getchannel("A"))
                image_to_save = background
            elif img.mode != "RGB":
                image_to_save = img.convert("RGB")
            save_kwargs.update({"format": "JPEG", "quality": clamp_int(settings.jpeg_quality, 1, 100), "optimize": bool(settings.jpeg_optimize)})
        elif fmt == "png":
            if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                image_to_save = img.convert("RGBA")
            save_kwargs.update({"format": "PNG", "compress_level": clamp_int(settings.png_compression, 0, 9)})
        elif fmt == "webp":
            save_kwargs.update({"format": "WEBP", "quality": clamp_int(settings.webp_quality, 1, 100), "lossless": bool(settings.webp_lossless)})
        else:
            raise RuntimeError(f"Unsupported target format: {settings.target_format}")

        image_to_save.save(destination, **save_kwargs)


def process_image_dirs(
    image_dirs: list[Path],
    journal_dir: Path,
    output_dir: Path,
    report_path: Path,
    conversion_settings: Optional[ConversionSettings] = None,
    logger: Optional[Callable[[str], None]] = None,
    lang: str = "de",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    stop_event: Optional[threading.Event] = None,
) -> bool:
    settings = conversion_settings or ConversionSettings()
    ensure_dir(output_dir)

    def emit(message: str) -> None:
        if logger:
            logger(message)
        else:
            print(message)

    def update_progress(done: int, total: int) -> None:
        if progress_callback:
            progress_callback(done, total)

    images = iter_image_files(image_dirs)
    if not images:
        raise FileNotFoundError("No supported image files found.")

    screenshot_by_filename, screenshot_events, timeline, journal_min_utc, journal_max_utc = build_journal_indexes(journal_dir)
    screenshot_timestamps = [item.ts_utc for item in screenshot_events]
    timeline_timestamps = [item.ts_utc for item in timeline]

    preprocessed: list[tuple[datetime, Path, list[ImageTimeCandidate], Optional[ImageTimeCandidate], Optional[date]]] = []
    for image_path in images:
        candidates, oldest_fs, filename_date_only = get_time_candidates(image_path)
        sort_key = candidates[0].utc_dt if candidates else datetime.now(timezone.utc)
        preprocessed.append((sort_key, image_path, candidates, oldest_fs, filename_date_only))
    preprocessed.sort(key=lambda item: item[0])

    rows: list[dict[str, str]] = []
    total = len(preprocessed)
    update_progress(0, total)
    emit(f"{t(lang, 'images_found')}: {total}")
    emit(f"{t(lang, 'journal_range')}: {journal_min_utc.isoformat()} -> {journal_max_utc.isoformat()}")
    emit(f"{t(lang, 'output')}: {output_dir}")

    completed = True

    for idx, (_, image_path, candidates, oldest_fs, filename_date_only) in enumerate(preprocessed, 1):
        if stop_event and stop_event.is_set():
            completed = False
            emit(t(lang, 'canceled'))
            break

        match = pick_best_match(image_path, candidates, oldest_fs, screenshot_by_filename, screenshot_events, screenshot_timestamps, timeline, timeline_timestamps, journal_min_utc, journal_max_utc)
        is_highres = has_highres_marker(image_path)
        new_suffix = get_conversion_suffix(settings, image_path)
        new_name = build_new_filename(match, new_suffix, is_highres)
        destination = unique_destination(output_dir / new_name)

        if settings.enabled:
            save_converted_image(image_path, destination, settings)
            action = t(lang, "action_converted")
        else:
            shutil.copy2(image_path, destination)
            action = t(lang, "action_copied")

        original_deleted = False
        if settings.delete_originals:
            try:
                image_path.unlink()
                original_deleted = True
                emit(f"{t(lang, 'deleted_original')}: {image_path}")
            except Exception as exc:
                emit(f"{t(lang, 'delete_warning')}: {image_path} ({exc})")

        candidate_summary = " | ".join(f"{cand.source}:{cand.local_dt.strftime('%Y-%m-%d %H:%M:%S')}" for cand in candidates)
        rows.append({
            "original_file": image_path.name,
            "source_folder": str(image_path.parent),
            "new_filename": destination.name,
            "action": action,
            "original_deleted": t(lang, "yes") if original_deleted else t(lang, "no"),
            "target_format": destination.suffix.lower().lstrip("."),
            "image_time_local": match.image_ts_local.isoformat(),
            "image_time_utc": match.image_ts_utc.isoformat(),
            "time_source": match.chosen_time_source,
            "time_precision": match.chosen_time_precision,
            "filename_date": filename_date_only.isoformat() if filename_date_only else "",
            "highres": t(lang, "yes") if is_highres else t(lang, "no"),
            "system": match.system or "",
            "body": strip_duplicate_system_from_body(match.system, match.body) or "",
            "method": match.method,
            "confidence": match.confidence,
            "journal_time_utc": match.matched_event_ts_utc.isoformat() if match.matched_event_ts_utc else "",
            "delta_seconds": str(match.age_seconds) if match.age_seconds is not None else "",
            "score": str(match.score),
            "checked_time_candidates": candidate_summary,
        })

        emit(f"[{idx:>4}/{total}] {image_path.name} -> {destination.name} ({match.chosen_time_source}, {match.method}, {match.confidence}, {action})")
        update_progress(idx, total)

    with report_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "original_file", "source_folder", "new_filename", "action", "original_deleted", "target_format",
                "image_time_local", "image_time_utc", "time_source", "time_precision", "filename_date", "highres",
                "system", "body", "method", "confidence", "journal_time_utc", "delta_seconds", "score",
                "checked_time_candidates",
            ],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerows(rows)

    emit("")
    emit(f"{len(rows)} {t(lang, 'images_processed')}")
    emit(f"{t(lang, 'report')}: {report_path}")
    if completed:
        emit(t(lang, 'kept_originals') if not settings.delete_originals else t(lang, 'done'))
    return completed

def process_images(base_dir: Optional[Path] = None) -> None:
    base_dir = base_dir or get_app_base_dir()
    image_dir = get_default_image_dir(base_dir)
    journal_dir = get_default_journal_dir(base_dir)
    output_dir = base_dir / OUTPUT_DIR_NAME
    report_path = output_dir / REPORT_FILE_NAME

    ensure_dir(output_dir)
    process_image_dirs([image_dir], journal_dir, output_dir, report_path, ConversionSettings(), lang="en")


def launch_gui() -> int:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:
        print("Error: tkinter is not available in this Python installation.", file=sys.stderr)
        print(f"Details: {exc}", file=sys.stderr)
        return 1

    script_dir = get_app_base_dir()
    default_output_dir = script_dir / OUTPUT_DIR_NAME
    ensure_dir(default_output_dir)

    root = tk.Tk()
    root.title("Elite Image Mapper")
    root.geometry("1040x820")
    root.minsize(940, 720)

    var_lang = tk.StringVar(value="de")
    var_dark = tk.BooleanVar(value=True)
    var_img1 = tk.StringVar(value=str(get_default_image_dir(script_dir)))
    var_img2 = tk.StringVar(value="")
    var_journals = tk.StringVar(value=str(get_default_journal_dir(script_dir)))
    var_output = tk.StringVar(value=str(default_output_dir))

    var_convert = tk.BooleanVar(value=False)
    var_format = tk.StringVar(value="png")
    var_jpeg_quality = tk.IntVar(value=92)
    var_jpeg_optimize = tk.BooleanVar(value=True)
    var_webp_quality = tk.IntVar(value=90)
    var_webp_lossless = tk.BooleanVar(value=False)
    var_png_compression = tk.IntVar(value=6)
    var_delete_originals = tk.BooleanVar(value=False)

    status_var = tk.StringVar(value=t(var_lang.get(), "ready"))
    progress_text_var = tk.StringVar(value="0 / 0")
    progress_value = tk.DoubleVar(value=0.0)
    queue_log: queue.Queue[str] = queue.Queue()
    is_running = {"value": False}
    stop_event = threading.Event()

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    DARK = {
        "bg": "#1f1f1f",
        "field": "#2f2f2f",
        "field_disabled": "#2a2a2a",
        "text": "#f0f0f0",
        "muted": "#9c9c9c",
        "border": "#4a4a4a",
        "button": "#3a3a3a",
        "button_active": "#4b4b4b",
        "accent": "#6d8fb3",
        "accent_2": "#557799",
    }
    LIGHT = {
        "bg": "#f3f3f3",
        "field": "#ffffff",
        "field_disabled": "#ececec",
        "text": "#1e1e1e",
        "muted": "#666666",
        "border": "#bdbdbd",
        "button": "#e7e7e7",
        "button_active": "#d9e9ff",
        "accent": "#3d72b4",
        "accent_2": "#335f96",
    }

    text_keys: dict[str, object] = {}

    def colors() -> dict[str, str]:
        return DARK if var_dark.get() else LIGHT

    def apply_theme() -> None:
        c = colors()
        root.configure(bg=c["bg"])
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["text"])
        style.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"])
        style.configure("Status.TLabel", background=c["bg"], foreground=c["muted"])
        style.configure("TLabelframe", background=c["bg"], foreground=c["text"], bordercolor=c["border"], borderwidth=1, relief="solid")
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["text"])
        style.configure("Muted.TLabelframe", background=c["bg"], foreground=c["muted"], bordercolor=c["border"], borderwidth=1, relief="solid")
        style.configure("Muted.TLabelframe.Label", background=c["bg"], foreground=c["muted"])
        style.configure("TCheckbutton", background=c["bg"], foreground=c["text"])
        style.map("TCheckbutton", background=[("active", c["bg"]), ("disabled", c["bg"])], foreground=[("disabled", c["muted"])])
        style.configure("TRadiobutton", background=c["bg"], foreground=c["text"])
        style.map("TRadiobutton", background=[("active", c["bg"]), ("disabled", c["bg"])], foreground=[("disabled", c["muted"])])
        style.configure("TEntry", fieldbackground=c["field"], foreground=c["text"], bordercolor=c["border"], insertcolor=c["text"])
        style.map("TEntry", fieldbackground=[("readonly", c["field"]), ("disabled", c["field_disabled"])], foreground=[("disabled", c["muted"])])
        style.configure("TCombobox", fieldbackground=c["field"], foreground=c["text"], background=c["field"], bordercolor=c["border"], arrowsize=16, arrowcolor=c["text"])
        style.map("TCombobox", fieldbackground=[("readonly", c["field"]), ("disabled", c["field_disabled"])], foreground=[("disabled", c["muted"]), ("readonly", c["text"])], background=[("disabled", c["field_disabled"]), ("active", c["field"])], selectbackground=[("readonly", c["accent"])])
        style.configure("TSpinbox", fieldbackground=c["field"], foreground=c["text"], bordercolor=c["border"], arrowsize=14)
        style.map("TSpinbox", fieldbackground=[("disabled", c["field_disabled"])], foreground=[("disabled", c["muted"])])
        style.configure("TButton", background=c["button"], foreground=c["text"], bordercolor=c["border"], focusthickness=0, padding=(10, 8))
        style.map("TButton", background=[("active", c["button_active"]), ("disabled", c["button"])], foreground=[("disabled", c["muted"])])
        style.configure("Accent.TButton", background=c["accent"], foreground="#ffffff", bordercolor=c["accent"], padding=(10, 10))
        style.map("Accent.TButton", background=[("active", c["accent_2"]), ("disabled", c["accent"])])
        style.configure("Danger.TButton", background="#884444" if var_dark.get() else "#d97c7c", foreground="#ffffff", bordercolor="#884444" if var_dark.get() else "#d97c7c", padding=(10, 10))
        style.map("Danger.TButton", background=[("active", "#a55555" if var_dark.get() else "#c76464"), ("disabled", "#6e4a4a" if var_dark.get() else "#d0a0a0")])
        style.configure("TProgressbar", troughcolor=c["field_disabled"], background=c["accent"], bordercolor=c["border"], lightcolor=c["accent"], darkcolor=c["accent"])
        log_text.configure(bg=c["field"], fg=c["text"], insertbackground=c["text"], selectbackground=c["accent"], highlightbackground=c["border"], highlightcolor=c["accent"], relief="flat")
        set_conversion_note()

    def browse_dir(target_var: 'tk.StringVar') -> None:
        initial = target_var.get().strip() or str(script_dir)
        chosen = filedialog.askdirectory(title=t(var_lang.get(), "browse_title"), initialdir=initial)
        if chosen:
            target_var.set(chosen)


    def show_about() -> None:
        lang = var_lang.get()
        win = tk.Toplevel(root)
        win.title(t(lang, "about_title"))
        win.transient(root)
        win.resizable(False, False)
        win.configure(bg=colors()["bg"])

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text=t(lang, "app_title"), font=("TkDefaultFont", 12, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=f"{t(lang, 'version')}: {APP_VERSION}", style="Status.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(frame, text=t(lang, "about_text"), wraplength=440, justify="left").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Label(frame, text=f"{t(lang, 'repository')}:\n{GITHUB_REPO_URL}", wraplength=440, justify="left", style="Status.TLabel").grid(row=3, column=0, sticky="w", pady=(12, 0))

        button_row = ttk.Frame(frame)
        button_row.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        button_row.columnconfigure(0, weight=1)
        button_row.columnconfigure(1, weight=1)
        button_row.columnconfigure(2, weight=1)

        def open_repo() -> None:
            webbrowser.open(GITHUB_REPO_URL)

        def copy_link() -> None:
            root.clipboard_clear()
            root.clipboard_append(GITHUB_REPO_URL)
            root.update_idletasks()
            messagebox.showinfo(t(lang, "app_title"), t(lang, "github_copied"), parent=win)

        ttk.Button(button_row, text=t(lang, "open_repo"), command=open_repo).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(button_row, text=t(lang, "copy_link"), command=copy_link).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(button_row, text=t(lang, "close"), command=win.destroy).grid(row=0, column=2, sticky="ew", padx=(6, 0))

    def add_log(message: str) -> None:
        queue_log.put(message)

    def flush_logs() -> None:
        try:
            while True:
                msg = queue_log.get_nowait()
                log_text.configure(state="normal")
                log_text.insert("end", msg + "\n")
                log_text.see("end")
                log_text.configure(state="disabled")
        except queue.Empty:
            pass
        root.after(100, flush_logs)

    def update_progress(done: int, total: int) -> None:
        def _apply() -> None:
            total_safe = max(total, 1)
            progress_value.set((done / total_safe) * 100.0)
            progress_text_var.set(f"{done} / {total}")
        root.after(0, _apply)

    def open_output_folder() -> None:
        lang = var_lang.get()
        try:
            target = Path(var_output.get()).expanduser()
            ensure_dir(target)
            if os.name == "nt":
                os.startfile(str(target))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", str(target)])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", str(target)])
        except Exception as exc:
            messagebox.showerror(t(lang, "app_title"), f"{t(lang, 'open_output_failed')}: {exc}")

    def set_conversion_note() -> None:
        muted = not var_convert.get()
        conversion_note.configure(text=t(var_lang.get(), "conversion_disabled") if muted else "", style="Muted.TLabel")
        frame_style = "Muted.TLabelframe" if muted else "TLabelframe"
        label_style = "Muted.TLabel" if muted else "TLabel"
        try:
            conversion_frame.configure(style=frame_style)
        except Exception:
            pass
        for label in conversion_labels:
            label.configure(style=label_style)

    def set_running(running: bool) -> None:
        is_running["value"] = running
        state = "disabled" if running else "normal"
        for widget in editable_widgets:
            try:
                widget.configure(state=state)
            except Exception:
                pass
        stop_button.configure(state=("normal" if running else "disabled"))
        open_output_button.configure(state=("normal" if not running else "disabled"))
        update_conversion_controls()
        if running:
            status_var.set(t(var_lang.get(), "running"))

    def update_conversion_controls(*_args) -> None:
        enabled = bool(var_convert.get()) and not is_running["value"]
        if not PIL_AVAILABLE:
            enabled = False
            convert_check.configure(state="disabled")
        else:
            convert_check.configure(state=("normal" if not is_running["value"] else "disabled"))
        target_combo.configure(state=("readonly" if enabled else "disabled"))
        delete_check.configure(state=("normal" if not is_running["value"] else "disabled"))

        fmt = var_format.get().lower()
        for widget in (jpeg_spin, jpeg_opt_check):
            widget.configure(state=("normal" if enabled and fmt == "jpeg" else "disabled"))
        for widget in (webp_spin, webp_lossless_check):
            widget.configure(state=("normal" if enabled and fmt == "webp" else "disabled"))
        png_spin.configure(state=("normal" if enabled and fmt == "png" else "disabled"))
        set_conversion_note()

    def refresh_texts(*_args) -> None:
        lang = var_lang.get()
        root.title(t(lang, "app_title"))
        for key, widget in text_keys.items():
            widget.configure(text=t(lang, key))
        if is_running["value"] and stop_event.is_set():
            status_var.set(t(lang, "stopping"))
        elif is_running["value"]:
            status_var.set(t(lang, "running"))
        elif stop_event.is_set():
            status_var.set(t(lang, "canceled"))
        else:
            status_var.set(t(lang, "ready"))
        set_conversion_note()

    def worker(image_dirs: list[Path], journal_dir: Path, output_dir: Path, settings: ConversionSettings, lang: str) -> None:
        try:
            completed = process_image_dirs(
                image_dirs=image_dirs,
                journal_dir=journal_dir,
                output_dir=output_dir,
                report_path=output_dir / REPORT_FILE_NAME,
                conversion_settings=settings,
                logger=add_log,
                lang=lang,
                progress_callback=update_progress,
                stop_event=stop_event,
            )
            if completed:
                root.after(0, lambda: status_var.set(t(lang, "done")))
                root.after(0, lambda: messagebox.showinfo(t(lang, "app_title"), t(lang, "processing_finished")))
            else:
                root.after(0, lambda: status_var.set(t(lang, "canceled")))
        except Exception as exc:
            add_log(f"{t(lang, 'processing_failed')}: {exc}")
            root.after(0, lambda: status_var.set(f"{t(lang, 'processing_failed')}: {exc}"))
            root.after(0, lambda: messagebox.showerror(t(lang, "app_title"), str(exc)))
        finally:
            root.after(0, lambda: set_running(False))

    def stop_processing() -> None:
        if not is_running["value"]:
            return
        stop_event.set()
        status_var.set(t(var_lang.get(), "stopping"))
        stop_button.configure(state="disabled")
        add_log(t(var_lang.get(), "stopping"))

    def start_processing() -> None:
        if is_running["value"]:
            return
        lang = var_lang.get()
        image_dirs: list[Path] = []
        if var_img1.get().strip():
            image_dirs.append(Path(var_img1.get()).expanduser())
        if var_img2.get().strip():
            image_dirs.append(Path(var_img2.get()).expanduser())
        if not image_dirs:
            messagebox.showerror(t(lang, "app_title"), t(lang, "select_image_folder"))
            return
        journal_dir = Path(var_journals.get()).expanduser()
        if not journal_dir.exists() or not journal_dir.is_dir():
            messagebox.showerror(t(lang, "app_title"), t(lang, "select_journal_folder"))
            return
        output_dir = Path(var_output.get()).expanduser()
        for folder in image_dirs:
            if not folder.exists() or not folder.is_dir():
                messagebox.showerror(t(lang, "missing_folder"), str(folder))
                return
        if var_convert.get() and not PIL_AVAILABLE:
            messagebox.showerror(t(lang, "app_title"), t(lang, "missing_pillow"))
            return
        if var_delete_originals.get():
            if not messagebox.askyesno(t(lang, "confirm_delete_title"), t(lang, "confirm_delete"), icon="warning"):
                return

        ensure_dir(output_dir)
        stop_event.clear()
        update_progress(0, 0)
        settings = ConversionSettings(
            enabled=bool(var_convert.get()),
            target_format=var_format.get().lower(),
            jpeg_quality=clamp_int(var_jpeg_quality.get(), 1, 100),
            jpeg_optimize=bool(var_jpeg_optimize.get()),
            webp_quality=clamp_int(var_webp_quality.get(), 1, 100),
            webp_lossless=bool(var_webp_lossless.get()),
            png_compression=clamp_int(var_png_compression.get(), 0, 9),
            delete_originals=bool(var_delete_originals.get()),
        )
        log_text.configure(state="normal")
        log_text.delete("1.0", "end")
        log_text.configure(state="disabled")
        add_log(t(lang, "processing_started"))
        set_running(True)
        threading.Thread(target=worker, args=(image_dirs, journal_dir, output_dir, settings, lang), daemon=True).start()

    main = ttk.Frame(root, padding=14)
    main.pack(fill="both", expand=True)
    main.columnconfigure(0, weight=1)
    main.rowconfigure(6, weight=1)

    top_bar = ttk.Frame(main)
    top_bar.grid(row=0, column=0, sticky="ew")
    top_bar.columnconfigure(5, weight=1)

    lang_label = ttk.Label(top_bar)
    lang_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
    lang_combo = ttk.Combobox(top_bar, textvariable=var_lang, values=["de", "en"], width=8, state="readonly")
    lang_combo.grid(row=0, column=1, sticky="w", padx=(0, 18))

    theme_label = ttk.Label(top_bar)
    theme_label.grid(row=0, column=2, sticky="w", padx=(0, 8))
    dark_radio = ttk.Radiobutton(top_bar, variable=var_dark, value=True, command=apply_theme)
    dark_radio.grid(row=0, column=3, sticky="w")
    light_radio = ttk.Radiobutton(top_bar, variable=var_dark, value=False, command=apply_theme)
    light_radio.grid(row=0, column=4, sticky="w", padx=(8, 0))

    about_button = ttk.Button(top_bar, command=show_about)
    about_button.grid(row=0, column=6, sticky="e")

    folders_frame = ttk.LabelFrame(main, padding=12)
    folders_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
    folders_frame.columnconfigure(1, weight=1)

    def add_path_row(parent, row: int, label_key: str, variable: 'tk.StringVar', note_key: Optional[str] = None):
        label = ttk.Label(parent)
        label.grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=5)
        button = ttk.Button(parent, command=lambda: browse_dir(variable))
        button.grid(row=row, column=2, sticky="ew", padx=(10, 0), pady=5)
        text_keys[label_key] = label
        text_keys[f"{label_key}_browse"] = button
        note = None
        if note_key:
            note = ttk.Label(parent, style="Muted.TLabel")
            note.grid(row=row + 1, column=1, sticky="w", pady=(0, 4))
            text_keys[note_key] = note
        return entry, button, note

    img1_entry, img1_button, _ = add_path_row(folders_frame, 0, "screenshots_1", var_img1)
    img2_entry, img2_button, _ = add_path_row(folders_frame, 2, "screenshots_2", var_img2, "screenshots_2_hint")
    journals_entry, journals_button, _ = add_path_row(folders_frame, 4, "journals", var_journals)
    output_entry, output_button, _ = add_path_row(folders_frame, 6, "output_folder", var_output)

    conversion_frame = ttk.LabelFrame(main, padding=12)
    conversion_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
    for col in range(4):
        conversion_frame.columnconfigure(col, weight=1 if col in (1, 3) else 0)

    convert_check = ttk.Checkbutton(conversion_frame, variable=var_convert, command=update_conversion_controls)
    convert_check.grid(row=0, column=0, sticky="w", pady=(0, 8))
    text_keys["enable_conversion"] = convert_check

    delete_check = ttk.Checkbutton(conversion_frame, variable=var_delete_originals)
    delete_check.grid(row=0, column=2, columnspan=2, sticky="w", pady=(0, 8), padx=(12, 0))
    text_keys["delete_originals"] = delete_check

    target_label = ttk.Label(conversion_frame)
    target_label.grid(row=1, column=0, sticky="w", pady=4)
    text_keys["target_format"] = target_label
    target_combo = ttk.Combobox(conversion_frame, textvariable=var_format, values=["png", "jpeg", "webp"], state="readonly", width=12)
    target_combo.grid(row=1, column=1, sticky="w", pady=4)

    jpeg_label = ttk.Label(conversion_frame)
    jpeg_label.grid(row=2, column=0, sticky="w", pady=4)
    text_keys["jpeg_quality"] = jpeg_label
    jpeg_spin = ttk.Spinbox(conversion_frame, from_=1, to=100, textvariable=var_jpeg_quality, width=8)
    jpeg_spin.grid(row=2, column=1, sticky="w", pady=4)
    jpeg_opt_check = ttk.Checkbutton(conversion_frame, variable=var_jpeg_optimize)
    jpeg_opt_check.grid(row=2, column=2, sticky="w", pady=4, padx=(12, 0))
    text_keys["jpeg_optimize"] = jpeg_opt_check

    webp_label = ttk.Label(conversion_frame)
    webp_label.grid(row=3, column=0, sticky="w", pady=4)
    text_keys["webp_quality"] = webp_label
    webp_spin = ttk.Spinbox(conversion_frame, from_=1, to=100, textvariable=var_webp_quality, width=8)
    webp_spin.grid(row=3, column=1, sticky="w", pady=4)
    webp_lossless_check = ttk.Checkbutton(conversion_frame, variable=var_webp_lossless)
    webp_lossless_check.grid(row=3, column=2, sticky="w", pady=4, padx=(12, 0))
    text_keys["webp_lossless"] = webp_lossless_check

    png_label = ttk.Label(conversion_frame)
    png_label.grid(row=4, column=0, sticky="w", pady=4)
    text_keys["png_compression"] = png_label
    png_spin = ttk.Spinbox(conversion_frame, from_=0, to=9, textvariable=var_png_compression, width=8)
    png_spin.grid(row=4, column=1, sticky="w", pady=4)

    conversion_note = ttk.Label(conversion_frame, style="Muted.TLabel")
    conversion_note.grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 0))

    progress_frame = ttk.LabelFrame(main, padding=12)
    progress_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
    progress_frame.columnconfigure(0, weight=1)
    text_keys["progress"] = progress_frame

    progress_bar = ttk.Progressbar(progress_frame, variable=progress_value, maximum=100, mode="determinate")
    progress_bar.grid(row=0, column=0, sticky="ew")
    progress_count = ttk.Label(progress_frame, textvariable=progress_text_var, style="Status.TLabel")
    progress_count.grid(row=0, column=1, sticky="e", padx=(10, 0))

    button_row = ttk.Frame(main)
    button_row.grid(row=4, column=0, sticky="ew", pady=(12, 0))
    button_row.columnconfigure(0, weight=2)
    button_row.columnconfigure(1, weight=1)
    button_row.columnconfigure(2, weight=1)

    start_button = ttk.Button(button_row, command=start_processing, style="Accent.TButton")
    start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
    text_keys["run"] = start_button

    stop_button = ttk.Button(button_row, command=stop_processing, style="Danger.TButton")
    stop_button.grid(row=0, column=1, sticky="ew", padx=4)
    text_keys["stop"] = stop_button

    open_output_button = ttk.Button(button_row, command=open_output_folder)
    open_output_button.grid(row=0, column=2, sticky="ew", padx=(8, 0))
    text_keys["open_output"] = open_output_button

    status_bar = ttk.Frame(main)
    status_bar.grid(row=5, column=0, sticky="ew", pady=(8, 0))
    status_bar.columnconfigure(1, weight=1)
    status_label = ttk.Label(status_bar)
    status_label.grid(row=0, column=0, sticky="w")
    text_keys["status"] = status_label
    status_value = ttk.Label(status_bar, textvariable=status_var, style="Status.TLabel")
    status_value.grid(row=0, column=1, sticky="e")

    log_frame = ttk.LabelFrame(main, padding=10)
    log_frame.grid(row=6, column=0, sticky="nsew", pady=(12, 0))
    log_frame.columnconfigure(0, weight=1)
    log_frame.rowconfigure(0, weight=1)
    text_keys["log"] = log_frame

    log_text = tk.Text(log_frame, wrap="word", height=16, state="disabled", bd=0, padx=10, pady=10)
    log_text.grid(row=0, column=0, sticky="nsew")
    log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
    log_scroll.grid(row=0, column=1, sticky="ns")
    log_text.configure(yscrollcommand=log_scroll.set)

    conversion_labels = [target_label, jpeg_label, webp_label, png_label]
    editable_widgets = [
        img1_entry, img2_entry, journals_entry, output_entry, img1_button, img2_button, journals_button, output_button,
        lang_combo, dark_radio, light_radio, start_button, convert_check, target_combo, jpeg_spin, jpeg_opt_check,
        webp_spin, webp_lossless_check, png_spin, delete_check,
    ]

    text_keys["language"] = lang_label
    text_keys["theme"] = theme_label
    text_keys["theme_dark"] = dark_radio
    text_keys["theme_light"] = light_radio
    text_keys["folders"] = folders_frame
    text_keys["conversion"] = conversion_frame
    text_keys["about"] = about_button

    def apply_button_translations() -> None:
        lang = var_lang.get()
        for btn in (img1_button, img2_button, journals_button, output_button):
            btn.configure(text=t(lang, "browse"))

    def on_language_change(*_args) -> None:
        refresh_texts()
        apply_button_translations()

    var_lang.trace_add("write", on_language_change)
    var_format.trace_add("write", update_conversion_controls)
    var_convert.trace_add("write", update_conversion_controls)

    refresh_texts()
    apply_button_translations()
    apply_theme()
    update_conversion_controls()
    stop_button.configure(state="disabled")
    flush_logs()

    root.mainloop()
    return 0

def main() -> int:
    try:
        if "--gui" in sys.argv:
            return launch_gui()
        process_images(get_app_base_dir())
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
