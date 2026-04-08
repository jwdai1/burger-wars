# Burger Wars — McDonald's vs Burger King Data Art

Two print-ready 3D compositions visualizing the global territory war between
McDonald's and Burger King, rendered from 51,000+ real store locations.

**Output:** 6000×4000 px PNG, moderngl (OpenGL 4.1) render

## Compositions

### B: Tectonic Plates (`output/tectonic.png`)
51,188 micro-tiles fill a plane — each tile is one store. Country clusters form
tectonic landmasses. Fault lines run along dominance boundaries. McD-dominant
territories rise higher; BK-dominant territories push back. A geological survey
of fast food power.

### C: Siege Wall (`output/siege.png`)
McDonald's 36,009 blocks advance from the left. Burger King's 15,207 from the
right. A central void separates the forces. The 2:1 mass asymmetry is immediate.
Country battalions cluster by size — the US megaforce charges at the front.

## Data Sources
- OpenStreetMap (Overpass API) — 51,216 individual store locations globally
- Wikipedia / Corporate IR — country-level store count validation (100 countries)

## Color Palette
| Chain | Primary | Secondary |
|-------|---------|-----------|
| McDonald's | Deep Crimson `#8B1A1A` | Burnt Gold `#B8860B` |
| Burger King | Midnight Blue `#1B2A4A` | Bronze Orange `#CD7F32` |
| Contested | Muted grey-brown | |

Dominant markets: vivid. Contested markets: desaturated.

## Stack
- Python 3.8.2 (data + geometry)
- moderngl 5.12.0 / OpenGL 4.1 (3D rendering — no Blender required)
- Pillow (post-processing + labels)

## Pipeline

```bash
# 1. Fetch data (~5 min, cached after first run)
/usr/local/bin/python3 data/fetch_osm.py

# 2. Generate geometry
/usr/local/bin/python3 generate_tectonic.py
/usr/local/bin/python3 generate_siege.py

# 3. Render (6000x4000, ~10s each)
/usr/local/bin/python3 render_tectonic_mgl.py
/usr/local/bin/python3 render_siege_mgl.py

# 4. Post-process + labels
/usr/local/bin/python3 postprocess.py
```

## Part of the Data Art Series
- **Breathing Planet** — NASA temperature anomaly data (1880–2025)
- **Neural Surge** — Tesla stock price (2010–2025)
- **Tokyo Pulse** — 23-ward population data (2015–2024)
- **Burger Wars** — Global fast food territory (2024)
