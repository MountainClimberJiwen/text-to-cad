"""Generate the base plate part."""
from build123d import Box, Part

# 100x60x5 mm base plate
part = Part(Box(100, 60, 5))
