# Canvas defaults
WIDTH = 1400
HEIGHT = 900

# Icon base dimensions (reference size)
ICON_WIDTH = 80  # Base reference for all proportional calculations
ICON_HEIGHT = 50

# === PROPORTIONAL VALUES (based on ICON_WIDTH) ===

# Spacing between elements
SPACING_SMALL = ICON_WIDTH * 0.5        # 40px - spacing between elements in tight layouts
SPACING_MEDIUM = ICON_WIDTH * 0.625     # 50px - margins and gaps
SPACING_LARGE = ICON_WIDTH * 1.25       # 100px - vertical spacing between levels
SPACING_XLARGE = ICON_WIDTH * 1.5       # 120px - horizontal spacing between elements
SPACING_XXLARGE = ICON_WIDTH * 1.875    # 150px - large gaps and initial margins
SPACING_HUGE = ICON_WIDTH * 3.125       # 250px - container spacing

# Container padding
CONTAINER_PADDING = ICON_WIDTH * 0.125  # 10px - internal padding of containers
CONTAINER_SPACING = SPACING_HUGE        # 250px - spacing between containers
CONTAINER_ELEMENT_SPACING = SPACING_XLARGE  # 120px - spacing between elements in container
CONTAINER_ICON_HEIGHT = ICON_HEIGHT     # 50px - height of container icon/header

# Text and label dimensions
TEXT_LINE_HEIGHT = ICON_WIDTH * 0.225   # 18px - height per line of text
TEXT_CHAR_WIDTH = ICON_WIDTH * 0.1      # 8px - approximate width per character
TEXT_CHAR_WIDTH_NARROW = ICON_WIDTH * 0.0875  # 7px - narrow character width for connections

# Label offsets from icons
LABEL_OFFSET_BOTTOM = ICON_WIDTH * 0.25    # 20px - distance below icon
LABEL_OFFSET_TOP = ICON_WIDTH * 0.125      # 10px - distance above icon
LABEL_OFFSET_SIDE = ICON_WIDTH * 0.1875    # 15px - distance left/right of icon
LABEL_OFFSET_VERTICAL = ICON_WIDTH * 0.1875  # 15px - vertical offset for contained elements

# Container label positioning
CONTAINER_ICON_X = CONTAINER_PADDING       # 10px - left padding for container icon
CONTAINER_ICON_Y = 0                       # 0px - no top padding (flush with top)
CONTAINER_LABEL_X = CONTAINER_PADDING + ICON_WIDTH + CONTAINER_PADDING  # 100px - after icon + margins
CONTAINER_LABEL_Y = ICON_WIDTH * 0.2       # 16px - baseline alignment with icon

# Canvas margins for expansion
CANVAS_MARGIN_SMALL = ICON_WIDTH * 0.625   # 50px - small margin
CANVAS_MARGIN_LARGE = ICON_WIDTH * 1.25    # 100px - large margin
CANVAS_MARGIN_XLARGE = ICON_WIDTH * 1.875  # 150px - extra large margin

# Movement and optimization
MOVEMENT_THRESHOLD = ICON_WIDTH * 1.0      # 80px - minimum space to move element
MOVEMENT_MAX_DISTANCE = ICON_WIDTH * 1.25  # 100px - maximum movement distance
MOVEMENT_DEFAULT_DY = ICON_WIDTH * 0.75    # 60px - default vertical movement

# Grid and layout
GRID_SPACING_SMALL = ICON_WIDTH * 0.25     # 20px - tight grid spacing
GRID_SPACING_LARGE = SPACING_SMALL         # 40px - normal grid spacing

# Radial layout (for priority-based positioning)
RADIUS_NORMAL_MAX = ICON_WIDTH * 3.125     # 250px - max radius for normal priority
RADIUS_LOW_MAX = ICON_WIDTH * 4.375        # 350px - max radius for low priority

# Label optimizer penalties (proportional for consistency)
PENALTY_OUTSIDE_CANVAS = 1000              # Out of canvas
PENALTY_COLLISION_ELEMENT = 100            # Collision with element
PENALTY_COLLISION_LABEL = 50               # Collision with label
PENALTY_COLLISION_LINE = 75                # Collision with connection line
PENALTY_DENSITY_LOCAL = 60                 # Per nearby label
DENSITY_SEARCH_RADIUS = ICON_WIDTH * 0.9375  # 75px - search radius for local density

# Connection label
CONNECTION_BBOX_PADDING = ICON_WIDTH * 0.1  # 8px - padding around connection line

# Top margin for debug visual area
TOP_MARGIN_DEBUG = ICON_WIDTH              # 80px - area for debug badges
TOP_MARGIN_NORMAL = ICON_WIDTH * 0.25      # 20px - normal top margin

# === LAF (Layout Abstracto Primero) System ===
# LAF spacing configuration
LAF_SPACING_BASE = ICON_WIDTH * 6.0        # 480px - base spacing for LAF layout
LAF_VERTICAL_FACTOR = 0.5                  # Vertical spacing factor (0.5 = 50%)
LAF_VERTICAL_SPACING = LAF_SPACING_BASE * LAF_VERTICAL_FACTOR  # 240px - vertical spacing between levels
