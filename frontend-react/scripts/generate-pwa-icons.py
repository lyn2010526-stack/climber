#!/usr/bin/env python3
"""Generate PWA icons from Climber brand colors."""

import os
from PIL import Image, ImageDraw

OUTPUT_DIR = "/workspace/agent-engine/frontend-react/public"
BRAND_BG = (0x86, 0x3B, 0xFF)  # #863BFF
BRAND_ACCENT = (0x5E, 0x6A, 0xD2)  # #5E6AD2
WHITE = (255, 255, 255)

SIZES = [
    72,
    96,
    128,
    144,
    152,
    168,
    180,
    192,
    256,
    384,
    512,
]


def draw_star(draw: ImageDraw.Draw, cx: int, cy: int, size: int, color: tuple):
    points = [
        (cx, cy - size),
        (cx + size * 0.2245, cy - size * 0.3090),
        (cx + size * 0.9511, cy - size * 0.3090),
        (cx + size * 0.3633, cy + size * 0.1180),
        (cx + size * 0.5878, cy + size * 0.8090),
        (cx, cy + size * 0.3819),
        (cx - size * 0.5878, cy + size * 0.8090),
        (cx - size * 0.3633, cy + size * 0.1180),
        (cx - size * 0.9511, cy - size * 0.3090),
        (cx - size * 0.2245, cy - size * 0.3090),
    ]
    draw.polygon(points, fill=color)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    padding = int(size * 0.12)
    radius = (size // 2 - padding) * 2 // 3
    cx = size // 2
    cy = size // 2
    r = size // 2 - padding

    draw.rounded_rectangle(
        [padding, padding, size - padding, size - padding],
        radius=radius,
        fill=BRAND_BG,
    )

    glow_radius = int(size * 0.28)
    for i in range(3):
        alpha = 60 - i * 15
        glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gdraw.ellipse(
            [
                cx - glow_radius + i * 4,
                cy - glow_radius + i * 4,
                cx + glow_radius - i * 4,
                cy + glow_radius - i * 4,
            ],
            fill=(94, 106, 210, alpha),
        )
        img = Image.alpha_composite(img, glow)
        draw = ImageDraw.Draw(img)

    star_size = int(size * 0.22)
    draw_star(draw, cx, cy, star_size, WHITE)

    return img


def generate():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for s in SIZES:
        icon = draw_icon(s)
        path = os.path.join(OUTPUT_DIR, f"icon-{s}x{s}.png")
        icon.save(path, "PNG")
        print(f"Generated {path}")


if __name__ == "__main__":
    generate()
