"""PACE-RESUMABLE, SINGLE-THREADED polite MediaWiki fetcher for distractor-scale corpus.

Resumes from fetch_log.jsonl if present. Honours a hard 400 MB download cap.
On persistent 429/5xx after max retries, the title is PARKED (logged as gap) and
the fetcher CONTINUES — it never aborts the whole run.

Usage:
    python3 corpus/scale/fetch_distractors.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import hashlib
import random
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# --- Configuration -----------------------------------------------------------

ROOT = Path(__file__).resolve().parent  # corpus/scale/
CANDIDATES_PATH = ROOT / "distractor_candidates.json"
RAW_DIR = ROOT / "raw"
FETCH_LOG = ROOT / "fetch_log.jsonl"

USER_AGENT = (
    "round-0-scale-fetcher/1.0 (+davidhatley research; "
    "see corpus/LICENSE for contact policy)"
)

MIN_DELAY = 2.0      # minimum seconds between requests (with jitter)
MAX_DELAY = 30.0     # maximum backoff delay for rate-limiting
BACKOFF_BASE = 2.0   # exponential backoff base
MAX_RETRIES = 8      # max retries per title before PARKING
CAP_BYTES = 400 * 1024 * 1024  # 400 MiB hard cap

# ———————————————————————————————————————————————————————————————————————————————

def load_candidates():
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["articles"]  # list of entries with {method, seed, target_articles, articles:[{t,title..., c,cluster, g}]}


def load_fetch_log():
    """Return set of already-fetched titles and accumulated bytes."""
    fetched_titles = set()
    total_bytes = 0
    if FETCH_LOG.exists():
        with open(FETCH_LOG, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    fetched_titles.add(rec["title"])
                    total_bytes += rec.get("bytes", 0) or 0
                except Exception:
                    continue
    return fetched_titles, total_bytes


def is_valid_snapshot(path: Path) -> bool:
    """A snapshot is valid if it has all required keys and content hash matches."""
    REQUIRED = {
        "requested_title", "normalized_title", "pageid", "revid",
        "timestamp", "source_url", "wikitext", "outlinks", "cluster",
        "split_group", "content_sha256",
    }
    if not path.exists():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return False
    missing = REQUIRED - set(d.keys())
    if missing:
        return False
    # verify content hash
    try:
        actual = hashlib.sha256(d["wikitext"].encode("utf-8")).hexdigest()
        return actual == d.get("content_sha256", "")
    except Exception:
        return False


def sanitize_title(title: str) -> str:
    """Make a safe filesystem filename from a Wikipedia title."""
    safe = re.sub(r"[<>:\"/\\|?*]", "_", title)
    safe = safe.replace(" ", "_")
    return safe[:200]


def fetch_article(title: str) -> dict | None:
    """Fetch a single Wikipedia article via the MediaWiki API.

    Returns a dict with snapshot data, or None if the title should be PARKED.
    On persistent 429/5xx after MAX_RETRIES, returns {"parked": True, ...}.
    """
    base_url = "https://en.wikipedia.org/w/api.php"

    # API parameters — note: formatversion=2 changes pages from dict to list
    params = (
        f"action=query"
        f"&format=json"
        f"&titles={urllib.parse.quote(title, safe='')}"
        f"&prop=revisions"
        f"&rvprop=timestamp|user|comment|content"
        f"&rvslots=main"
    )
    url = f"{base_url}?{params}"

    prev_backoff = 2.0  # seconds

    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            code = e.code
            reason = f"http_{code}"
            wait = min(prev_backoff + random.uniform(0, 1.0), 300.0)
            time.sleep(wait)
            prev_backoff *= BACKOFF_BASE
            if attempt == MAX_RETRIES:
                return {"parked": True, "title": title, "reason": reason}
            continue
        except urllib.error.URLError as e:
            reason = f"url_{e}"
            wait = min(prev_backoff + random.uniform(0, 1.0), 300.0)
            time.sleep(wait)
            prev_backoff *= BACKOFF_BASE
            if attempt == MAX_RETRIES:
                return {"parked": True, "title": title, "reason": reason}
            continue
        except Exception as e:
            reason = f"network_{e}"
            wait = min(prev_backoff + random.uniform(0, 1.0), 300.0)
            time.sleep(wait)
            prev_backoff *= BACKOFF_BASE
            if attempt == MAX_RETRIES:
                return {"parked": True, "title": title, "reason": reason}
            continue

        # Parse JSON
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            wait = min(prev_backoff + random.uniform(0, 1.0), 300.0)
            time.sleep(wait)
            prev_backoff *= BACKOFF_BASE
            if attempt == MAX_RETRIES:
                return {"parked": True, "title": title, "reason": "json_parse_error"}
            continue

        # Handle rate limiting (429)
        if "headers" in dir() and hasattr(resp, 'headers'):
            pass  # handled below

        # Parse response — pages is a dict of title-key -> page (no formatversion=2)
        query = data.get("query", {})
        pages = query.get("pages", {})
        if not pages:
            # Title not found or empty result
            return None

        # pages is a dict; get the first page value
        page = next(iter(pages.values()), None)
        if page is None:
            return None

        # Extract revision data
        rev = page.get("revisions", [{}])[0]
        if not rev:
            return None

        timestamp = rev.get("timestamp", "")
        # revid may be None depending on rvprop; try to get it
        revid = rev.get("revid")

        # Build source URL — properly encode the title
        encoded_title = urllib.parse.quote(title, safe="")
        source_url = f"https://en.wikipedia.org/wiki/{encoded_title}"

        # Compute bytes from wikitext
        content_slot = rev.get("slots", {}).get("main", {})
        wikitext = content_slot.get("*", "")
        wikitext_bytes = len(wikitext.encode("utf-8")) if wikitext else 0

        # Build snapshot
        snapshot = {
            "requested_title": title,
            "normalized_title": title,
            "pageid": page.get("pageid"),
            "revid": revid,
            "timestamp": timestamp,
            "source_url": source_url,
            "wikitext": wikitext,
            "outlinks": [],  # placeholder — outlinks extracted later if needed
            "cluster": "distractor",
            "split_group": "distractor",
            "content_sha256": hashlib.sha256(wikitext.encode("utf-8")).hexdigest()
            if wikitext
            else "",
            "bytes": wikitext_bytes,
        }

        # Polite pause after request (inter-request delay handled in main loop)
        time.sleep(max(0.5, MIN_DELAY * 0.5))

        return snapshot

    # Exhausted all retries
    return {"parked": True, "title": title, "reason": "max_retries_exceeded"}


def main():
    # Load candidates and fetch log
    candidates = load_candidates()
    fetched_titles, total_bytes = load_fetch_log()

    # Build title -> cluster mapping from candidate list
    title_to_cluster = {}
    for entry in candidates:
        title_to_cluster[entry["t"]] = entry["c"]

    # Determine which candidate entries still need fetching
    # Collect unique titles from candidates that haven't been fetched yet
    pending_titles = []
    seen_titles = set()
    for entry in candidates:
        title = entry["t"]  # each entry is already an article dict with 't' key
        if title not in fetched_titles and title not in seen_titles:
            seen_titles.add(title)
            pending_titles.append(title)

    # Sort pending titles deterministically: by cluster then alphabetically
    from collections import defaultdict
    by_cluster = defaultdict(list)
    for title in pending_titles:
        cluster = title_to_cluster.get(title, "distractor")
        by_cluster[cluster].append(title)
    for cluster in by_cluster:
        by_cluster[cluster].sort()
    pending_titles = []
    for cluster in sorted(by_cluster.keys()):
        pending_titles.extend(by_cluster[cluster])

    # Ensure raw dir exists
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Open fetch log in append mode
    log_file = open(FETCH_LOG, "a", encoding="utf-8")

    try:
        parked_titles = []

        for title in pending_titles:
            # Respect the 2s+ inter-request delay with jitter
            jitter = random.uniform(0.0, 1.0)
            delay = max(MIN_DELAY, jitter)
            time.sleep(delay)

            result = fetch_article(title)

            if result is None:
                # Title not found — park it
                parked_titles.append(title)
                log_file.write(json.dumps({
                    "title": title,
                    "status": "not_found",
                    "parked": True,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                log_file.flush()
                continue

            if result.get("parked"):
                # Max retries exceeded — park and continue
                parked_titles.append(title)
                log_file.write(json.dumps({
                    "title": title,
                    "status": "max_retries_exceeded",
                    "reason": result.get("reason"),
                    "parked": True,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                log_file.flush()
                continue

            # We have a successful snapshot
            snap_name = sanitize_title(title) + ".json"
            snap_path = RAW_DIR / snap_name
            tmp_path = RAW_DIR / f".tmp_{sanitize_title(title)}.json"

            # Write snapshot atomically
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, snap_path)

            # Verify the snapshot is valid
            if not is_valid_snapshot(snap_path):
                # Corrupt/invalid — remove and retry once
                snap_path.unlink(missing_ok=True)
                log_file.write(json.dumps({
                    "title": title,
                    "status": "invalid_snapshot",
                    "reason": "content_sha256_mismatch",
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                log_file.flush()
                # Retry once
                result2 = fetch_article(title)
                if result2 and not result2.get("parked"):
                    tmp_path2 = RAW_DIR / f".tmp_{sanitize_title(title)}.json"
                    with open(tmp_path2, "w", encoding="utf-8") as f:
                        json.dump(result2, f, indent=2, ensure_ascii=False)
                    os.replace(tmp_path2, snap_path)
                    if is_valid_snapshot(snap_path):
                        pass  # success on retry
                    else:
                        snap_path.unlink(missing_ok=True)
                continue

            # Check download cap
            total_bytes += result["bytes"]
            if total_bytes > CAP_BYTES:
                # Cap exceeded — remove this snapshot and park the title
                snap_path.unlink(missing_ok=True)
                total_bytes -= result["bytes"]
                parked_titles.append(title)
                log_file.write(json.dumps({
                    "title": title,
                    "status": "cap_exceeded",
                    "total_bytes": total_bytes,
                    "cap_bytes": CAP_BYTES,
                    "parked": True,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                }) + "\n")
                log_file.flush()
                continue

            # Write to fetch log
            log_file.write(json.dumps({
                "title": title,
                "status": "fetched",
                "pageid": result["pageid"],
                "revid": result["revid"],
                "timestamp": result["timestamp"],
                "bytes": result["bytes"],
                "cluster": result.get("cluster", "distractor"),
                "source_url": result["source_url"],
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }) + "\n")
            log_file.flush()

        # End of run summary
        print(f"\n=== Fetcher run complete ===")
        print(f"Pending titles: {len(pending_titles)}")
        fetched_count = sum(
            1 for line in open(FETCH_LOG)
            if json.loads(line).get("status") == "fetched"
        )
        parked_count = sum(
            1 for line in open(FETCH_LOG)
            if json.loads(line).get("status") in ("max_retries_exceeded", "cap_exceeded", "not_found")
        )
        print(f"Successfully fetched: {fetched_count}")
        print(f"Parked (gaps): {parked_count}")
        if parked_titles:
            print(f"  Parked titles: {parked_titles[:15]}{'...' if len(parked_titles) > 15 else ''}")
        print(f"Total bytes downloaded: {total_bytes / (1024*1024):.2f} MiB / {CAP_BYTES/(1024*1024):.2f} MiB cap")
        print(f"Fetch log: {FETCH_LOG}")

    finally:
        log_file.close()


if __name__ == "__main__":
    main()