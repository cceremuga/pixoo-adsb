from PIL import Image, ImageDraw

from aircraft import Aircraft
from config import load
from logo_manager import LogoManager
from renderer import compose

SCENARIOS = [
    ("SWA1234", "N8731Q", 35000, 450, "BOS", "LAX", 19),
    ("DAL447", "N392DA", 17500, 310, "JFK", "ATL", 8),
    ("N172SP", "N172SP", 4500, 120, "???", "???", 31),
]

SCALE = 6
BORDER = 8
GAP = 12
W = H = 64
SW = SH = W * SCALE

_PIXEL_BORDER = (0x22, 0x22, 0x22)
_grid_mask = Image.new("L", (SW, SH), 255)
_gd = ImageDraw.Draw(_grid_mask)
for _i in range(0, SW, SCALE):
    _gd.line([(_i, 0), (_i, SH - 1)], fill=0)
for _j in range(0, SH, SCALE):
    _gd.line([(0, _j), (SW - 1, _j)], fill=0)
del _gd, _i, _j
_grid_bg = Image.new("RGB", (SW, SH), _PIXEL_BORDER)


def _apply_pixel_grid(frame: Image.Image) -> Image.Image:
    upscaled = frame.resize((SW, SH), Image.NEAREST)
    return Image.composite(upscaled, _grid_bg, _grid_mask)


def main():
    cfg = load()
    logos = LogoManager(cfg)

    total_w = len(SCENARIOS) * SW + (len(SCENARIOS) - 1) * GAP + 2 * BORDER
    total_h = SH + 2 * BORDER
    canvas = Image.new("RGB", (total_w, total_h), (18, 18, 18))

    for i, (flight, reg, alt, spd, orig, dest, dist_km) in enumerate(SCENARIOS):
        ac = Aircraft.from_dump1090(
            {
                "hex": "aabbcc",
                "flight": flight,
                "r": reg,
                "lat": 42.6,
                "lon": -73.8,
                "alt_baro": alt,
                "gs": spd,
                "seen_pos": 2,
            }
        )
        ac.distance_km = dist_km
        img = compose(ac, logos.get(flight), orig, dest, cfg.display)
        canvas.paste(_apply_pixel_grid(img), (BORDER + i * (SW + GAP), BORDER))

    canvas.save("sample.png")
    print(f"sample.png written ({canvas.width}x{canvas.height})")


if __name__ == "__main__":
    main()
