"""KScapeX: the user's language and regional formats, from Kodi (pure Python once configured).

Kodi gives month names (its strings 21-32), the clock (Settings > Interface > Regional: 12 or
24 hours) and the order of day and month. from_kodi() reads them once per script run; until
then (the unit tests) every function keeps KScape's original English output.

Titles: with Kodi in French, titles sort without their leading article (The, Le, La, Les, L')
and without accents (É sorts with E), as a French library is read. In English Kodi's own library
order is kept.
"""
import re
import unicodedata
from types import SimpleNamespace

_conf = {'lang': '', 'months': (), 'clock24': False, 'day_first': False}

ENGLISH_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                  'September', 'October', 'November', 'December')
_ARTICLES_EN = re.compile(r'^the[\s._]+', re.IGNORECASE)
_ARTICLES_FR = re.compile(r"^(?:(?:the|le|la|les)[\s._]+|l['’]\s*)", re.IGNORECASE)
_DATE = re.compile(r'^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:[ T](\d{2}):(\d{2}))?')


def configure(lang='', months=(), clock24=False, day_first=False):
    _conf.update(lang=(lang or '').lower()[:2], months=tuple(months), clock24=bool(clock24),
                 day_first=bool(day_first))


def from_kodi():
    """Read Kodi's language and regional formats (call once at the start of a script run)."""
    try:
        import xbmc
        lang = xbmc.getLanguage(xbmc.ISO_639_1) or ''
        months = [xbmc.getLocalizedString(21 + i) for i in range(12)]
        clock = xbmc.getRegion('time') or ''
        datelong = xbmc.getRegion('datelong') or ''
    except Exception:
        return
    d = min((datelong.find(t) for t in ('%d', '%-d', '%e') if t in datelong), default=-1)
    m = datelong.find('%B')
    configure(lang, months if all(months) else ENGLISH_MONTHS,
              clock24='%H' in clock or '%k' in clock, day_first=0 <= d < m if m >= 0 else d >= 0)


def configured():
    return bool(_conf['months'])


def language():
    """Kodi's language as two letters ('fr', 'en'); '' before from_kodi()."""
    return _conf['lang']


def french():
    return _conf['lang'] == 'fr'


# ---- dates and times -------------------------------------------------------------------------

def _month(n):
    months = _conf['months'] or ENGLISH_MONTHS
    return months[n - 1]


def day(d, now=None):
    """'6 novembre' / 'November 6' (with the year when it is not this year's)."""
    if _conf['day_first']:
        text = f'{d.day} {_month(d.month)}'
        return text if now is not None and d.year == now.year else f'{text} {d.year}'
    text = f'{_month(d.month)} {d.day}'
    return text if now is not None and d.year == now.year else f'{text}, {d.year}'


def clock(d):
    """'14:05' (24-hour Kodi) / '2:05 pm'."""
    if _conf['clock24']:
        return f'{d.hour}:{d.minute:02d}'
    h = d.hour % 12 or 12
    return f"{h}:{d.minute:02d} {'am' if d.hour < 12 else 'pm'}"


def date_text(text):
    """A Kodi / TMDB / Wikidata date ('1978-09-12', '1978-09' or '1978', a time may follow) as the
    user reads it: '12 septembre 1978' / 'September 12, 1978'; unchanged before from_kodi()."""
    text = (text or '').strip()
    m = _DATE.match(text)
    if not configured() or not m or text.startswith('0000'):
        return text
    year, month, dd = m.group(1), m.group(2), m.group(3)
    if not month or month == '00':
        return year
    name = _month(int(month))
    if not dd or dd == '00':
        return f'{name} {year}'
    return f'{int(dd)} {name} {year}' if _conf['day_first'] else f'{name} {int(dd)}, {year}'


def stamp_text(stamp):
    """Kodi's 'YYYY-MM-DD HH:MM:SS' as a date and time: '6 novembre 2026, 14:05'. Before
    from_kodi(): 'YYYY-MM-DD HH:MM' as KScape showed it."""
    stamp = stamp or ''
    if not stamp or stamp.startswith('0000'):
        return ''
    m = _DATE.match(stamp)
    if not configured() or not m or not m.group(3):
        return stamp[:16]
    text = date_text(stamp[:10])
    if m.group(4) is None:
        return text
    t = SimpleNamespace(hour=int(m.group(4)), minute=int(m.group(5)))
    return f'{text}, {clock(t)}'


# ---- titles ----------------------------------------------------------------------------------

def _articles():
    return _ARTICLES_FR if french() else _ARTICLES_EN


def article_length(title):
    """How many leading characters a title sorts without ('The Lion King' -> 4, "L'Abandon" -> 2
    in French)."""
    m = _articles().match(title or '')
    return m.end() if m else 0


def fold(text):
    """Lower case without accents: 'Été' -> 'ete'."""
    return ''.join(c for c in unicodedata.normalize('NFKD', text or '') if not unicodedata.combining(c)).casefold()


def title_key(title):
    title = (title or '').strip()
    return fold(title[article_length(title):])


def in_title_order(items):
    """`items` (movies or TV shows) by title as a French reader expects; unchanged otherwise
    (Kodi's own library order)."""
    if not french():
        return list(items)
    return sorted(items, key=lambda m: (title_key(getattr(m, 'sorttitle', '') or m.title), title_key(m.title), m.key))


# ---- certifications --------------------------------------------------------------------------

FR_RATINGS = {'tp': 0, 'tous publics': 0, 'u': 0, '10': 1, '-10': 1, '12': 2, '-12': 2, '16': 3, '-16': 3,
              '18': 4, '-18': 4}


def french_rating_rank(rating):
    """Rank of a French certification (Tous publics, -10, -12, -16, -18), or None."""
    r = (rating or '').strip().lower()
    for prefix in ('fr:', 'fr '):
        if r.startswith(prefix):
            r = r[len(prefix):].strip()
    return FR_RATINGS.get(r)
