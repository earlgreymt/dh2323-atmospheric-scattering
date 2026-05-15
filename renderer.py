import numpy as np
import pygame
import sys
from camera import Camera
from atmosphere import (PLANET_RADIUS, ATMO_RADIUS, SCALE_HEIGHT,
                        RAYLEIGH_COEFF, SUN_INTENSITY,
                        MIE_COEFF, MIE_G, MIE_SCALE_HEIGHT,
                        VIEW_SAMPLES, SUN_SAMPLES)
from planet import OCEAN_COLOUR, LAND_COLOUR, SNOW_COLOUR
import os
import datetime

#window settings 
LOW_RES_W  = 200
LOW_RES_H  = 150
HIGH_RES_W = 800
HIGH_RES_H = 600

#sun directions for presets
SUN_DIRECTIONS = [
    np.array([ 0.0,  0.3,  1.0]),   # noon
    np.array([ 1.0,  0.05, 0.2]),   # sunset
    np.array([ 0.8,  0.0, -0.4]),   # deep sunset
    np.array([ 0.0,  0.0, -1.0]),   # backlit
]

EXPOSURE = 1.0 # lower exposure 


def normalise(v):
    return v / np.linalg.norm(v)


def rotate_camera(position, axis, angle_deg):
    angle = np.radians(angle_deg)
    axis  = normalise(axis)
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    return (position * cos_a
            + np.cross(axis, position) * sin_a
            + axis * np.dot(axis, position) * (1 - cos_a))


# vectorised render (combineing rayleigh, mie, and lambertian shading in one pass by marchin)
def render_frame(camera, sun_dir, width, height):
    
    sun_n = sun_dir / np.linalg.norm(sun_dir)

    #Camera and Ray Setup 
    fov_rad  = np.radians(camera.fov)
    aspect   = width / height
    px_g, py_g = np.meshgrid(np.arange(width), np.arange(height))

    screen_x = (2.0 * (px_g + 0.5) / width  - 1.0) * aspect * np.tan(fov_rad / 2.0)
    screen_y = (1.0 - 2.0 * (py_g + 0.5) / height)        * np.tan(fov_rad / 2.0)

    forward  = -camera.position / np.linalg.norm(camera.position)
    world_up = np.array([0.0, 1.0, 0.0])
    if abs(np.dot(forward, world_up)) > 0.99:
        world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, world_up);  right /= np.linalg.norm(right)
    up    = np.cross(right,   forward);   up    /= np.linalg.norm(up)

    # (H, W, 3) Ray Directions
    rd  = (forward
           + right * screen_x[:, :, np.newaxis]
           + up    * screen_y[:, :, np.newaxis])
    rd /= np.linalg.norm(rd, axis=2, keepdims=True)

    ro = camera.position

    # Intersection Logic
    def isect(radius):
        b    = 2.0 * np.einsum('hwc,c->hw', rd, ro)
        c    = float(np.dot(ro, ro)) - radius * radius
        disc = b * b - 4.0 * c
        hit  = disc >= 0
        sq   = np.sqrt(np.maximum(disc, 0.0))
        return (-b - sq) / 2.0, (-b + sq) / 2.0, hit

    at1, at2, a_hit = isect(ATMO_RADIUS)
    pt1, _,   p_hit = isect(PLANET_RADIUS)

    t_start = np.maximum(at1, 0.0)
    t_end   = np.where(p_hit & (pt1 > 0), np.minimum(at2, pt1), at2)
    active  = a_hit & (t_start < t_end)

    step_v  = np.where(active, (t_end - t_start) / VIEW_SAMPLES, 0.0)

    # Phase Functions
    cos_th = np.einsum('hwc,c->hw', rd, sun_n)
    
    # Rayleigh Phase
    phase_r = (3.0 / (16.0 * np.pi)) * (1.0 + cos_th ** 2)
    
    # Mie Phase (Henyey-Greenstein)
    g, g2   = MIE_G, MIE_G * MIE_G
    phase_m = (1.0 - g2) / (4.0 * np.pi * np.power(1.0 + g2 - 2.0 * g * cos_th, 1.5))

    # Main Ray March 
    colour      = np.zeros((height, width, 3))
    od_view_r   = np.zeros((height, width))
    od_view_m   = np.zeros((height, width))

    for i in range(VIEW_SAMPLES):
        t         = t_start + (i + 0.5) * step_v
        sp        = ro + rd * t[:, :, np.newaxis]

        alt       = np.maximum(np.linalg.norm(sp, axis=2) - PLANET_RADIUS, 0.0)
        
        # Rayleigh and Mie Densities
        den_r     = np.exp(-alt / SCALE_HEIGHT)
        den_m     = np.exp(-alt / MIE_SCALE_HEIGHT)
        
        sample_od_r = den_r * step_v
        sample_od_m = den_m * step_v
        
        od_view_r += np.where(active, sample_od_r, 0.0)
        od_view_m += np.where(active, sample_od_m, 0.0)

        # Sun-ray geometry
        A    = np.einsum('hwc,c->hw', sp, sun_n)
        sp2  = np.einsum('hwc,hwc->hw', sp, sp)

        # Shadow Check
        disc_p = A * A - (sp2 - PLANET_RADIUS**2)
        shadow = (disc_p >= 0) & ((-A + np.sqrt(np.maximum(disc_p, 0.0))) > 1e-4)

        # Sun path atmosphere intersection
        disc_a  = A * A - (sp2 - ATMO_RADIUS**2)
        t2_a    = np.where(disc_a >= 0, -A + np.sqrt(np.maximum(disc_a, 0.0)), 0.0)
        step_s  = np.where((disc_a >= 0) & (t2_a > 0), t2_a / SUN_SAMPLES, 0.0)

        od_sun_r = np.zeros((height, width))
        od_sun_m = np.zeros((height, width))
        
        for j in range(SUN_SAMPLES):
            ts      = (j + 0.5) * step_s
            sun_pt  = sp + sun_n * ts[:, :, np.newaxis]
            alt_s   = np.maximum(np.linalg.norm(sun_pt, axis=2) - PLANET_RADIUS, 0.0)
            od_sun_r += np.exp(-alt_s / SCALE_HEIGHT) * step_s
            od_sun_m += np.exp(-alt_s / MIE_SCALE_HEIGHT) * step_s

        od_sun_r = np.where(shadow, 1e9, od_sun_r)
        od_sun_m = np.where(shadow, 1e9, od_sun_m)

        # Combined Transmittance
        total_od_r = (od_view_r + od_sun_r)[:, :, np.newaxis]
        total_od_m = (od_view_m + od_sun_m)[:, :, np.newaxis]
        trans      = np.exp(-(RAYLEIGH_COEFF * total_od_r + MIE_COEFF * total_od_m))

        # Combined Scattering (Rayleigh + Mie)
        col_r = (sample_od_r * phase_r)[:, :, np.newaxis] * RAYLEIGH_COEFF
        col_m = (sample_od_m * phase_m)[:, :, np.newaxis] * MIE_COEFF
        colour += trans * (col_r + col_m) * active[:, :, np.newaxis]

    colour *= SUN_INTENSITY

    # View-side Transmittance (Limb Darkening)
    view_trans = np.exp(-(RAYLEIGH_COEFF * od_view_r[:, :, np.newaxis] + 
                          MIE_COEFF * od_view_m[:, :, np.newaxis]) * 2.2)

    #Planet Surface (Lambertian)
    p_active = p_hit & (pt1 > 0)
    hit_pt   = ro + rd * pt1[:, :, np.newaxis]
    norm_l   = np.maximum(np.linalg.norm(hit_pt, axis=2, keepdims=True), 1e-8)
    normal   = hit_pt / norm_l

    diffuse  = np.maximum(np.einsum('hwc,c->hw', normal, sun_n), 0.0)

    ny      = np.abs(normal[:, :, 1])
    lmask   = np.sin(normal[:, :, 0] * 8.0) * np.cos(normal[:, :, 2] * 6.0)
    snow    = ny > 0.7
    land    = (~snow) & (lmask > 0.15)

    sc = (snow[:, :, np.newaxis] * SNOW_COLOUR + 
          land[:, :, np.newaxis] * LAND_COLOUR + 
          (~snow & ~land)[:, :, np.newaxis] * OCEAN_COLOUR)

    planet_rgb = sc * (diffuse + 0.02)[:, :, np.newaxis]

    # Final Composition
    image = np.where(p_active[:, :, np.newaxis],
                     planet_rgb * view_trans + colour,
                     colour)

    return image

#def render_frame(camera, sun_dir, width, height):
    sun_n = sun_dir / np.linalg.norm(sun_dir)

    # ── HARD-CODED DRAMATIC CONSTANTS ────────────────────────────────
    # These override any external imports to ensure the effect is visible
    R_COEFF   = np.array([2.0, 4.6, 11.3]) # Rayleigh scattering coefficients

    S_HEIGHT  = 0.025                      # Rayleigh scale height

    # MIE HARD-CODES: Cranked up for maximum visual difference
    M_COEFF   = np.array([10.0, 10.0, 10.0]) # INCREASED from 3.6 to 20.0 (Thick haze)
    M_G       = 0.98                         # INCREASED from 0.85 to 0.98 (Sharp Sun Halo)
    M_S_HEIGHT = 0.015                       # INCREASED from 0.007 to 0.015 (Higher haze)
    
    INTENSITY = np.array([20.0, 15.0, 10.0]) # Sun brightness
    # ────────────────────────────────────────────────────────────────

    # Camera and Ray Setup 
    fov_rad  = np.radians(camera.fov)
    aspect   = width / height
    px_g, py_g = np.meshgrid(np.arange(width), np.arange(height))

    screen_x = (2.0 * (px_g + 0.5) / width  - 1.0) * aspect * np.tan(fov_rad / 2.0)
    screen_y = (1.0 - 2.0 * (py_g + 0.5) / height)        * np.tan(fov_rad / 2.0)

    forward  = -camera.position / np.linalg.norm(camera.position)
    world_up = np.array([0.0, 1.0, 0.0])
    if abs(np.dot(forward, world_up)) > 0.99:
        world_up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, world_up);  right /= np.linalg.norm(right)
    up    = np.cross(right,   forward);   up    /= np.linalg.norm(up)

    # (H, W, 3) Ray Directions
    rd  = (forward
           + right * screen_x[:, :, np.newaxis]
           + up    * screen_y[:, :, np.newaxis])
    rd /= np.linalg.norm(rd, axis=2, keepdims=True)

    ro = camera.position

    # Intersection Logic
    def isect(radius):
        b    = 2.0 * np.einsum('hwc,c->hw', rd, ro)
        c    = float(np.dot(ro, ro)) - radius * radius
        disc = b * b - 4.0 * c
        hit  = disc >= 0
        sq   = np.sqrt(np.maximum(disc, 0.0))
        return (-b - sq) / 2.0, (-b + sq) / 2.0, hit

    at1, at2, a_hit = isect(ATMO_RADIUS)
    pt1, _,   p_hit = isect(PLANET_RADIUS)

    t_start = np.maximum(at1, 0.0)
    t_end   = np.where(p_hit & (pt1 > 0), np.minimum(at2, pt1), at2)
    active  = a_hit & (t_start < t_end)

    step_v  = np.where(active, (t_end - t_start) / VIEW_SAMPLES, 0.0)

    # Phase Functions
    cos_th = np.einsum('hwc,c->hw', rd, sun_n)
    
    # Rayleigh Phase
    phase_r = (3.0 / (16.0 * np.pi)) * (1.0 + cos_th ** 2)
    
    # Mie Phase (Henyey-Greenstein) - Using HARD-CODED M_G
    g, g2   = M_G, M_G * M_G
    phase_m = (1.0 - g2) / (4.0 * np.pi * np.power(1.0 + g2 - 2.0 * g * cos_th, 1.5))

    # Main Ray March 
    colour      = np.zeros((height, width, 3))
    od_view_r   = np.zeros((height, width))
    od_view_m   = np.zeros((height, width))

    for i in range(VIEW_SAMPLES):
        t         = t_start + (i + 0.5) * step_v
        sp        = ro + rd * t[:, :, np.newaxis]

        alt       = np.maximum(np.linalg.norm(sp, axis=2) - PLANET_RADIUS, 0.0)
        
        # Rayleigh and Mie Densities - Using HARD-CODED S_HEIGHT and M_S_HEIGHT
        den_r     = np.exp(-alt / S_HEIGHT)
        den_m     = np.exp(-alt / M_S_HEIGHT)
        
        sample_od_r = den_r * step_v
        sample_od_m = den_m * step_v
        
        od_view_r += np.where(active, sample_od_r, 0.0)
        od_view_m += np.where(active, sample_od_m, 0.0)

        # Sun-ray geometry
        A    = np.einsum('hwc,c->hw', sp, sun_n)
        sp2  = np.einsum('hwc,hwc->hw', sp, sp)

        # Shadow Check
        disc_p = A * A - (sp2 - PLANET_RADIUS**2)
        shadow = (disc_p >= 0) & ((-A + np.sqrt(np.maximum(disc_p, 0.0))) > 1e-4)

        # Sun path atmosphere intersection
        disc_a  = A * A - (sp2 - ATMO_RADIUS**2)
        t2_a    = np.where(disc_a >= 0, -A + np.sqrt(np.maximum(disc_a, 0.0)), 0.0)
        step_s  = np.where((disc_a >= 0) & (t2_a > 0), t2_a / SUN_SAMPLES, 0.0)

        od_sun_r = np.zeros((height, width))
        od_sun_m = np.zeros((height, width))
        
        for j in range(SUN_SAMPLES):
            ts      = (j + 0.5) * step_s
            sun_pt  = sp + sun_n * ts[:, :, np.newaxis]
            alt_s   = np.maximum(np.linalg.norm(sun_pt, axis=2) - PLANET_RADIUS, 0.0)
            od_sun_r += np.exp(-alt_s / S_HEIGHT) * step_s
            od_sun_m += np.exp(-alt_s / M_S_HEIGHT) * step_s

        od_sun_r = np.where(shadow, 1e9, od_sun_r)
        od_sun_m = np.where(shadow, 1e9, od_sun_m)

        # Combined Transmittance - Using HARD-CODED R_COEFF and M_COEFF
        total_od_r = (od_view_r + od_sun_r)[:, :, np.newaxis]
        total_od_m = (od_view_m + od_sun_m)[:, :, np.newaxis]
        trans      = np.exp(-(R_COEFF * total_od_r + M_COEFF * total_od_m))

        # Combined Scattering (Rayleigh + Mie)
        col_r = (sample_od_r * phase_r)[:, :, np.newaxis] * R_COEFF
        col_m = (sample_od_m * phase_m)[:, :, np.newaxis] * M_COEFF
        colour += trans * (col_r + col_m) * active[:, :, np.newaxis]

    colour *= INTENSITY # Using HARD-CODED INTENSITY

    # View-side Transmittance (Limb Darkening)
    view_trans = np.exp(-(R_COEFF * od_view_r[:, :, np.newaxis] + 
                          M_COEFF * od_view_m[:, :, np.newaxis]) * 2.2)

    # Planet Surface (Lambertian)
    p_active = p_hit & (pt1 > 0)
    hit_pt   = ro + rd * pt1[:, :, np.newaxis]
    norm_l   = np.maximum(np.linalg.norm(hit_pt, axis=2, keepdims=True), 1e-8)
    normal   = hit_pt / norm_l

    diffuse  = np.maximum(np.einsum('hwc,c->hw', normal, sun_n), 0.0)

    ny      = np.abs(normal[:, :, 1])
    lmask   = np.sin(normal[:, :, 0] * 8.0) * np.cos(normal[:, :, 2] * 6.0)
    snow    = ny > 0.7
    land    = (~snow) & (lmask > 0.15)

    sc = (snow[:, :, np.newaxis] * SNOW_COLOUR + 
          land[:, :, np.newaxis] * LAND_COLOUR + 
          (~snow & ~land)[:, :, np.newaxis] * OCEAN_COLOUR)

    planet_rgb = sc * (diffuse + 0.02)[:, :, np.newaxis]

    # Final Composition
    image = np.where(p_active[:, :, np.newaxis],
                     planet_rgb * view_trans + colour,
                     colour)

    return image


# tone map 
def tone_map(image):
    image = 1.0 - np.exp(-image * EXPOSURE)
    return np.power(np.clip(image, 0, 1), 1.0 / 2.2)


#NUMPY IMAGE to PYGAME SURFACE 
def image_to_surface(image, display_w, display_h):
    img_uint8 = (tone_map(image) * 255).astype(np.uint8)
    surface   = pygame.surfarray.make_surface(np.transpose(img_uint8, (1, 0, 2)))
    return pygame.transform.scale(surface, (display_w, display_h))


# save png
def save_png(image, folder="renders"):
    if not os.path.exists(folder):
        os.makedirs(folder)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(folder, f"render_{timestamp}.png")
    
    import matplotlib.pyplot as plt
    plt.imsave(filename, tone_map(image))
    print(f"Successfully saved: {filename}")



#main interactive loop 
def run():
    pygame.init()

    DISPLAY_W, DISPLAY_H = 800, 600
    screen = pygame.display.set_mode((DISPLAY_W, DISPLAY_H))
    pygame.display.set_caption("DH2323 — Atmospheric Scattering")

    camera  = Camera(LOW_RES_W, LOW_RES_H)
    sun_idx = 0
    sun_dir = SUN_DIRECTIONS[sun_idx]

    preset_names = ["Noon", "Sunset", "Deep Sunset", "Backlit"]
    print("Controls: Arrow keys = rotate | S = cycle sun | R = save PNG | Q = quit")

    image   = render_frame(camera, sun_dir, LOW_RES_W, LOW_RES_H)
    surface = image_to_surface(image, DISPLAY_W, DISPLAY_H)
    screen.blit(surface, (0, 0))
    pygame.display.flip()

    needs_redraw = False
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    camera.position = rotate_camera(camera.position, np.array([0.,1.,0.]), -10)
                    needs_redraw = True
                elif event.key == pygame.K_RIGHT:
                    camera.position = rotate_camera(camera.position, np.array([0.,1.,0.]),  10)
                    needs_redraw = True
                elif event.key == pygame.K_UP:
                    camera.position = rotate_camera(camera.position, np.array([1.,0.,0.]), -10)
                    needs_redraw = True
                elif event.key == pygame.K_DOWN:
                    camera.position = rotate_camera(camera.position, np.array([1.,0.,0.]),  10)
                    needs_redraw = True
                elif event.key == pygame.K_s:
                    sun_idx = (sun_idx + 1) % len(SUN_DIRECTIONS)
                    sun_dir = SUN_DIRECTIONS[sun_idx]
                    print(f"Preset {sun_idx + 1}: {preset_names[sun_idx]}")
                    needs_redraw = True
                elif event.key == pygame.K_r:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        print("Rendering high resolution to folder...")
                        hi_cam = Camera(HIGH_RES_W, HIGH_RES_H)
                        hi_cam.position = camera.position.copy()
                        high_res_img = render_frame(hi_cam, sun_dir, HIGH_RES_W, HIGH_RES_H)
                        save_png(high_res_img)
                    else:
                        print("Press Shift+R to save a high-res image to the renders folder.")
                elif event.key == pygame.K_q:
                    pygame.quit(); sys.exit()

        if needs_redraw:
            print("Rendering...")
            image   = render_frame(camera, sun_dir, LOW_RES_W, LOW_RES_H)
            surface = image_to_surface(image, DISPLAY_W, DISPLAY_H)
            screen.blit(surface, (0, 0))
            pygame.display.flip()
            needs_redraw = False

        clock.tick(30)
