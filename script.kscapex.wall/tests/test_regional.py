"""KScapeX: language and regional formats (regional.py). Run: python3 -m unittest discover -s tests"""
import os
import sys
import unittest
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from resources.lib import collectionmodel as C  # noqa: E402
from resources.lib import listmodel as L  # noqa: E402
from resources.lib import moviesets as MS  # noqa: E402
from resources.lib import regional as R  # noqa: E402

FR_MONTHS = ('janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre',
             'octobre', 'novembre', 'décembre')


def item(key, title, sorttitle=''):
    return SimpleNamespace(key=key, title=title, sorttitle=sorttitle or title.lower())


class Unconfigured(unittest.TestCase):
    """Before from_kodi() (and in English) KScape's original output is kept."""

    def setUp(self):
        R.configure()
        R._conf['months'] = ()

    def test_dates_and_clock(self):
        now = datetime(2026, 11, 6)
        self.assertEqual(R.day(datetime(2026, 3, 4), now), 'March 4')
        self.assertEqual(R.day(datetime(2025, 3, 4), now), 'March 4, 2025')
        self.assertEqual(R.clock(datetime(2026, 1, 1, 14, 5)), '2:05 pm')
        self.assertEqual(R.date_text('1964-09-02'), '1964-09-02')
        self.assertEqual(R.stamp_text('2026-11-06 14:05:33'), '2026-11-06 14:05')
        self.assertEqual(R.stamp_text('0000-00-00 00:00:00'), '')

    def test_titles_keep_kodi_order(self):
        lib = [item(1, "L'Abandon"), item(2, 'Alien')]
        self.assertEqual([m.key for m in R.in_title_order(lib)], [1, 2])
        self.assertEqual(R.article_length('The Lion King'), 4)
        self.assertEqual(R.article_length("L'Abandon"), 0)


class French(unittest.TestCase):
    def setUp(self):
        R.configure('fr', FR_MONTHS, clock24=True, day_first=True)

    def tearDown(self):
        R.configure()
        R._conf['months'] = ()

    def test_dates_and_clock(self):
        now = datetime(2026, 11, 6)
        self.assertEqual(R.day(datetime(2026, 11, 6), now), '6 novembre')
        self.assertEqual(R.day(datetime(2025, 8, 1), now), '1 août 2025')
        self.assertEqual(R.clock(datetime(2026, 1, 1, 14, 5)), '14:05')
        self.assertEqual(R.date_text('1964-09-02'), '2 septembre 1964')
        self.assertEqual(R.date_text('1978-09'), 'septembre 1978')
        self.assertEqual(R.date_text('1978'), '1978')
        self.assertEqual(R.stamp_text('2026-11-06 14:05:33'), '6 novembre 2026, 14:05')

    def test_collection_lines(self):
        movie = SimpleNamespace(dateadded='2026-11-02 09:00:00', lastplayed='2026-10-30 21:40:00')
        tr = {32161: 'Ajouté le {}', 32162: 'En pause le {} à {}', 32163: 'Vu le {}'}.get
        now = datetime(2026, 11, 6)
        self.assertEqual(C.describe('new', movie, tr, now), 'Ajouté le 2 novembre')
        self.assertEqual(C.describe('paused', movie, tr, now), 'En pause le 30 octobre à 21:40')

    def test_titles_sort_without_articles_and_accents(self):
        lib = [item(1, "L'Abandon"), item(2, 'Le Bureau des légendes'), item(3, 'Été 85'),
               item(4, 'Alien'), item(5, 'The Batman'), item(6, 'Les Misérables'), item(7, 'La La Land')]
        self.assertEqual([m.title for m in R.in_title_order(lib)],
                         ["L'Abandon", 'Alien', 'The Batman', 'Le Bureau des légendes', 'Été 85',
                          'La La Land', 'Les Misérables'])
        self.assertEqual(L.sort_letter("L'Abandon"), 2)
        self.assertEqual(L.sort_letter('Les Misérables'), 4)
        self.assertEqual(MS.sort_key('La Saga Alien'), 'saga alien')

    def test_french_certifications_in_order(self):
        def rated(r):
            return SimpleNamespace(mpaa=r)
        order = sorted(['16', 'Tous publics', '-12', '18', '10', 'PG-13'], key=lambda r: L._rating_key(rated(r)))
        self.assertEqual(order[0], 'Tous publics')
        self.assertEqual(order[-2:], ['16', '18'])
