"""Generate script.kscapex.wall's cover wall XML for a 16:9 screen, once per cover layout:
script-kscape-wall.xml (2:3 posters: movies, TV shows) and script-kscape-wall-square.xml
(album covers). The builder is the add-on's (resources/lib/wallxml.py), which also builds the
wall for other screen shapes and CinemaScope bands at run time.

KScapeX: also script-kscape-newwall.xml, the "New wall test" view of posters
(resources/lib/newwallxml.py), and script-kscape-info-new.xml, its cinema fiche, transformed
from the hand-written script-kscape-info.xml (resources/lib/newinfoxml.py).

Usage: python3 tools/gen_wall_xml.py
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'script.kscapex.wall')
sys.path.insert(0, ROOT)
from resources.lib import geometry as G  # noqa: E402
from resources.lib import newinfoxml, newwallxml, wallxml  # noqa: E402


def main():
    folder = os.path.join(ROOT, 'resources', 'skins', 'Default', '1080i')
    for L, name in ((G.POSTER, 'script-kscape-wall.xml'), (G.SQUARE, 'script-kscape-wall-square.xml')):
        out = os.path.join(folder, name)
        with open(out, 'w') as f:
            f.write(wallxml.build(L))
        print(f'wrote {out} ({L.pool_cols * L.pool_rows} slots per pool)')
    out = os.path.join(folder, 'script-kscape-newwall.xml')
    with open(out, 'w') as f:
        f.write(newwallxml.build(G.POSTER))
    print(f'wrote {out} (New wall test)')
    with open(os.path.join(folder, 'script-kscape-info.xml')) as f:
        classic = f.read()
    out = os.path.join(folder, newinfoxml.NAME)
    with open(out, 'w') as f:
        f.write(newinfoxml.transform(classic))
    print(f'wrote {out} (New wall test fiche)')


if __name__ == '__main__':
    main()
