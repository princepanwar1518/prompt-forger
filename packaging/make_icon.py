"""Generates the app icon (icon.png + multi-size icon.ico) so the repo needs no binary design files."""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent
SIZE = 512


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size * 0.22
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=(23, 26, 33, 255))
    c, s = size / 2, size * 0.30
    diamond = [(c, c - s), (c + s, c), (c, c + s), (c - s, c)]
    d.polygon(diamond, fill=(255, 122, 51, 255))
    inner = size * 0.12
    d.polygon([(c, c - inner), (c + inner, c), (c, c + inner), (c - inner, c)], fill=(23, 26, 33, 255))
    return img


if __name__ == "__main__":
    big = draw(SIZE)
    big.save(OUT / "icon.png")
    big.save(OUT / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    draw(64).save(OUT.parent / "app/src/main/resources/com/panwarstudio/promptforger/icon.png")
    print("icons written")
