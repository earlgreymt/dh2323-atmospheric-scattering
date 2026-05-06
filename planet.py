import numpy as np
from atmosphere import (
    PLANET_RADIUS,
    ATMO_RADIUS,
    RAYLEIGH_COEFF,
    ray_sphere_intersect,
    density_at,
    optical_depth_sun
)

# ── PLANET SURFACE COLOURS ────────────────────────────────────────
OCEAN_COLOUR = np.array([0.05, 0.15, 0.5])   # deep blue ocean
LAND_COLOUR  = np.array([0.15, 0.4,  0.15])  # green land
SNOW_COLOUR  = np.array([0.9,  0.9,  0.9])   # white poles
CLOUD_COLOUR = np.array([1.0,  1.0,  1.0])   # white clouds

# ── HELPER: VECTOR LENGTH ─────────────────────────────────────────
def length(v):
    return np.sqrt(np.dot(v, v))


# ── SURFACE COLOUR BY POSITION ────────────────────────────────────
def surface_colour(normal):
    """
    Given a surface normal vector, return a surface colour.
    We use the Y component of the normal to decide:
    - near poles (high |y|) = snow
    - mid latitudes         = land or ocean
    - equatorial            = ocean

    normal = normalised surface normal (points away from planet centre)
    """
    y = abs(normal[1])  # latitude proxy — 0 at equator, 1 at poles

    # polar caps — snow above 70 degrees latitude
    if y > 0.7:
        return SNOW_COLOUR

    # use x and z to create a simple land/ocean pattern
    # this gives a rough continent-like distribution
    land_mask = np.sin(normal[0] * 8.0) * np.cos(normal[2] * 6.0)

    if land_mask > 0.15:
        return LAND_COLOUR
    else:
        return OCEAN_COLOUR


# ── ATMOSPHERIC TINT ON SURFACE ───────────────────────────────────
def atmosphere_on_surface(hit_point, sun_dir):
    """
    Compute how much atmosphere sits between the surface hit point
    and the sun. This dims and tints the surface near the terminator
    (day/night boundary) — giving the planet a more realistic look.
    """
    od = optical_depth_sun(hit_point, sun_dir)
    transmittance = np.exp(-RAYLEIGH_COEFF * od * 2.0)
    return transmittance


# ── MAIN PLANET SHADING FUNCTION ─────────────────────────────────
def shade_planet(ro, rd, sun_dir):
    """
    Given a camera ray, compute the planet surface colour if the
    ray hits the planet. Returns the surface colour or None if
    the ray does not hit the planet.

    ro      = ray origin (camera position)
    rd      = ray direction (normalised)
    sun_dir = direction towards the sun (normalised)
    """
    # check if ray hits planet surface
    hit = ray_sphere_intersect(ro, rd, PLANET_RADIUS)
    if hit is None:
        return None

    t_planet, _ = hit
    if t_planet < 0:
        # planet is behind the camera
        return None

    # ── compute hit point and surface normal ──
    hit_point = ro + rd * t_planet

    # surface normal points outward from planet centre
    # planet is centred at origin so normal = normalised hit point
    normal = hit_point / length(hit_point)

    # ── basic diffuse lighting ──
    # dot product of normal and sun direction
    # 1.0 = directly facing sun (bright)
    # 0.0 = edge on (terminator)
    # negative = dark side (night)
    diffuse = max(np.dot(normal, sun_dir), 0.0)

    # small ambient term so night side is not completely black
    ambient = 0.02

    # ── get surface colour based on position ──
    surf_colour = surface_colour(normal)

    # ── apply atmospheric tint ──
    # atmosphere dims the surface near the terminator
    atmo_tint = atmosphere_on_surface(hit_point, sun_dir)

    # ── combine everything ──
    final_colour = surf_colour * (diffuse + ambient) * atmo_tint

    return final_colour