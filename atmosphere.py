import numpy as np

def normalise(v):
    return v / np.linalg.norm(v)

# ── ATMOSPHERE CONSTANTS ──────────────────────────────────────────
# all distances are in "scene units" where planet radius = 1.0

PLANET_RADIUS    = 1.0        # solid planet surface
ATMO_RADIUS      = 1.15        # outer edge of atmosphere shell
SCALE_HEIGHT     = 0.1       # how fast density drops with altitude
                               # smaller = thinner atmosphere

# Rayleigh scattering coefficients per RGB channel
# based on real wavelengths: red=700nm, green=550nm, blue=440nm
# blue scatters ~5.5x more than red (proportional to 1/wavelength^4)
RAYLEIGH_COEFF = np.array([0.0030, 0.0090, 0.0400])

# sun light colour and intensity
SUN_INTENSITY  = np.array([1.2, 1.1, 1.0])

# number of steps along each view ray
# more steps = more accurate but slower
VIEW_SAMPLES   = 16

# number of steps towards the sun at each view ray point
SUN_SAMPLES    = 8


# ── HELPER: VECTOR LENGTH ─────────────────────────────────────────
def length(v):
    return np.sqrt(np.dot(v, v))


# ── STEP 1: RAY SPHERE INTERSECTION ──────────────────────────────
def ray_sphere_intersect(ro, rd, radius):
    """
    Find where a ray hits a sphere centred at the origin.

    ro = ray origin (3D point)
    rd = ray direction (normalised 3D vector)
    radius = sphere radius

    Returns (t1, t2) distances along the ray, or None if no hit.
    t1 is entry point, t2 is exit point.
    """
    # expand |ro + t*rd|^2 = radius^2 into quadratic at^2 + bt + c = 0
    a = np.dot(rd, rd)
    b = 2.0 * np.dot(ro, rd)
    c = np.dot(ro, ro) - radius * radius

    discriminant = b * b - 4.0 * a * c

    # no real solution = ray misses the sphere
    if discriminant < 0:
        return None

    sqrt_disc = np.sqrt(discriminant)
    t1 = (-b - sqrt_disc) / (2.0 * a)
    t2 = (-b + sqrt_disc) / (2.0 * a)

    return (t1, t2)


# ── STEP 2: ATMOSPHERIC DENSITY ───────────────────────────────────
def density_at(point):
    """
    Returns atmospheric density at a 3D point.
    Density falls off exponentially with altitude above planet surface.
    """
    altitude = length(point) - PLANET_RADIUS
    # clamp altitude so we never go below surface
    altitude = max(altitude, 0.0)
    return np.exp(-altitude / SCALE_HEIGHT)


# ── STEP 3: OPTICAL DEPTH TOWARDS SUN ────────────────────────────
def optical_depth_sun(point, sun_dir):
    """
    From a point in the atmosphere, march towards the sun and
    accumulate how much atmosphere the sunlight passes through.
    This tells us how much sunlight is blocked/scattered before
    reaching our point.
    """
    # check if sun ray exits the atmosphere
    hit = ray_sphere_intersect(point, sun_dir, ATMO_RADIUS)
    if hit is None:
        return 0.0

    _, t_sun = hit
    step_size = t_sun / SUN_SAMPLES
    optical_depth = 0.0

    for i in range(SUN_SAMPLES):
        # march along sun ray
        sample_point = point + sun_dir * (i + 0.5) * step_size
        optical_depth += density_at(sample_point) * step_size

    return optical_depth


# ── STEP 4: MAIN RAY MARCH ────────────────────────────────────────
def compute_pixel_colour(ro, rd, sun_dir):
    colour = np.zeros(3)
    sun_n = normalise(sun_dir)

    atmo_hit = ray_sphere_intersect(ro, rd, ATMO_RADIUS)
    if atmo_hit is None:
        return colour

    t_start, t_end = atmo_hit

    planet_hit = ray_sphere_intersect(ro, rd, PLANET_RADIUS)
    if planet_hit is not None:
        t_planet, _ = planet_hit
        if t_planet > 0:
            t_end = min(t_end, t_planet)

    t_start = max(t_start, 0.0)
    if t_start >= t_end:
        return colour

    step_size = (t_end - t_start) / VIEW_SAMPLES
    optical_depth_view = 0.0

    for i in range(VIEW_SAMPLES):
        t = t_start + (i + 0.5) * step_size
        sample_point = ro + rd * t

        # direction from sample point outward (away from planet centre)
        outward = normalise(sample_point)

        # how much is this sample point facing the sun
        # positive = sun side, negative = night side
        sun_angle = np.dot(outward, sun_n)

        # only contribute if this point is on the sun-facing hemisphere
        # soft falloff towards the terminator
        sun_factor = max(sun_angle + 0.2, 0.0)

        sample_density = density_at(sample_point) * step_size
        optical_depth_view += sample_density

        od_sun = optical_depth_sun(sample_point, sun_n)
        total_od = optical_depth_view + od_sun

        transmittance = np.exp(-RAYLEIGH_COEFF * total_od)

        # multiply contribution by sun factor
        colour += transmittance * sample_density * RAYLEIGH_COEFF * sun_factor

    colour *= SUN_INTENSITY * 35.0

    return colour