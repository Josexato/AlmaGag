# SDJF v2.0 - Optional Coordinates & Proportional Sizing

## Overview

SDJF (Simple Diagram JSON Format) v2.0 introduces two major enhancements:
1. **Optional Coordinates** - `x` and `y` are now optional; auto-layout calculates positions
2. **Proportional Sizing** - `hp` and `wp` properties for flexible element sizing

## Optional Coordinates

### No Coordinates (Full Auto-Layout)

Elements without `x` and `y` coordinates are automatically positioned using a hybrid algorithm:

```json
{
  "elements": [
    {
      "id": "server1",
      "type": "server",
      "label": "Auto-positioned"
    }
  ]
}
```

**Auto-Layout Strategy:**
- **HIGH priority** elements → Center (compact grid)
- **NORMAL priority** elements → Around center (middle ring)
- **LOW priority** elements → Periphery (outer ring)

Priority is determined by:
- **Manual**: `"label_priority": "high"` / `"normal"` / `"low"`
- **Automatic**: Based on connection count
  - ≥4 connections = HIGH
  - 2-3 connections = NORMAL
  - <2 connections = LOW

### Partial Coordinates

You can specify only `x` or only `y`:

```json
{
  "elements": [
    {
      "id": "server1",
      "type": "server",
      "y": 300,
      "label": "Fixed Y, auto X"
    },
    {
      "id": "server2",
      "type": "server",
      "x": 500,
      "label": "Fixed X, auto Y"
    }
  ]
}
```

**Behavior:**
- **Missing X**: Calculated based on level grouping (elements with similar Y)
- **Missing Y**: Calculated based on priority (HIGH=top, NORMAL=middle, LOW=bottom)

## Proportional Sizing

### Height and Width Proportions

Use `hp` (height proportion) and `wp` (width proportion) to scale elements:

```json
{
  "id": "big-server",
  "type": "server",
  "hp": 2.0,
  "wp": 1.5,
  "label": "Large Server"
}
```

**Default Icon Sizes:**
- `ICON_WIDTH = 80px`
- `ICON_HEIGHT = 50px`

**Final Size Calculation:**
- `width = ICON_WIDTH × wp`
- `height = ICON_HEIGHT × hp`

**Examples:**
| hp | wp | Final Size | Description |
|----|----|-----------|-|
| 1.0 | 1.0 | 80×50 | Default |
| 2.0 | 1.0 | 80×100 | Double height |
| 1.0 | 1.5 | 120×50 | 1.5× wider |
| 2.0 | 2.0 | 160×100 | Double both |
| 0.8 | 0.8 | 64×40 | 20% smaller |

### Size Affects Layout

**Centrality:** Larger elements (hp/wp > 1.0) are positioned more centrally during auto-layout.

**Weight in Optimization:** Larger elements resist movement during collision resolution:
- **Weight = hp × wp** (proportional to area)
- Movement scaled by **1/weight**
- Example: Element with `hp=2.0, wp=2.0` → weight=4.0 → moves 1/4 as much

### Priority Resolution

Sizing properties have priority order:

1. **Explicit `width`/`height`** (containers)
2. **`hp`/`wp` multipliers**
3. **Default** (`ICON_WIDTH`, `ICON_HEIGHT`)

```json
{
  "id": "custom",
  "width": 200,
  "hp": 2.0
}
```
→ Uses `width=200` (explicit wins), `height=100` (hp applies)

## Complete Example: Hybrid Layout

```json
{
  "canvas": {"width": 1000, "height": 800},
  "elements": [
    {
      "id": "load-balancer",
      "hp": 2.0,
      "wp": 1.5,
      "label": "Load Balancer",
      "label_priority": "high",
      "color": "gold"
    },
    {
      "id": "app-server-1",
      "hp": 1.5,
      "label": "App Server 1",
      "color": "lightblue"
    },
    {
      "id": "database",
      "hp": 1.8,
      "wp": 1.3,
      "label": "Database",
      "label_priority": "high",
      "color": "orange"
    },
    {
      "id": "logger",
      "hp": 0.8,
      "wp": 0.8,
      "label": "Logger",
      "label_priority": "low",
      "color": "gray"
    }
  ],
  "connections": [
    {"from": "load-balancer", "to": "app-server-1"},
    {"from": "app-server-1", "to": "database"},
    {"from": "app-server-1", "to": "logger"}
  ]
}
```

**Result:**
- **load-balancer** (HIGH, large) → Center, hard to move
- **database** (HIGH, large) → Center, hard to move
- **app-server-1** (NORMAL, medium) → Around center
- **logger** (LOW, small) → Periphery, easy to move

## Backward Compatibility

SDJF v2.0 is **100% backward compatible**:
- Elements with `x`, `y` → Positioned exactly as specified
- Elements without `hp`, `wp` → Use default size (80×50)
- Existing `.gag` files work identically

## Examples

See `docs/examples/`:
- **08-auto-layout.gag** - Full auto-layout (no coordinates)
- **09-proportional-sizing.gag** - Various hp/wp values
- **10-hybrid-layout.gag** - Combined: auto-layout + hp/wp + priorities

## Technical Details

### Auto-Layout Algorithm

1. **Analyze Graph**
   - Build adjacency graph
   - Calculate priorities (manual or automatic)
   - Identify connected components

2. **Position Elements**
   - Group by priority (HIGH/NORMAL/LOW)
   - Sort by centrality score: `(3 - priority) × hp × wp`
   - HIGH → Compact grid at center
   - NORMAL → Ring around center (radius=300)
   - LOW → Outer ring (radius=450)

3. **Collision Resolution**
   - Detect overlaps between elements/labels/connections
   - Select victim weighted by: `collisions / (hp × wp)`
   - Move victim (scaled by 1/weight)
   - Iterate up to max_iterations (default: 10)

### Weight-Based Movement

When resolving collisions:

```python
weight = hp × wp
movement_x = original_dx / weight
movement_y = original_dy / weight
```

Example: Element with `hp=2.0, wp=2.0` moving 100px right:
- weight = 4.0
- actual movement = 100 / 4.0 = 25px

## Containers

**Note:** Containers (elements with `contains` property) do NOT use `hp`/`wp`.
They use `aspect_ratio` and calculate size dynamically based on contained elements.

## Future Enhancements

Potential v2.1 features:
- `margin` property for spacing around elements
- Force-directed layout option
- Alignment constraints (align-left, align-center, etc.)
- Smart connector routing avoiding elements
