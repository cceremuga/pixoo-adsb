from PIL import Image

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


def main():
    cfg = load()
    logos = LogoManager(cfg)

    total_w = len(SCENARIOS) * W * SCALE + (len(SCENARIOS) - 1) * GAP + 2 * BORDER
    total_h = H * SCALE + 2 * BORDER
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
        canvas.paste(
            img.resize((W * SCALE, H * SCALE), Image.NEAREST),
            (BORDER + i * (W * SCALE + GAP), BORDER),
        )

    canvas.save("sample.png")
    print(f"sample.png written ({canvas.width}x{canvas.height})")


if __name__ == "__main__":
    main()
