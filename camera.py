import numpy as np

class Camera:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.fov = 60.0

        # camera always looks at the origin (planet centre)
        # position orbits around it
        self.position = np.array([0.0, 0.0, 2.5])

    def get_ray_direction(self, px, py):
        """
        Compute ray direction for pixel (px, py).
        Camera always looks towards the origin.
        """
        fov_rad = np.radians(self.fov)
        aspect  = self.width / self.height

        ndc_x = (px + 0.5) / self.width
        ndc_y = (py + 0.5) / self.height

        screen_x = (2.0 * ndc_x - 1.0) * aspect * np.tan(fov_rad / 2.0)
        screen_y = (1.0 - 2.0 * ndc_y) * np.tan(fov_rad / 2.0)

        # compute camera basis vectors so it always looks at origin
        forward = -self.position / np.linalg.norm(self.position)
        world_up = np.array([0.0, 1.0, 0.0])

        # handle edge case when camera is directly above/below
        if abs(np.dot(forward, world_up)) > 0.99:
            world_up = np.array([0.0, 0.0, 1.0])

        right = np.cross(forward, world_up)
        right = right / np.linalg.norm(right)

        up = np.cross(right, forward)
        up = up / np.linalg.norm(up)

        # ray direction in world space
        direction = forward + right * screen_x + up * screen_y
        direction = direction / np.linalg.norm(direction)

        return direction