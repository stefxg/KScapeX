"""Unit tests for KScapeX's "New wall test" view (newwallxml.py, newwall.py), and that the classic
wall's XML stays as it was. Run: python3 -m unittest discover -s tests"""
import os
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from resources.lib import display as D  # noqa: E402
from resources.lib import geometry as G  # noqa: E402
from resources.lib import newwallxml as NX  # noqa: E402
from resources.lib import wallxml  # noqa: E402
from resources.lib.wallmodel import Wall, wave_delay  # noqa: E402

# newwall.py needs Kodi's modules; import it against mocks, then put sys.modules back as it was.
with mock.patch.dict(sys.modules, {n: mock.MagicMock() for n in ('xbmc', 'xbmcaddon', 'xbmcgui', 'xbmcvfs')}):
    from resources.lib import newwall as NW  # noqa: E402

SKIN = os.path.join(os.path.dirname(__file__), '..', 'resources', 'skins', 'Default', '1080i')


def shipped(name):
    with open(os.path.join(SKIN, name), encoding='utf-8') as f:
        return f.read()


def ids(xml):
    return {c.get('id') for c in ET.fromstring(xml).iter('control') if c.get('id')}


def items(n):
    return [types.SimpleNamespace(key=i) for i in range(1, n + 1)]


class ShippedXmlTest(unittest.TestCase):
    def test_classic_walls_are_unchanged_by_the_new_one(self):
        # The shipped classic XML is what wallxml builds (gen_wall_xml.py), slot badges and all.
        self.assertEqual(wallxml.build(G.POSTER), shipped('script-kscape-wall.xml'))
        self.assertEqual(wallxml.build(G.SQUARE), shipped('script-kscape-wall-square.xml'))
        self.assertIn('Property(badge)', wallxml.slot(10000, G.POSTER))

    def test_new_wall_is_generated(self):
        self.assertEqual(NX.build(G.POSTER), shipped('script-kscape-newwall.xml'))


class NewWallXmlTest(unittest.TestCase):
    def setUp(self):
        self.xml = NX.build(G.POSTER)

    def test_controls_python_needs(self):
        # Every control WallWindow looks up, and the new ones.
        need = {'900', '998', '1000', '1001', '1006', '1007', '1900', '1901', '1902', '1905', '1909',
                '1911', '1912', '1914', '1950', '1951', '1960', '1961', '1962', '1963', '1965', '1980',
                '1971', '1972', '1973', '1974', '1990', '1991',
                '1008', '1010', '1906', '1966', str(NX.SPOT_SRC)}
        slots = {str(b + k) for b in (10000, 20000) for k in range(G.POSTER.pool_cols * G.POSTER.pool_rows)}
        self.assertLessEqual(need | slots, ids(self.xml))

    def test_slots_carry_no_badge(self):
        slot = wallxml.slot(10000, G.POSTER, badge=False)
        self.assertNotIn('Property(badge)', slot)
        spot = f'Container({NX.SPOT_SRC}).ListItemAbsolute(0).Property(badge)'
        self.assertEqual(self.xml.count('Property(badge)'), self.xml.count(spot))   # the spotlight's own
        count = lambda xml: len(list(ET.fromstring(xml).iter('control')))
        self.assertLess(count(self.xml), count(wallxml.build(G.POSTER)))     # lighter every frame

    def test_panel_leaves_room_for_the_zoomed_frame(self):
        frame_w = G.POSTER.cover_w + 2 * G.fx(G.POSTER)
        growth = frame_w * (NX.SPOT_ZOOM - 100) / 200.0
        self.assertGreaterEqual(NX.SPOT_GAP, growth)
        self.assertEqual(NX.panel_width(G.POSTER), G.panel_w(G.POSTER) - NX.SPOT_GAP)
        panel = next(c for c in ET.fromstring(self.xml).iter('control') if c.get('id') == '1900')
        self.assertEqual(int(panel.find('width').text), NX.panel_width(G.POSTER))

    def test_title_hides_while_there_is_a_logo(self):
        title = next(c for c in ET.fromstring(self.xml).iter('control') if c.get('id') == '1901')
        self.assertEqual(title.find('visible').text,
                         f'String.IsEmpty(Container({NX.SPOT_SRC}).ListItemAbsolute(0).Property(logo))')

    def test_dimmer_covers_the_view_wherever_the_frame_is(self):
        left, top, w, h = NX.DIM_BOX
        for fx_, fy in ((0, 0), (G.SCREEN_W - 230, 0), (0, G.SCREEN_H - 323), (G.SCREEN_W, G.SCREEN_H)):
            self.assertLessEqual(fx_ + left, 0)
            self.assertLessEqual(fy + top, 0)
            self.assertGreaterEqual(fx_ + left + w, G.SCREEN_W)
            self.assertGreaterEqual(fy + top + h, G.SCREEN_H)

    def test_adapted_layouts_build(self):
        for stage in (D.stage(2560, 1080), D.stage(1920, 1080, '2.40', rows='3')):
            lay = G.adapt(G.POSTER, stage)
            xml = NX.build(lay, stage.sx)
            self.assertIn('1992', ids(xml))
            self.assertEqual(wallxml.SX, 1.0)                    # restored after the build


class WaveTest(unittest.TestCase):
    def test_delay_grows_with_distance_from_the_selected_cover(self):
        L = G.POSTER
        self.assertEqual(wave_delay((5, 2), (5, 2), L, 50), 0)
        self.assertEqual(wave_delay((6, 2), (5, 2), L, 50), 50)
        self.assertEqual(wave_delay((4, 2), (5, 2), L, 50), 50)
        up = wave_delay((5, 1), (5, 2), L, 50)
        self.assertEqual(up, round(L.pitch_y / L.pitch_x * 50))     # rows are taller than columns are wide
        self.assertLess(wave_delay((6, 3), (5, 2), L, 50), wave_delay((7, 3), (5, 2), L, 50))

    def test_only_changed_covers_on_screen_turn(self):
        library = items(40)
        old = Wall.row_major(library, rows=4)
        moved = list(library)
        moved[1], moved[2] = moved[2], moved[1]                 # two covers swap cells
        new = Wall.row_major(moved, rows=4)
        cells = [(k, (k % old.cols, k // old.cols)) for k in range(40)]
        plan = NW.wave_plan(old, new, cells, lambda cell: True, (0, 0), G.POSTER)
        self.assertEqual(sorted(cell for _, cell, _ in plan), sorted([new.cell_of(2), new.cell_of(3)]))
        hidden = NW.wave_plan(old, new, cells, lambda cell: cell != new.cell_of(2), (0, 0), G.POSTER)
        self.assertEqual([cell for _, cell, _ in hidden], [new.cell_of(3)])

    def test_turns_follow_each_other(self):
        out_, = NW.turn_out(120, 'C')
        in_, = NW.turn_in(120, 'C')
        f_out = dict(f.split('=', 1) for f in out_[1].split(' '))
        f_in = dict(f.split('=', 1) for f in in_[1].split(' '))
        self.assertEqual((f_out['start'], f_out['end']), ('100,100', '0,100'))
        self.assertEqual((f_in['start'], f_in['end']), ('0,100', '100,100'))
        self.assertEqual(int(f_in['delay']), int(f_out['delay']) + int(f_out['time']))
        self.assertEqual(f_in['condition'], 'C')


class ClearLogoTest(unittest.TestCase):
    def test_logo_of_movie_set_and_show(self):
        kinds = {n: types.SimpleNamespace(name=n) for n in ('movies', 'tv', 'music')}
        answers = {
            'VideoLibrary.GetMovieDetails': {'moviedetails': {'art': {'clearlogo': 'image://m/'}}},
            'VideoLibrary.GetMovieSetDetails': {'setdetails': {'art': {}}},
            'VideoLibrary.GetTVShowDetails': {'tvshowdetails': {'art': {'clearlogo': 'image://t/'}}},
        }
        with mock.patch.object(NW, 'rpc', side_effect=lambda method, params: answers[method]):
            self.assertEqual(NW.clearlogo(kinds['movies'], types.SimpleNamespace(movieid=4, key=4)), 'image://m/')
            self.assertEqual(NW.clearlogo(kinds['movies'], types.SimpleNamespace(movieid=-2, key=-2)), '')
            self.assertEqual(NW.clearlogo(kinds['tv'], types.SimpleNamespace(tvshowid=9, key=9)), 'image://t/')
            self.assertEqual(NW.clearlogo(kinds['music'], types.SimpleNamespace(key=1)), '')


if __name__ == '__main__':
    unittest.main()
