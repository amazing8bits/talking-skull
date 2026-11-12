#!/usr/bin/env python3
"""
eyegen: procedurally generate original, lifelike eye textures for the
talking skull's GC9A01 displays.

Everything here comes from noise and geometry, so the output is original
artwork you're free to publish in the repo.

Outputs (in --out):
  iris_polar.png   - iris texture in polar form (x = angle, y = pupil edge -> limbus)
                     so the firmware can dilate the pupil without distorting the iris
  sclera.png       - sclera (eye white) texture with veins and shading
  preview_*.png    - composited 240x240 previews at several pupil sizes

Usage:
  python3 eyegen.py --color hazel --seed 7 --out out/
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PALETTES = {
    # (pupil-side inner color, outer color, dark fiber color, limbal ring color)
    "blue":  ((150, 140, 90),  (95, 140, 190),  (30, 55, 90),  (20, 35, 60)),
    "green": ((170, 130, 60),  (95, 140, 80),   (35, 60, 30),  (25, 40, 25)),
    "hazel": ((165, 105, 40),  (110, 120, 60),  (50, 40, 15),  (35, 28, 12)),
    "brown": ((120, 70, 30),   (95, 55, 25),    (40, 22, 10),  (25, 15, 8)),
    "ember": ((255, 210, 80),  (200, 40, 10),   (70, 5, 0),    (30, 0, 0)),
}


def aniso_noise(rng, h, w, sy, sx):
    """Gaussian-filtered white noise via FFT (periodic in both axes), normalized 0..1."""
    n = rng.standard_normal((h, w))
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    g = np.exp(-2 * (np.pi ** 2) * ((fy * sy) ** 2 + (fx * sx) ** 2))
    out = np.real(np.fft.ifft2(np.fft.fft2(n) * g))
    out -= out.min()
    return out / (out.max() + 1e-9)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def make_iris_polar(rng, palette, A=1024, R=128):
    inner, outer, dark, limbal = [np.array(c, float) / 255 for c in palette]
    r = np.linspace(0, 1, R)[:, None] * np.ones((1, A))

    # Radial fibers: fine detail around the circle, long along the radius.
    # Warp the angle slightly with radius so the fibers wander like real stroma.
    warp = (aniso_noise(rng, R, A, 40, 30) - 0.5) * 22

    def warped(n):
        cols = (np.arange(A)[None, :] + warp).astype(int) % A
        return np.take_along_axis(n, cols, axis=1)

    # Multi-scale fibers, contrast-stretched so individual strands stand out
    f1 = warped(aniso_noise(rng, R, A, 10, 0.9))
    f2 = warped(aniso_noise(rng, R, A, 18, 2.0))
    f3 = warped(aniso_noise(rng, R, A, 30, 5.0))
    fibers = 0.45 * f1 + 0.35 * f2 + 0.20 * f3
    fibers = smoothstep(0.30, 0.70, fibers)

    # Collarette: an irregular ring about a third of the way out, broken up by fibers
    col_r = 0.30 + (aniso_noise(rng, 1, A, 1, 18)[0] - 0.5) * 0.16
    collarette = np.exp(-((r - col_r[None, :]) / 0.05) ** 2) * (0.5 + 0.5 * f2)

    # Inner (pupillary) zone vs outer (ciliary) zone colors, soft and ragged boundary
    zone = smoothstep(col_r[None, :] - 0.06, col_r[None, :] + 0.18, r + 0.06 * (f3 - 0.5))
    base = inner[None, None, :] * (1 - zone[..., None]) + outer[None, None, :] * zone[..., None]

    # Low-frequency color drift so the iris isn't one flat hue
    drift = (aniso_noise(rng, R, A, 25, 40) - 0.5)[..., None]
    base = base * (1 + 0.35 * drift * np.array([1.0, 0.7, -0.4]))

    # Crypts: small dark pits, elongated along the radius, in the outer zone
    blobs = aniso_noise(rng, R, A, 5, 3)
    crypts = smoothstep(0.66, 0.80, blobs) * smoothstep(0.35, 0.45, r) * (1 - smoothstep(0.75, 0.88, r))

    # Broken contraction furrows (faint, only in patches)
    furrows = sum(np.exp(-((r - fr) / 0.015) ** 2) for fr in (0.66, 0.80))
    furrows *= smoothstep(0.55, 0.8, aniso_noise(rng, R, A, 4, 30))

    # Brightness: fibers + collarette, darkened by crypts/furrows/edges
    light = 0.50 + 0.55 * (fibers - 0.5) + 0.25 * collarette
    light -= 0.35 * crypts + 0.25 * furrows
    light *= 0.45 + 0.55 * smoothstep(0.0, 0.10, r)   # dark pupil margin
    light = np.clip(light, 0, 1.3)

    rgb = dark[None, None, :] + (base - dark[None, None, :]) * light[..., None]
    # Pupillary ruff: a thin dark brown fringe right at the pupil edge
    ruff = np.exp(-(r / 0.025) ** 2)[..., None]
    rgb = rgb * (1 - 0.7 * ruff) + np.array([0.12, 0.07, 0.04]) * 0.7 * ruff

    # Limbal ring: a dark soft edge where the iris meets the sclera
    limb = smoothstep(0.82, 1.0, r)[..., None]
    rgb = rgb * (1 - 0.85 * limb) + limbal[None, None, :] * 0.85 * limb
    return np.clip(rgb, 0, 1)


def make_sclera(rng, size=240, iris_r=70):
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    cx = cy = (size - 1) / 2
    d = np.hypot(xx - cx, yy - cy) / (size / 2)

    base = np.array([0.93, 0.90, 0.86])
    pink = np.array([0.88, 0.62, 0.58])
    tint = smoothstep(0.55, 1.05, d)[..., None]
    mottle = (aniso_noise(rng, size, size, 8, 8) - 0.5)[..., None] * 0.06
    rgb = base * (1 - 0.5 * tint) + pink * 0.5 * tint + mottle

    # Veins: branching random walks from the edge toward the iris
    veins = Image.new("L", (size, size), 0)
    dr = ImageDraw.Draw(veins)

    def walk(x, y, ang, width, length, depth):
        for _ in range(length):
            nx = x + np.cos(ang) * 2.0
            ny = y + np.sin(ang) * 2.0
            dist = np.hypot(nx - cx, ny - cy)
            if dist < iris_r + 4:
                return
            dr.line([(x, y), (nx, ny)], fill=int(255 * min(1, width / 2.2)), width=max(1, int(round(width))))
            x, y = nx, ny
            ang += rng.normal(0, 0.25)
            width *= 0.985
            if depth < 3 and rng.random() < 0.04:
                walk(x, y, ang + rng.choice([-1, 1]) * rng.uniform(0.4, 0.9), width * 0.7, length // 2, depth + 1)

    for _ in range(rng.integers(7, 11)):
        a = rng.uniform(0, 2 * np.pi)
        r0 = size / 2 * 1.02
        x, y = cx + np.cos(a) * r0, cy + np.sin(a) * r0
        walk(x, y, a + np.pi + rng.normal(0, 0.35), rng.uniform(1.2, 2.4), 40, 0)

    v = np.asarray(veins.filter(ImageFilter.GaussianBlur(0.8)), float)[..., None] / 255
    vein_col = np.array([0.70, 0.18, 0.16])
    rgb = rgb * (1 - 0.55 * v) + vein_col * 0.55 * v

    # Spherical shading: darker toward the edges, as if wrapping around a ball
    rgb *= (1 - 0.35 * smoothstep(0.6, 1.1, d))[..., None]
    return np.clip(rgb, 0, 1)


def composite(iris_polar, sclera, pupil_frac, size=240, iris_r=70, highlight=True):
    R, A, _ = iris_polar.shape
    yy, xx = np.mgrid[0:size, 0:size].astype(float)
    cx = cy = (size - 1) / 2
    dx, dy = xx - cx, yy - cy
    d = np.hypot(dx, dy)
    ang = (np.arctan2(dy, dx) % (2 * np.pi)) / (2 * np.pi)

    pupil_r = iris_r * pupil_frac
    rr = np.clip((d - pupil_r) / (iris_r - pupil_r), 0, 1)
    iy = np.clip((rr * (R - 1)).astype(int), 0, R - 1)
    ix = np.clip((ang * A).astype(int), 0, A - 1)
    iris = iris_polar[iy, ix]

    out = sclera.copy()
    m_iris = smoothstep(iris_r + 1.0, iris_r - 1.0, d)[..., None]
    out = out * (1 - m_iris) + iris * m_iris

    # Pupil, with a soft edge and a slight dark bluish tint
    m_pupil = smoothstep(pupil_r + 1.2, pupil_r - 1.2, d)[..., None]
    out = out * (1 - m_pupil) + np.array([0.02, 0.02, 0.03]) * m_pupil

    # Shadow from the upper lid on the top of the iris and sclera
    shadow = smoothstep(-0.2 * size, -0.5 * size, dy)[..., None]
    out *= 1 - 0.25 * shadow

    if highlight:
        # Corneal reflections: one soft window glint and a small sharp dot
        g1 = np.exp(-(((dx + 22) / 11) ** 2 + ((dy + 24) / 8) ** 2))
        g2 = np.exp(-(((dx - 14) / 3.2) ** 2 + ((dy - 16) / 3.2) ** 2))
        glint = np.clip(0.85 * g1 + 0.6 * g2, 0, 1)[..., None]
        out = out * (1 - glint) + glint

    # Round GC9A01 mask
    out *= smoothstep(size / 2 + 0.5, size / 2 - 1.5, d)[..., None]
    return np.clip(out, 0, 1)


def to_img(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--color", choices=PALETTES, default="hazel")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--size", type=int, default=240)
    p.add_argument("--iris-radius", type=int, default=70)
    p.add_argument("--out", default="out")
    a = p.parse_args()

    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    iris = make_iris_polar(rng, PALETTES[a.color])
    sclera = make_sclera(rng, a.size, a.iris_radius)

    to_img(iris).save(os.path.join(a.out, "iris_polar.png"))
    to_img(sclera).save(os.path.join(a.out, "sclera.png"))
    for name, pf in (("small", 0.28), ("normal", 0.40), ("dilated", 0.58)):
        to_img(composite(iris, sclera, pf, a.size, a.iris_radius)).save(
            os.path.join(a.out, f"preview_{name}.png"))
    print(f"wrote textures and previews to {a.out}/")


if __name__ == "__main__":
    main()
