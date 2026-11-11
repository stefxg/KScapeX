"""Generate the two textures of the "New wall test" view (script.kscapex.wall/resources/lib/
newwallxml.py), into the wall's media folder:

  kscape-shadow.png        soft drop shadow behind the selected cover (9-slice, border 32)
  kscape-glass-border.png  thin outline of the smoked-glass info panel (9-slice, border 2)

Both are white or black on transparent, so the XML tints them (colordiffuse).

Usage: python3 tools/gen_newwall_media.py   (needs Pillow)
"""
import os

from PIL import Image, ImageDraw, ImageFilter

MEDIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'script.kscapex.wall',
                     'resources', 'skins', 'Default', 'media')


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


def main():
    for name, img in (('kscape-shadow.png', shadow()), ('kscape-glass-border.png', outline())):
        path = os.path.join(MEDIA, name)
        img.save(path, optimize=True)
        print(f'wrote {path} {img.size}')


if __name__ == '__main__':
    main()
