import numpy as np
from atmosphere import (
    PLANET_RADIUS,
    ray_sphere_intersect,
)


OCEAN_COLOUR = np.array([0.01, 0.05, 0.25])   # Deep, dark navy
LAND_COLOUR  = np.array([0.05, 0.25, 0.05])   # Deep forest green
SNOW_COLOUR  = np.array([0.8,  0.8,  0.9])    # Slightly blue-tinted white
CLOUD_COLOUR = np.array([1.0,  1.0,  1.0])


def length(v):
    return np.sqrt(np.dot(v, v))


def surface_colour(normal):
    y = abs(normal[1])
    if y > 0.7:
        return SNOW_COLOUR
    land_mask = np.sin(normal[0] * 8.0) * np.cos(normal[2] * 6.0)
    if land_mask > 0.15:
        return LAND_COLOUR
    return OCEAN_COLOUR


#Returns the Lambertian-shaded surface colour, or None if the ray misses.
# Atmospheric glow and tinting are composited on top in renderer.py.
def shade_planet(ro, rd, sun_dir):
    hit = ray_sphere_intersect(ro, rd, PLANET_RADIUS)
    if hit is None:
        return None

    t_planet, _ = hit
    if t_planet < 0:
        return None

    hit_point = ro + rd * t_planet
    normal    = hit_point / length(hit_point)

    # Lambertian diffuse — clamp negative (night side) to zero
    diffuse = max(np.dot(normal, sun_dir), 0.0)
    ambient = 0.03   # faint night-side glow so poles/oceans aren't pure black

    surf_colour = surface_colour(normal)

    return surf_colour * (diffuse + ambient)
