#!/usr/bin/env python3
"""
fetch_osm.py — Fetch McDonald's and BK store locations from OpenStreetMap.

Uses Overpass API. Queries by brand:wikidata to avoid name-variant issues.
McDonald's Wikidata: Q38076
Burger King Wikidata: Q177054

Enriches with country code and merges reference counts for validation.
Output: data/stores.json
"""
import json
import os
import sys
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.reference_counts import REFERENCE_COUNTS
from common import classify_dominance

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
CACHE_FILE = os.path.join(os.path.dirname(__file__), "osm_raw_cache.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "stores.json")

CHAINS = {
    "mcd": {"wikidata": "Q38076",  "name": "McDonald's"},
    "bk":  {"wikidata": "Q177054", "name": "Burger King"},
}


def fetch_chain_osm(chain_id: str) -> list:
    """Fetch all locations for a chain from Overpass API."""
    wikidata = CHAINS[chain_id]["wikidata"]
    query = f"""
[out:json][timeout:300];
(
  node["brand:wikidata"="{wikidata}"];
  way["brand:wikidata"="{wikidata}"];
  relation["brand:wikidata"="{wikidata}"];
);
out center;
"""
    print(f"  Fetching {CHAINS[chain_id]['name']} from Overpass...", flush=True)
    r = requests.post(OVERPASS_URL, data={"data": query}, timeout=320)
    r.raise_for_status()
    elements = r.json().get("elements", [])

    stores = []
    for el in elements:
        lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
        lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
        if lat is None or lon is None:
            continue
        country = el.get("tags", {}).get("addr:country", "")
        stores.append({
            "chain": chain_id,
            "lat": round(float(lat), 5),
            "lon": round(float(lon), 5),
            "country": country,
        })

    print(f"  -> {len(stores)} {CHAINS[chain_id]['name']} locations found")
    return stores


def load_or_fetch_raw() -> dict:
    """Load from cache if available, otherwise fetch from Overpass."""
    if os.path.exists(CACHE_FILE):
        print("Using cached OSM data (delete osm_raw_cache.json to refresh)")
        with open(CACHE_FILE) as f:
            return json.load(f)

    print("Fetching from Overpass API (this may take 2-5 minutes)...")
    raw = {}
    for chain_id in CHAINS:
        raw[chain_id] = fetch_chain_osm(chain_id)
        time.sleep(5)  # Be polite to Overpass

    with open(CACHE_FILE, "w") as f:
        json.dump(raw, f)
    print(f"Raw data cached to {CACHE_FILE}")
    return raw


def enrich_with_country(stores: list) -> list:
    """
    Fill missing country codes using a simple lat/lon bounding box lookup.
    For stores with addr:country already set, use that.
    """
    COUNTRY_BOXES = {
        # (lat_min, lat_max, lon_min, lon_max): ISO code
        (24.5, 49.5, -125.0, -66.0): "US",
        (18.0, 52.0, -118.0, -86.0): "MX",
        (49.0, 60.0, -141.0, -52.0): "CA",
        (51.0, 71.5, -10.5, 28.0):   "GB",
        (42.0, 51.5, -5.5,  8.3):    "FR",
        (47.0, 55.5,  5.9,  15.1):   "DE",
        (17.0, 55.0,  68.0, 97.0):   "IN",
        (18.0, 53.5,  73.5, 135.5):  "CN",
        (30.0, 46.5, 128.5, 146.0):  "JP",
        (-33.8, -5.0, -73.0, -35.0): "BR",
        (-44.0, -10.0, -75.0, -53.0): "AR",
        (-44.0, -10.5, -53.2, -28.8): "CL",
        (-35.0, -10.0, 113.0, 154.0): "AU",
    }

    def guess_country(lat, lon):
        for (la_min, la_max, lo_min, lo_max), code in COUNTRY_BOXES.items():
            if la_min <= lat <= la_max and lo_min <= lon <= lo_max:
                return code
        return "OTHER"

    enriched = []
    for s in stores:
        country = s.get("country", "").strip().upper()
        if not country or len(country) != 2:
            country = guess_country(s["lat"], s["lon"])
        s["country"] = country
        enriched.append(s)
    return enriched


def build_country_stats(stores: list) -> dict:
    """Aggregate per-country stats and merge with reference counts."""
    from collections import defaultdict
    osm_counts = defaultdict(lambda: {"mcd": 0, "bk": 0})
    for s in stores:
        osm_counts[s["country"]][s["chain"]] += 1

    countries = {}
    for code, ref in REFERENCE_COUNTS.items():
        mcd = ref["mcd"]
        bk = ref["bk"]
        total = mcd + bk
        if total == 0:
            continue
        mcd_ratio = mcd / total
        bk_ratio = bk / total
        countries[code] = {
            "code": code,
            "name": ref["name"],
            "mcd_count": mcd,
            "bk_count": bk,
            "total": total,
            "mcd_ratio": round(mcd_ratio, 4),
            "bk_ratio": round(bk_ratio, 4),
            "dominance": classify_dominance(mcd_ratio, bk_ratio),
        }

    for code, counts in osm_counts.items():
        if code not in countries and code != "OTHER":
            mcd = counts["mcd"]
            bk = counts["bk"]
            total = mcd + bk
            if total == 0:
                continue
            mcd_ratio = mcd / total
            bk_ratio = bk / total
            countries[code] = {
                "code": code,
                "name": code,
                "mcd_count": mcd,
                "bk_count": bk,
                "total": total,
                "mcd_ratio": round(mcd_ratio, 4),
                "bk_ratio": round(bk_ratio, 4),
                "dominance": classify_dominance(mcd_ratio, bk_ratio),
            }

    return countries


def assign_country_to_unmatched(stores, countries):
    """For stores with no country or 'OTHER', fall back to US."""
    result = []
    for s in stores:
        if s["country"] not in countries:
            s["country"] = "US"
        result.append(s)
    return result


def main():
    print("=== Burger Wars -- Data Fetcher ===")
    raw = load_or_fetch_raw()

    all_stores = []
    for chain_id, stores in raw.items():
        enriched = enrich_with_country(stores)
        all_stores.extend(enriched)

    countries = build_country_stats(all_stores)
    all_stores = assign_country_to_unmatched(all_stores, countries)

    for s in all_stores:
        country = countries.get(s["country"], {})
        s["dominance"] = country.get("dominance", "contested")
        s["country_name"] = country.get("name", s["country"])

    output = {
        "stores": all_stores,
        "countries": countries,
        "summary": {
            "total_stores": len(all_stores),
            "mcd_count": sum(1 for s in all_stores if s["chain"] == "mcd"),
            "bk_count": sum(1 for s in all_stores if s["chain"] == "bk"),
            "country_count": len(countries),
        }
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n=== Done ===")
    print(f"Total stores: {output['summary']['total_stores']:,}")
    print(f"McDonald's:   {output['summary']['mcd_count']:,}")
    print(f"Burger King:  {output['summary']['bk_count']:,}")
    print(f"Countries:    {output['summary']['country_count']}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
