# Burger Wars — McDonald's vs Burger King Data Art

Three print-ready compositions visualizing the global territory war between
McDonald's and Burger King, rendered from 51,216 real store locations.

**Output:** 6000×4000 px PNG — print-ready at A2 and larger

![Territory Light Map](output/lightmap_preview.png)

---

## Compositions

### Territory Light Map (`output/lightmap.png`) — *featured*

No borders. No outlines. The world drawn entirely by where people go to eat.

Each of the 51,216 stores is rendered as an additive light source — a Gaussian
glow that accumulates with every neighbor. Dense urban clusters burn white-hot.
Sparse suburban rings fade to dim ember. The Atlantic is darkness. Europe is a
contested blue-orange aurora.

- **McDonald's** — red-orange glow (`#FF4400`)
- **Burger King** — electric blue (`#0077FF`)
- **Overlap zones** — white/yellow where both chains cluster (US Northeast, Western Europe)
- **Black void** — ocean, wilderness, markets neither chain has entered

The US dominates in mass and intensity. Europe is the true battleground —
blue pushes hard across Germany, Turkey, and the UK. Japan appears as a warm
pinpoint east of the continent cluster. Australia glows softly at the bottom right.

Technical: NumPy float32 additive accumulation → two-pass Gaussian bloom
(σ=18px + σ=60px) → ACES filmic tone mapping → gamma correction.

---

### Tectonic Plates (`output/tectonic.png`)

51,216 micro-tiles fill a flat plane — each tile is one store. Country clusters
form tectonic landmasses separated by fault-line gaps. McD-dominant territories
rise higher; BK-dominant territories push back. A geological survey of fast food
power rendered in 3D with shadow mapping.

### Siege Wall (`output/siege.png`)

McDonald's 36,009 blocks advance from the left. Burger King's 15,207 from the
right. The 2:1 mass asymmetry is immediate. Country battalions cluster by size —
the US megaforce at the front. Rendered with rim lighting through the central void.

---

## Data Sources

- **OpenStreetMap** (Overpass API, brand:wikidata) — 51,216 individual store locations globally
- **Wikipedia / Corporate IR** — country-level store count validation, 100 countries, 2023–2024
- **Coverage:** McDonald's 36,009 stores / Burger King 15,207 stores across 100 countries

## Pipeline

```bash
# 1. Fetch store data from OSM (~5 min, cached after first run)
python3 data/fetch_osm.py

# 2a. Territory Light Map (recommended — ~2 min)
python3 generate_lightmap.py
python3 postprocess_lightmap.py

# 2b. 3D compositions
python3 generate_tectonic.py && python3 render_tectonic_mgl.py
python3 generate_siege.py    && python3 render_siege_mgl.py
python3 postprocess.py

```

## Stack

| Layer | Tools |
|-------|-------|
| Data | Python 3.8, requests (Overpass API) |
| Light Map | NumPy, SciPy (Gaussian bloom), Pillow |
| 3D Render | moderngl 5.12 / OpenGL 4.1 (no Blender required) |
| Post-process | Pillow (vignette, sharpen, labels) |

## Part of the Data Art Series

- **Breathing Planet** — NASA temperature anomaly data (1880–2025)
- **Neural Surge** — Tesla stock price (2010–2025)
- **Tokyo Pulse** — 23-ward population data (2015–2024)
- **Burger Wars** — Global fast food territory (2024)
