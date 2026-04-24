# DH2323 — Atmospheric Scattering: Interactive Planet Renderer

**Course:** DH2323 Computer Graphics and Interaction, KTH Royal Institute of Technology  
**Group:** Ma Jinlin and Rajadharshini Nedumaran  
**Target grade:** B  
**Date:** May 2026  

---

## About This Project

We are implementing a CPU-based atmospheric scattering renderer in Python
that simulates how sunlight interacts with a planetary atmosphere as seen
from space. The visual output is a planet with a physically-based glowing
atmospheric halo — colours ranging from blue at noon to orange-red at the
day-night boundary — based on the SIGGRAPH paper by Nishita et al. (1993).

**Core CG techniques:** Ray casting, ray-sphere intersection, ray marching,
Rayleigh scattering, scalar field visualisation  
**Tools:** Python 3, numpy, pygame  
**Key reference:** Nishita, T. et al. (1993). SIGGRAPH.  

---

## Blog Posts

### Post 1 — Project Specification (May 2026)

**What we are building:**  
An interactive planet renderer that simulates atmospheric scattering from
space. The user rotates a virtual camera around the planet using arrow keys
and observes how the atmosphere glows blue on the lit side and fades to
orange-red at the day-night boundary. A keypress triggers a high-resolution
render saved as a PNG file.

**Why atmospheric scattering:**  
This phenomenon explains why the sky is blue, why sunsets are orange, and
why planets have a glowing halo when seen from space. It is modelled
physically using Rayleigh scattering — shorter wavelengths like blue scatter
more than longer wavelengths like red, proportional to 1/wavelength^4.
The Nishita et al. 1993 SIGGRAPH paper is our primary reference.

**Core techniques we are implementing:**
- Ray casting — ray direction per pixel from virtual camera
- Ray-sphere intersection — where rays hit the planet and atmosphere
- Ray marching — stepping along each ray to accumulate scattered light
- Rayleigh scattering — wavelength-based RGB colour computation
- Optional: Mie scattering for haze and sun glow

**Work split:**  
Ma Jinlin — core rendering pipeline (ray marching, intersections, camera,
pygame window)  
Rajadharshini Nedumaran — scattering coefficients, planet surface shading,
Mie scattering extension, report writing lead  

**Timeline:**  
- Week 1 (May 1-7): Setup, ray infrastructure, specification submission  
- Week 2 (May 8-14): Ray marching, scattering, interactive window  
- Week 3 (May 15-18): Extensions, demo video, report, submission  

**References:**  
Nishita, T. et al. (1993). Display of the Earth taking into account
atmospheric scattering. SIGGRAPH 1993.  
Preetham, A. J. et al. (1999). A practical analytic model for daylight.
SIGGRAPH 1999.  
Bruneton, E. and Neyret, F. (2008). Precomputed atmospheric scattering.
Computer Graphics Forum, 27(4).  

---

*Progress updates, screenshots and code notes will be posted here
as the project develops. Check back weekly.*
