"""Generate a cylindrical peg."""
from build123d import Cylinder, Part

# 8mm diameter, 15mm long peg
part = Part(Cylinder(4, 15))
