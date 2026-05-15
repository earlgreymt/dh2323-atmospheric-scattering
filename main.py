import os

from renderer import run
import renderer

if __name__ == "__main__":
    print("--- DEBUG INFO ---")
    print(f"I am loading render.py from: {os.path.abspath(renderer.__file__)}")
    print("------------------")
    print("=" * 50)
    print("DH2323 — Atmospheric Scattering Planet Renderer")
    print("Ma Jinlin and Rajadharshini Nedumaran")
    print("KTH Royal Institute of Technology, 2026")
    print("=" * 50)
    print()
    print("Controls:")
    print("  Arrow keys — rotate camera around planet")
    print("  S          — cycle sun direction")
    print("  R          — save high resolution PNG")
    print("  Q          — quit")
    print()
    run()