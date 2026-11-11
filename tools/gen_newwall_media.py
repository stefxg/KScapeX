"""Generate the textures and the sound of the "New wall test" view (script.kscapex.wall/
resources/lib/newwallxml.py), into the wall's media folder:

  kscape-shadow.png        soft drop shadow behind the selected cover (9-slice, border 32)
  kscape-glass-border.png  thin outline of the smoked-glass info panel (9-slice, border 2)
  kscape-vignette.png      dark edges over the fanart backdrop (stretched full view)
  kscape-gloss.png         diagonal light band that glints across the selected cover
  kscape-reflect.png       alpha mask of the floor reflection (opaque at the cover, gone at 45%)
  kscape-sheen.png         wide diagonal highlight across the glass panels
  kscape-row.png           greyscale gradient for a selected row, lit from above (tinted)

White or black on transparent, so the XML tints them (colordiffuse); and, into
resources/sounds:

  kscape-whoosh.wav        soft noise sweep played when the wall rearranges (xbmc.playSFX)

Usage: python3 tools/gen_newwall_media.py   (needs Pillow)
"""
import math
import os
import random
import struct
import wave as wavemod

from PIL import Image, ImageDraw, ImageFilter

ADDON = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'script.kscapex.wall')
MEDIA = os.path.join(ADDON, 'resources', 'skins', 'Default', 'media')
SOUNDS = os.path.join(ADDON, 'resources', 'sounds')


def shadow(size=96, inset=26, blur=11, strength=190):
    """Black, opaque in the middle, fading out over the outer ~30 px."""
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).rectangle((inset, inset, size - 1 - inset, size - 1 - inset), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(blur))
    mask = mask.point(lambda a: a * strength // 255)
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    img.putalpha(mask)
    return img


def outline(size=16, width=2):
    img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
    ImageDraw.Draw(img).rectangle((0, 0, size - 1, size - 1), outline=(255, 255, 255, 255), width=width)
    return img


def vignette(w=480, h=270, start=0.52, strength=215):
    """Black, transparent in the middle, darkening towards the edges (an ellipse)."""
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            r = math.hypot((x / (w - 1) - 0.5) * 2, (y / (h - 1) - 0.5) * 2)   # 0 centre, ~1.41 corner
            a = max(0.0, min(1.0, (r - start) / (1.30 - start)))
            px[x, y] = (0, 0, 0, int(strength * a * a))
    return img


def band(w, h, peak, width, centre):
    """Soft white diagonal band (top-left to bottom-right), `width` of the diagonal wide."""
    img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
    px = img.load()
    for y in range(h):
        for x in range(w):
            d = (x / w + y / h) / 2.0 - centre      # distance along the diagonal from the band
            a = peak * math.exp(-(d / width) ** 2)
            px[x, y] = (255, 255, 255, int(a))
    return img


def gloss():
    """The glint that crosses the selected cover."""
    return band(160, 240, peak=70, width=0.16, centre=0.42)


def sheen():
    """The still highlight lying across a pane of glass: wider, and strong enough to read on a
    television from across the room (0.20.0 peaked at 20% white and was invisible there)."""
    return band(512, 256, peak=96, width=0.30, centre=0.34)


def row(h=64, top=255, bottom=166):
    """Greyscale gradient of a surface lit from above (a selected row)."""
    img = Image.new('RGBA', (4, h), (255, 255, 255, 255))
    px = img.load()
    for y in range(h):
        v = int(top + (bottom - top) * (y / (h - 1)) ** 0.9)
        for x in range(4):
            px[x, y] = (v, v, v, 255)
    return img


def reflect_mask(h=256, cut=0.45, top=150):
    """Alpha of the floor reflection: strongest against the cover, gone at `cut` of its height."""
    img = Image.new('RGBA', (4, h), (255, 255, 255, 0))
    px = img.load()
    for y in range(h):
        p = y / (h - 1)
        a = int(top * max(0.0, 1.0 - p / cut) ** 1.6)
        for x in range(4):
            px[x, y] = (255, 255, 255, a)
    return img


def whoosh(path, ms=380, rate=44100, loud=0.22):
    """Soft band-swept noise with a sine-squared envelope: the wave's sound."""
    rng = random.Random(9599)
    n = int(rate * ms / 1000)
    raw, value = [], 0.0
    for _ in range(n):                              # brownish noise (random walk, re-centred)
        value += rng.uniform(-1, 1) * 0.28
        value *= 0.985
        raw.append(value)
    out = []
    for i in range(n):
        p = i / (n - 1)
        span = max(1, int(26 * (1.0 - 0.82 * p)))    # narrowing average: pitch rises through the sweep
        lo, hi = max(0, i - span), min(n, i + span + 1)
        sample = sum(raw[lo:hi]) / (hi - lo)
        env = math.sin(math.pi * min(1.0, p * 1.12)) ** 2
        out.append(sample * env)
    top = max(abs(s) for s in out) or 1.0
    frames = b''.join(struct.pack('<h', int(32767 * loud * s / top)) for s in out)
    with wavemod.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(frames)


def main():
    for name, img in (('kscape-shadow.png', shadow()), ('kscape-glass-border.png', outline()),
                      ('kscape-vignette.png', vignette()), ('kscape-gloss.png', gloss()),
                      ('kscape-reflect.png', reflect_mask()), ('kscape-sheen.png', sheen()),
                      ('kscape-row.png', row())):
        path = os.path.join(MEDIA, name)
        img.save(path, optimize=True)
        print(f'wrote {path} {img.size}')
    os.makedirs(SOUNDS, exist_ok=True)
    path = os.path.join(SOUNDS, 'kscape-whoosh.wav')
    whoosh(path)
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
