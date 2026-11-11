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
from resources.lib import newinfoxml as NX2  # noqa: E402
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
        self.assertNotIn('WindowOpen', wallxml.build(G.POSTER))     # the cascade is the new wall's

    def test_new_wall_is_generated(self):
        self.assertEqual(NX.build(G.POSTER), shipped('script-kscape-newwall.xml'))

    def test_cinema_fiche_is_transformed_from_the_untouched_classic_one(self):
        classic = shipped('script-kscape-info.xml')
        self.assertIn('Hand-written', classic)                   # the classic fiche is untouched
        self.assertNotIn('GENERATED', classic)
        new = NX2.transform(classic)
        self.assertEqual(new, shipped(NX2.NAME))
        self.assertLessEqual({'100', '151', '153', '221', '310', '410', '510', '610', '710'}, ids(new))
        self.assertEqual(ids(new), ids(classic))                 # same controls: details.py drives both
        self.assertIn('Window.Property(fanart)', new)
        self.assertIn('Window.Property(clearlogo)', new)
        self.assertNotIn('effect="slide" start="0,1032"', new)   # fade + bloom, no slide from the bottom
        self.assertIn('effect="zoom" start="97"', new)
        self.assertIn('kscape-sheen.png', new)                   # polished glass, selected rows lit
        self.assertEqual(new.count('kscape-row.png'), 8)
        self.assertNotIn('kscape-sheen.png', classic)            # none of it in the classic fiche
        self.assertNotIn('kscape-row.png', classic)
        ET.fromstring(new)

    def test_transform_refuses_a_changed_classic_fiche(self):
        with self.assertRaises(ValueError):
            NX2.transform('<window/>')


class NewWallXmlTest(unittest.TestCase):
    def setUp(self):
        self.xml = NX.build(G.POSTER)

    def test_controls_python_needs(self):
        # Every control WallWindow looks up, and the new ones.
        need = {'900', '998', '1000', '1001', '1006', '1007', '1900', '1901', '1902', '1905', '1909',
                '1911', '1912', '1914', '1950', '1951', '1960', '1961', '1962', '1963', '1965', '1980',
                '1971', '1972', '1973', '1974', '1990', '1991',
                '1009', '1010', '1906', '1966', str(NX.SPOT_SRC)}
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

    def test_backdrop_fills_the_view_with_fanart_veil_and_vignette(self):
        back = next(c for c in ET.fromstring(self.xml).iter('control') if c.get('id') == '1009')
        images = list(back.iter('control'))[1:]
        self.assertEqual([i.find('texture').text for i in images],
                         [f'$INFO[Container({NX.SPOT_SRC}).ListItemAbsolute(0).Property(fanart)]',
                          'kscape-white.png', 'kscape-vignette.png'])
        for i in images:
            self.assertEqual(int(i.find('width').text), G.SCREEN_W)
            self.assertEqual(int(i.find('height').text), G.SCREEN_H)
        self.assertIn('kscape.spot', back.find('visible').text)

    def test_spotlight_carries_reflection_glint_and_polish(self):
        self.assertIn('kscape-reflect.png', self.xml)
        self.assertIn('flipy="true"', self.xml)

    def test_the_amber_carries_no_gloss(self):
        # 0.20.0 gave the frame's bars a gradient and the badge a sheen: streaky on screen, so
        # every amber part is flat again, as the classic wall's.
        frame = NX.focus_frame(G.POSTER)
        self.assertIn(f'colordiffuse="{NX.AMBER}">kscape-white.png', frame)
        self.assertNotIn('kscape-bar.png', self.xml)
        self.assertNotIn('kscape-badge-glossy.png', self.xml)
        self.assertIn('kscape-badge-box.png', self.xml)

    def test_panels_are_polished_glass(self):
        self.assertIn('kscape-sheen.png', self.xml)               # sheen across the pane
        self.assertIn(f'colordiffuse="{NX.FOOT_SHADOW}" flipy="true">kscape-fade.png', self.xml)

    def test_no_white_rim_anywhere(self):
        # A white line across the top of a pane looked bad on screen: gone from both.
        self.assertNotIn('Lit edge', self.xml)
        self.assertNotIn('Lit edge', shipped(NX2.NAME))

    def test_one_sheet_of_plexiglas_in_front_of_the_whole_wall(self):
        tree = ET.fromstring(self.xml)
        sheet = next(c for c in tree.iter('control') if c.get('id') == '1967')
        self.assertEqual(sheet.find('texture').text, 'kscape-plexi.png')
        self.assertEqual((int(sheet.find('width').text), int(sheet.find('height').text)),
                         (G.SCREEN_W, G.SCREEN_H))
        # One control for the wall, not one per slot, and none in the classic wall's.
        self.assertEqual(self.xml.count('>kscape-plexi.png<'), 1)   # one control, not one per slot
        self.assertNotIn('kscape-gloss.png', wallxml.slot(10000, G.POSTER, gloss=''))
        self.assertNotIn('kscape-plexi.png', shipped('script-kscape-wall.xml'))

    def test_the_sheet_is_fixed_while_the_wall_slides_behind_it(self):
        # Outside the camera (1000), inside the viewport (998): the covers move, it does not.
        viewport = next(c for c in ET.fromstring(self.xml).iter('control') if c.get('id') == '998')
        children = [c.get('id') for c in viewport.findall('control')]
        self.assertIn('1967', children)
        camera = next(c for c in viewport.findall('control') if c.get('id') == '1000')
        self.assertNotIn('1967', [c.get('id') for c in camera.iter('control')])
        self.assertLess(children.index('1000'), children.index('1967'))   # drawn over the wall

    def test_gloss_textures_are_shipped(self):
        media = os.path.join(os.path.dirname(__file__), '..', 'resources', 'skins', 'Default', 'media')
        for name in ('kscape-sheen.png', 'kscape-row.png'):
            self.assertTrue(os.path.exists(os.path.join(media, name)), name)

    def test_panel_glass_is_the_dense_shade(self):
        panel = next(c for c in ET.fromstring(self.xml).iter('control') if c.get('id') == '1903')
        self.assertIn('kscape_bg_shade', panel.find('texture').get('colordiffuse'))

    def test_opening_cascade_plays_once(self):
        self.assertIn('WindowOpen', self.xml)
        self.assertIn('String.IsEmpty(Window.Property(kscape.opened))', self.xml)

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

    def test_fades_cross_each_other(self):
        out_, = NW.turn_out(120, 'C')
        fade_in, zoom_in = NW.turn_in(120, 'C')
        f_out = dict(f.split('=', 1) for f in out_[1].split(' '))
        f_in = dict(f.split('=', 1) for f in fade_in[1].split(' '))
        f_zoom = dict(f.split('=', 1) for f in zoom_in[1].split(' '))
        self.assertEqual((f_out['effect'], f_out['start'], f_out['end']), ('fade', '100', '0'))
        self.assertEqual((f_in['effect'], f_in['start'], f_in['end']), ('fade', '0', '100'))
        self.assertEqual(int(f_in['delay']), 120 + NW.FADE_LAG_MS)          # overlap: never a gap
        self.assertLess(int(f_in['delay']), int(f_out['delay']) + int(f_out['time']))
        self.assertEqual(f_zoom['effect'], 'zoom')
        self.assertEqual(f_in['condition'], 'C')


def source(name):
    with open(os.path.join(os.path.dirname(__file__), '..', 'resources', 'lib', name), encoding='utf-8') as f:
        return f.read()


class OrderTest(unittest.TestCase):
    # Under the Kodi mocks the window classes become mocks themselves, so the wiring of the
    # class attributes is checked in the source; the behaviour runs in the fake-Kodi harness.
    def test_wave_first_then_panel(self):
        self.assertEqual(NW.SHUFFLE_DELAY_S, 2.0)
        self.assertLess(NW.PANEL_PROMPT_S, NW.SHUFFLE_DELAY_S)   # no wave coming: the panel is prompt
        self.assertGreater(NW.PANEL_REST_S, 0)
        new = source('newwall.py')
        self.assertIn('shuffle_delay_s = SHUFFLE_DELAY_S', new)
        self.assertIn('def panel_delay_s(self):', new)
        self.assertIn('info_xml = NX2.NAME', new)
        classic = source('window.py')
        self.assertIn('panel_delay_s = G.PANEL_DELAY_S', classic)     # the classic wall keeps its
        self.assertIn('shuffle_delay_s = G.SHUFFLE_DELAY_S', classic)  # order and its fiche
        self.assertIn('info_xml = None', classic)

    def test_panel_scrolls_a_long_synopsis(self):
        self.assertIn('<autoscroll', NX.panel(G.POSTER))


class ArtTest(unittest.TestCase):
    def test_logo_and_fanart_of_movie_set_and_show(self):
        kinds = {n: types.SimpleNamespace(name=n) for n in ('movies', 'tv', 'music')}
        answers = {
            'VideoLibrary.GetMovieDetails': {'moviedetails': {'art': {'clearlogo': 'image://m/',
                                                                      'fanart': 'image://f/'}}},
            'VideoLibrary.GetMovieSetDetails': {'setdetails': {'art': {'fanart': 'image://sf/'}}},
            'VideoLibrary.GetTVShowDetails': {'tvshowdetails': {'art': {'clearlogo': 'image://t/'}}},
        }
        with mock.patch.object(NW, 'rpc', side_effect=lambda method, params: answers[method]):
            self.assertEqual(NW.art_of(kinds['movies'], types.SimpleNamespace(movieid=4, key=4)),
                             {'logo': 'image://m/', 'fanart': 'image://f/'})
            self.assertEqual(NW.art_of(kinds['movies'], types.SimpleNamespace(movieid=-2, key=-2)),
                             {'logo': '', 'fanart': 'image://sf/'})
            self.assertEqual(NW.art_of(kinds['tv'], types.SimpleNamespace(tvshowid=9, key=9)),
                             {'logo': 'image://t/', 'fanart': ''})
            self.assertEqual(NW.art_of(kinds['music'], types.SimpleNamespace(key=1)), NW.NO_ART)

    def test_sound_shipped(self):
        self.assertTrue(os.path.exists(os.path.join(os.path.dirname(__file__), '..', 'resources',
                                                    'sounds', 'kscape-whoosh.wav')))


if __name__ == '__main__':
    unittest.main()
