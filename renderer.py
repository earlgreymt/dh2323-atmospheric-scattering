import numpy as np
import pygame
import sys
from camera import Camera
from atmosphere import compute_pixel_colour, ray_sphere_intersect, PLANET_RADIUS
from planet import shade_planet

# ── WINDOW SETTINGS ───────────────────────────────────────────────
LOW_RES_W  = 200    # interactive mode resolution
LOW_RES_H  = 150
HIGH_RES_W = 800    # high quality save resolution
HIGH_RES_H = 600

# ── SUN DIRECTIONS ────────────────────────────────────────────────
# cycle through these with S key
SUN_DIRECTIONS = [
    np.array([0.5,  0.3,  1.0]),   # noon — blue sky
    np.array([1.5,  0.0,  0.3]),   # sunset — orange red
    np.array([2.0,  -0.1, 0.1]),   # deep sunset — very red
    np.array([0.0,  0.8,  1.0]),   # high sun — bright blue
]

def normalise(v):
    return v / np.linalg.norm(v)


# ── ROTATE CAMERA AROUND PLANET ───────────────────────────────────
def rotate_camera(position, axis, angle_deg):
    """
    Rotate the camera position around the planet (origin)
    by angle_deg degrees around the given axis.
    Uses Rodrigues rotation formula.
    """
    angle = np.radians(angle_deg)
    axis  = normalise(axis)
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)

    rotated = (position * cos_a
               + np.cross(axis, position) * sin_a
               + axis * np.dot(axis, position) * (1 - cos_a))
    return rotated


# ── RENDER ONE FRAME ──────────────────────────────────────────────
def render_frame(camera, sun_dir, width, height):
    image  = np.zeros((height, width, 3))
    # normalise sun direction once here for the whole frame
    sun_n  = sun_dir / np.linalg.norm(sun_dir)

    for py in range(height):
        for px in range(width):
            rd = camera.get_ray_direction(px, py)
            ro = camera.position

            planet_colour = shade_planet(ro, rd, sun_n)
            atmo_colour   = compute_pixel_colour(ro, rd, sun_n)

            if planet_colour is not None:
                atmo_blend = np.clip(atmo_colour * 2.0, 0, 1)
                colour = planet_colour * (1.0 - atmo_blend * 0.4) + atmo_colour
            else:
                colour = atmo_colour

            image[py, px] = colour

    return image


# ── TONE MAP AND CLAMP ────────────────────────────────────────────
def tone_map(image):
    """
    Convert raw linear light values to displayable range.
    Simple reinhard tone mapping then gamma correction.
    """
    # reinhard tone mapping — compresses bright values
    image = image / (image + 1.0)

    # gamma correction — makes colours look correct on screen
    image = np.power(np.clip(image, 0, 1), 1.0 / 2.2)

    return image


# ── NUMPY IMAGE TO PYGAME SURFACE ────────────────────────────────
def image_to_surface(image, display_w, display_h):
    """
    Convert a numpy float image (0-1) to a pygame surface
    scaled up to the display window size.
    """
    # convert 0-1 floats to 0-255 integers
    img_uint8 = (tone_map(image) * 255).astype(np.uint8)

    # pygame needs (width, height, 3) but numpy is (height, width, 3)
    img_transposed = np.transpose(img_uint8, (1, 0, 2))

    surface = pygame.surfarray.make_surface(img_transposed)

    # scale up to window size for display
    surface = pygame.transform.scale(surface, (display_w, display_h))

    return surface


# ── SAVE HIGH RES PNG ─────────────────────────────────────────────
def save_png(image, filename="render.png"):
    import matplotlib.pyplot as plt
    mapped = tone_map(image)
    plt.imsave(filename, mapped)
    print(f"Saved {filename}")


# ── MAIN INTERACTIVE LOOP ─────────────────────────────────────────
def run():
    pygame.init()

    # display window is always shown at full size
    DISPLAY_W = 800
    DISPLAY_H = 600
    screen = pygame.display.set_mode((DISPLAY_W, DISPLAY_H))
    pygame.display.set_caption("DH2323 — Atmospheric Scattering")

    # start in low res for fast interaction
    camera   = Camera(LOW_RES_W, LOW_RES_H)
    sun_idx  = 0
    sun_dir  = SUN_DIRECTIONS[sun_idx]

    print("Rendering... please wait")
    print("Controls: Arrow keys = rotate | S = change sun | R = save PNG | Q = quit")

    # render first frame
    image   = render_frame(camera, sun_dir, LOW_RES_W, LOW_RES_H)
    surface = image_to_surface(image, DISPLAY_W, DISPLAY_H)
    screen.blit(surface, (0, 0))
    pygame.display.flip()

    needs_redraw = False
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                # ── arrow keys — rotate camera ──
                if event.key == pygame.K_LEFT:
                    camera.position = rotate_camera(
                        camera.position, np.array([0.0, 1.0, 0.0]), -10)
                    needs_redraw = True

                elif event.key == pygame.K_RIGHT:
                    camera.position = rotate_camera(
                        camera.position, np.array([0.0, 1.0, 0.0]), 10)
                    needs_redraw = True

                elif event.key == pygame.K_UP:
                    camera.position = rotate_camera(
                        camera.position, np.array([1.0, 0.0, 0.0]), -10)
                    needs_redraw = True

                elif event.key == pygame.K_DOWN:
                    camera.position = rotate_camera(
                        camera.position, np.array([1.0, 0.0, 0.0]), 10)
                    needs_redraw = True

                # ── S key — cycle sun direction ──
                elif event.key == pygame.K_s:
                    sun_idx = (sun_idx + 1) % len(SUN_DIRECTIONS)
                    sun_dir = SUN_DIRECTIONS[sun_idx]
                    print(f"Sun direction changed to preset {sun_idx + 1}")
                    needs_redraw = True

                # ── R key — save high res PNG ──
                elif event.key == pygame.K_r:
                    print("Rendering high resolution image...")
                    hi_cam   = Camera(HIGH_RES_W, HIGH_RES_H)
                    hi_cam.position = camera.position.copy()
                    hi_image = render_frame(
                        hi_cam, sun_dir, HIGH_RES_W, HIGH_RES_H)
                    save_png(hi_image, "render.png")

                # ── Q key — quit ──
                elif event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()

        # redraw if camera or sun changed
        if needs_redraw:
            print("Rendering...")
            image   = render_frame(
                camera, sun_dir, LOW_RES_W, LOW_RES_H)
            surface = image_to_surface(image, DISPLAY_W, DISPLAY_H)
            screen.blit(surface, (0, 0))
            pygame.display.flip()
            needs_redraw = False

        clock.tick(30)