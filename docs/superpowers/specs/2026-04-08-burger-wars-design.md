# Burger Wars — McDonald's vs Burger King Data Art

## Overview

58,000+ store locations worldwide rendered as 3D geometric structures in Blender. Two compositions explore the global territory war between McDonald's (~40,000 stores) and Burger King (~18,000 stores) through structural, non-circular geometry with physical mass and depth.

**Output**: 2 static PNGs, 6000x4000 px, print-ready  
**Stack**: Python (data) + Blender/Cycles (rendering) + Pillow (post-process)  
**Visual language**: Geometric, structural, 3D — completely distinct from existing Pillow/NumPy particle-based pipeline

---

## Data

### Source
- **Primary**: OpenStreetMap via Overpass API — all McDonald's and Burger King locations globally (lat/lon per store)
- **Supplementary**: Wikipedia country-level store counts + corporate IR reports for validation and gap-filling

### Schema
```json
{
  "stores": [
    {
      "chain": "mcd" | "bk",
      "lat": 35.6812,
      "lon": 139.7671,
      "country": "JP",
      "country_name": "Japan"
    }
  ],
  "countries": [
    {
      "code": "JP",
      "name": "Japan",
      "mcd_count": 2975,
      "bk_count": 173,
      "total": 3148,
      "mcd_ratio": 0.945,
      "dominance": "mcd_dominant"
    }
  ]
}
```

### Dominance Classification
| Category | Ratio | Label |
|----------|-------|-------|
| McD dominant | >70% McD | `mcd_dominant` |
| McD advantage | 55-70% McD | `mcd_advantage` |
| Contested | 45-55% | `contested` |
| BK advantage | 55-70% BK | `bk_advantage` |
| BK dominant | >70% BK | `bk_dominant` |

---

## Composition B: Tectonic Plates

### Concept
Earth's tectonic plates as metaphor. ~58,000 stores become micro-tiles filling a flat plane. Two competing forces push against each other, with fault lines running along dominance boundaries.

### Spatial Rules
- Each tile = 1 store
- Tile area: uniform (1 store = 1 tile, fair representation)
- Tile height = dominance strength of that store's country. Stores in countries where their chain dominates rise higher
- Layout: Squarified Treemap algorithm groups stores by country, then edges are randomly displaced to create organic polygonal shapes
- Fault lines: where McD-dominant and BK-dominant country clusters border each other, a gap (void) with deep shadows creates visible fractures
- Country clusters maintain cohesion — stores from the same country stay together as recognizable landmasses

### Camera
- Oblique overhead, 30-40 degrees
- Geological survey / terrain model viewing angle
- Framing shows the entire "continent" with fault lines clearly visible

### Labeling
- Top 10 countries by total stores: embossed text on tile surface (country name + store count)
- Sans-serif, subtle, not competing with geometry

---

## Composition C: Siege Wall

### Concept
Central vertical boundary. McDonald's 40,000 blocks advance from the left, Burger King's 18,000 from the right. The 2:1 mass asymmetry is immediately visible.

### Spatial Rules
- Each block = 1 store, uniform base size
- Block height = dominance strength of that store's country in its chain's favor
- Density gradient: blocks pack tighter near the central wall, sparse at edges — "frontline pressure"
- Country clustering: stores from the same country form visible battalions (US mega-cluster, Japan cluster, Brazil cluster, etc.)
- Central wall = thin void (not a physical wall), the "no man's land" where both forces nearly touch
- Country clusters ordered by total store count: largest nations closest to the wall (they lead the charge)

### Camera
- Slightly elevated frontal view, 15-20 degrees
- Panoramic perspective emphasizing left-right asymmetry
- The viewer looks at it like a mural or relief sculpture

### Labeling
- Major country clusters: floating labels
- Title at top center: "McDonald's 40,000 vs Burger King 18,000"

---

## Color Palette

Brand colors recognizable but shifted toward matte, architectural tones.

### McDonald's Side
| Role | Hex | Description |
|------|-----|-------------|
| Primary | `#8B1A1A` | Deep crimson (from McD red) |
| Secondary | `#B8860B` | Burnt gold (from McD yellow) |
| Highlight | `#CD3333` | Brighter crimson for dominant peaks |
| Shadow | `#4A0E0E` | Dark maroon for recesses |

### Burger King Side
| Role | Hex | Description |
|------|-----|-------------|
| Primary | `#1B2A4A` | Midnight blue (from BK blue) |
| Secondary | `#CD7F32` | Bronze orange (from BK orange) |
| Highlight | `#2E4A7A` | Brighter blue for dominant peaks |
| Shadow | `#0D1520` | Deep navy for recesses |

### Contested
- Muted grey-brown blend of both palettes, desaturated

### Mapping
- Dominance strength maps to color saturation: dominant = vivid, contested = muted
- Height and color reinforce the same data axis for clarity

---

## Lighting

### Composition B (Tectonic Plates)
- Single key light from upper-left at ~45 degrees
- Warm ambient fill
- Tall tiles cast long shadows onto neighbors, dramatizing dominance gaps
- Matte surface material (concrete/stone texture)

### Composition C (Siege Wall)
- Rim light from behind the central void — light leaks through the gap
- McD side: slightly warm supplementary light
- BK side: slightly cool supplementary light
- Overlapping block shadows create oppressive density near the wall

---

## Technical Pipeline

### Step 1: Data Acquisition (Python)
```
fetch_osm.py
  → Overpass API queries for amenity=fast_food + brand=McDonald's / Burger King
  → Deduplicate, validate coordinates
  → Enrich with country code (reverse geocoding or point-in-polygon)
  → Merge with country-level statistics for gap-filling
  → Output: stores.json
```

### Step 2: Geometry Generation (Python)
```
generate_tectonic.py
  → Read stores.json
  → Squarified Treemap layout (country clusters by total size)
  → Subdivide each country block into per-store micro-tiles
  → Displace edges with Perlin noise for organic polygons
  → Calculate extrusion heights from dominance data
  → Export mesh data for Blender

generate_siege.py
  → Read stores.json
  → Split into McD/BK groups
  → Cluster by country, order by size
  → Pack blocks with density gradient toward center wall
  → Calculate heights from dominance data
  → Export mesh data for Blender
```

### Step 3: Blender Scene (Python bpy)
```
  → Import mesh geometry
  → Assign materials per dominance category
  → Configure Cycles renderer
  → Set up lighting rigs (per composition)
  → Position camera
  → Render 6000x4000 PNG (256-512 samples)
```

### Step 4: Post-Process (Python/Pillow)
```
  → Levels adjustment, sharpening
  → Label/title overlay
  → Final PNG export
```

---

## Directory Structure
```
data-art/burger-wars/
├── data/
│   ├── fetch_osm.py          # Overpass API data fetcher
│   └── stores.json           # Combined store data
├── generate_tectonic.py      # Composition B generator
├── generate_siege.py         # Composition C generator
├── common.py                 # Shared utilities (color, treemap, etc.)
├── output/
│   ├── tectonic.png
│   └── siege.png
├── docs/
│   └── superpowers/specs/
│       └── 2026-04-08-burger-wars-design.md
└── README.md
```

## Dependencies
- Blender 4.x (bpy module)
- Python 3.8+
- requests (Overpass API)
- numpy
- Pillow (post-process)

---

## Success Criteria
1. Both compositions render at 6000x4000 without artifacts
2. All ~58,000 stores represented (validated against country totals)
3. McDonald's 2:1 dominance is immediately visible in both compositions
4. Brand colors are recognizable but not garish
5. Print at A2 or larger looks sharp and detailed — close inspection reveals individual store tiles/blocks
6. Visually distinct from all existing data-art projects (no particles, no flow fields, no circular forms)
