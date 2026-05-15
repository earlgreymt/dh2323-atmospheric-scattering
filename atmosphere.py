import numpy as np

def normalise(v):
    return v / np.linalg.norm(v)

#atmosphere content 
PLANET_RADIUS = 1.0 #everything else is scaled to this unit
ATMO_RADIUS   = 1.15 #atmosphere thickenss is hence 0.15 units
SCALE_HEIGHT  = 0.025 #controls how quickly the atmosphere density falls off with altitude


#Rayleigh constants 
# Physical ratio 1/λ⁴ for λ_R=700nm, λ_G=550nm, λ_B=440nm
RAYLEIGH_COEFF = np.array([2.0, 4.6, 11.3])
SUN_INTENSITY = np.array([20.0, 15.0, 10.0]) 

#MIE scattering constants
MIE_COEFF = np.array([15.0, 15.0, 15.0]) #higher means more haze, lower means clearer skies
MIE_G     = 0.98 #higher means more forward scattering (hazy), lower means more isotropic (clear)
MIE_SCALE_HEIGHT = 0.015 #higher means more haze near the surface, lower means more uniform haze distribution

VIEW_SAMPLES = 20 #number of steps to march along the view ray through the atmosphere
SUN_SAMPLES  = 10 #number of steps to march along the ray towards the sun when calculating optical depth


def length(v):
    return np.sqrt(np.dot(v, v))


# ray sphere intersection 
def ray_sphere_intersect(ro, rd, radius):
    a = np.dot(rd, rd)
    b = 2.0 * np.dot(ro, rd)
    c = np.dot(ro, ro) - radius * radius
    discriminant = b * b - 4.0 * a * c
    if discriminant < 0:
        return None
    sqrt_disc = np.sqrt(discriminant)
    t1 = (-b - sqrt_disc) / (2.0 * a)
    t2 = (-b + sqrt_disc) / (2.0 * a)
    return (t1, t2)


# atmospheric density 
def density_at(point):
    altitude = length(point) - PLANET_RADIUS
    altitude = max(altitude, 0.0)
    return np.exp(-altitude / SCALE_HEIGHT)


# optical depth towards sun from a point in the atmosphere
def optical_depth_sun(point, sun_dir):
    # if the planet sits between this point and the sun, it's fully in shadow
    planet_hit = ray_sphere_intersect(point, sun_dir, PLANET_RADIUS)
    if planet_hit is not None:
        _, t2 = planet_hit
        if t2 > 1e-4:          # planet exit is ahead → sun is blocked
            return 1e9

    hit = ray_sphere_intersect(point, sun_dir, ATMO_RADIUS)
    if hit is None:
        return 0.0
    _, t_sun = hit
    if t_sun <= 0.0:
        return 0.0

    step_size = t_sun / SUN_SAMPLES
    optical_depth = 0.0
    for i in range(SUN_SAMPLES):
        sample_point = point + sun_dir * (i + 0.5) * step_size
        optical_depth += density_at(sample_point) * step_size
    return optical_depth


# main ray march-> the brute force function that computes the colour for each pixel by marching through the atmosphere along the view ray and accumulating scattering contributions
def compute_pixel_colour(ro, rd, sun_dir):
    """Return the scattered atmosphere colour for one pixel."""
    sun_n = normalise(sun_dir)
    colour = np.zeros(3)

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

    # Rayleigh phase function: (3/16π)(1 + cos²θ)
    # θ is the angle between the view ray and the sun direction.
    # Maximum at forward (cos_theta=1) and backward (cos_theta=-1) scattering.
    cos_theta = np.dot(rd, sun_n)
    phase = (3.0 / (16.0 * np.pi)) * (1.0 + cos_theta * cos_theta)

    step_size = (t_end - t_start) / VIEW_SAMPLES
    optical_depth_view = 0.0

    for i in range(VIEW_SAMPLES):
        t = t_start + (i + 0.5) * step_size
        sample_point = ro + rd * t

        density   = density_at(sample_point)
        sample_od = density * step_size
        optical_depth_view += sample_od

        od_sun   = optical_depth_sun(sample_point, sun_n)
        total_od = optical_depth_view + od_sun

        transmittance = np.exp(-RAYLEIGH_COEFF * total_od)
        colour += transmittance * sample_od * RAYLEIGH_COEFF * phase

    colour *= SUN_INTENSITY
    return colour
