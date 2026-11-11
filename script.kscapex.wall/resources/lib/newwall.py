"""KScapeX "New wall test": the cover wall in a new look, beside the classic one.

C > New wall test switches a library's wall (movies or TV shows) to this look and back
(window.open_wall); the choice is kept per library. Everything else is the classic wall
(WallWindow): navigation, menus, list view, info screen. What changes:

  Opening    the covers fade in, column by column, once (the XML's WindowOpen animations;
             the kscape.opened property, set 3 s later, keeps returns from replaying them).
  Badges     no format badge on any cover: the panel beside the selected one already gives the
             format, so repeating it on the poster was noise (and two controls and one
             condition per slot that Kodi no longer processes every frame).
  Panel      a solid panel in the theme's colours, the film's clear logo in place of its title
             when the library has one (one JSON-RPC call per film, cached); a synopsis longer
             than its four lines scrolls slowly through them (XML autoscroll, only while the
             panel is up). Nothing is drawn behind it: the wall stays visible around it.
  Counter    plain text, bottom right.
  Shuffle    the covers that change cross-fade where they stand, in a wave that spreads from
             the selected cover, instead of flying across the wall, which left empty cells on
             the way; a soft whoosh (xbmc.playSFX) marks it.
  Order      the wave comes first (2 s), the panel after it has settled (~1 s later), so the
             two never fight: the wall rearranges itself around the film, rests, and then the
             scene lights up. When no wave is coming (automatic shuffle off, or the wall is
             already arranged around this film), the panel comes at 1.2 s instead.

It is flat on purpose: 0.18 to 0.22 tried a spotlight, shadows, a reflection, polished glass,
a sheet of plexiglas and a fanart backdrop, and each of them fought the posters. Hierarchy now
comes from colour, weight and spacing alone.

Cost on the AM6B+: the clear logo goes into a hidden list item, which takes no GUI lock; the
wave makes the same number of control calls as the classic flight.
"""
import math
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from . import geometry as G
from . import moviesets as MS
from . import newinfoxml as NX2
from . import newwallxml as NX
from .library import rpc
from .wallmodel import wave_delay
from .window import HOME, WallWindow, _is

SHUFFLE_DELAY_S = 2.0           # the wave, 2 s after the last key press (before the panel)
PANEL_PROMPT_S = 1.2            # the panel, when no wave is coming
PANEL_REST_S = 1.0              # ...and this long after a wave has settled
WAVE_STEP_MS = 55               # the wave's delay per cover width of distance
FADE_OUT_MS = 240               # the old cover fades away...
FADE_IN_MS = 340                # ...as the new one fades in over it (an overlap: no gap)
FADE_LAG_MS = 90                # how far the new cover trails the old one
OPENED_AFTER_S = 3.0            # kscape.opened set this long after the open (opening cascade)


def sound(name):
    """Path of one of the add-on's sounds ('' when it is not there)."""
    path = os.path.join(xbmcaddon.Addon('script.kscapex.wall').getAddonInfo('path'),
                        'resources', 'sounds', name)
    return path if os.path.exists(path) else ''


def play_sound(name):
    """Play one of the add-on's sounds, where Kodi offers playSFX (never required)."""
    path, sfx = sound(name), getattr(xbmc, 'playSFX', None)
    if path and sfx:
        try:
            sfx(path)
        except (RuntimeError, TypeError):
            pass


def clearlogo(kind, item):
    """The clear logo of a library movie, movie set or TV show ('' when it has none)."""
    try:
        if kind.name == 'movies' and MS.is_set(item):
            d = rpc('VideoLibrary.GetMovieSetDetails',
                    {'setid': MS.set_id(item), 'properties': ['art']}).get('setdetails') or {}
        elif kind.name == 'movies':
            d = rpc('VideoLibrary.GetMovieDetails',
                    {'movieid': item.movieid, 'properties': ['art']}).get('moviedetails') or {}
        elif kind.name == 'tv':
            d = rpc('VideoLibrary.GetTVShowDetails',
                    {'tvshowid': item.tvshowid, 'properties': ['art']}).get('tvshowdetails') or {}
        else:
            return ''
    except (ValueError, TypeError, AttributeError) as e:
        xbmc.log(f'kscape.newwall: no clear logo for {getattr(item, "key", "?")}: {e}', xbmc.LOGWARNING)
        return ''
    return (d.get('art') or {}).get('clearlogo') or ''


def wave_plan(old, new, slot_cells, seen, centre, layout):
    """[(slot, cell, delay ms)]: the slots whose cover changes in a cell on screen (`seen`), and
    when each turns over - the further from `centre`, the later (wallmodel.wave_delay). A cell
    whose cover stays needs nothing: both pools show the same cover there."""
    def key_at(wall, cell):
        item = wall.at(*cell)
        return item.key if item is not None else None
    return [(k, cell, wave_delay(cell, centre, layout, WAVE_STEP_MS)) for k, cell in slot_cells
            if key_at(new, cell) != key_at(old, cell) and seen(cell)]


def turn_out(delay, on):
    """The old cover fades away (and stays gone until its pool retires)."""
    return [('Conditional', f'effect=fade start=100 end=0 delay={delay} '
                            f'time={FADE_OUT_MS} tween=sine easing=in reversible=false condition={on}')]


def turn_in(delay, on):
    """The new cover fades in over the old one, a touch behind it. A plain fade: the wall is
    flat, so nothing grows or shrinks."""
    return [('Conditional', f'effect=fade start=0 end=100 delay={delay + FADE_LAG_MS} '
                            f'time={FADE_IN_MS} tween=sine easing=out reversible=false condition={on}')]


class NewWallWindow(WallWindow):

    def onInit(self):
        first = not self.ready
        if first:
            # The panel's data: one offscreen item, updated without the GUI lock.
            self.spot_item = xbmcgui.ListItem(offscreen=True)
            self.getControl(NX.SPOT_SRC).addItems([self.spot_item])
            self.logos = {}                  # item key -> clear logo url ('' for none)
            self.logo_for = None             # the item whose logo is wanted now
            self.wave_rest_until = 0.0       # the wave has settled; the panel waits until then
        super().onInit()
        if first:
            # The opening cascade plays while kscape.opened is unset; after that, coming back
            # from the info screen or playback re-opens the window without it.
            timer = threading.Timer(OPENED_AFTER_S, self._mark_opened)
            timer.daemon = True
            timer.start()

    def _mark_opened(self):
        try:
            self.setProperty('kscape.opened', '1')
        except RuntimeError:                 # the window has closed
            pass

    # ---- the order of the dwell: wave first, then the panel ---------------------------------

    shuffle_delay_s = SHUFFLE_DELAY_S
    info_xml = NX2.NAME              # the cinema fiche (newinfoxml.py)

    @property
    def panel_delay_s(self):
        """The wave first: while one is still to come for this film, the panel holds back
        entirely (the wave, and then _show_panel's rest, bring it in afterwards)."""
        item = self.wall.at(*self.focus)
        waving = (self.auto_shuffle and item is not None and self.shuffled_for != item.key
                  and len(self.wall.movies()) > 1)
        return math.inf if waving else PANEL_PROMPT_S

    def _finish_shuffle(self):
        if self.shuffle_until:
            self.wave_rest_until = time.time() + PANEL_REST_S
        super()._finish_shuffle()

    # ---- the panel ---------------------------------------------------------------------------

    def _show_panel(self):
        if self.shuffle_until or time.time() < self.wave_rest_until:
            return                       # the wave first, and a breath after it settles
        item = self.wall.at(*self.focus)
        if not item:
            return
        self._logo(item)
        super()._show_panel()

    def _logo(self, item):
        """The film's clear logo into the hidden item, for the panel to show in place of the
        title. Unknown ones are fetched off the GUI thread and kept."""
        self.logo_for = item.key
        logo = self.logos.get(item.key)
        if logo is not None:
            self.spot_item.setProperty('logo', logo)
            return
        self.spot_item.setProperty('logo', '')
        threading.Thread(target=self._fetch_logo, args=(item,), daemon=True).start()

    def _fetch_logo(self, item):
        logo = clearlogo(self.kind, item)
        self.logos[item.key] = logo
        if self.logo_for == item.key and not self.closing:
            self.spot_item.setProperty('logo', logo)

    # ---- shuffle: a wave ----------------------------------------------------------------------

    def _before_shuffle(self):
        """C > Shuffle now: where the panel will be (the shuffle keeps clear of it), without
        showing it - it steps aside for the wave anyway."""
        if not self.panel_shown:
            self.panel_cells = tuple(self._panel_place()[0])

    def _shuffle_related(self, anchor):
        self._hide_panel()
        super()._shuffle_related(anchor)

    def _transition(self, new, anchor_key=None):
        """Cross-fade, where they stand, the covers on screen whose cell changes: the old one
        fades away as the new one fades in over it, each cell later the further it is from
        the selected cover. Off screen, and with Reduce motion, the covers swap at once.

        Control calls, as in the classic flight: one per pool for each cover on screen that
        changes, none for a cover that keeps its cell (both pools show it, so the swap of pools
        is invisible there)."""
        self.front.flush()                           # deferred moves: slots where their cells are
        self.back.flush()
        lay = self.lay
        old = self.wall
        self.front_token += 1
        tok = self.front_token
        on = _is(self.prop_front, tok)
        before = _is(self.prop_front, tok - 1)       # the value until the flip below
        cx, cy = self.cam
        vw, vh = G.view_size(lay)
        instant = self.reduced
        centre = (new.cell_of(anchor_key) if anchor_key is not None else None) or self.focus
        longest = 0

        def seen(cell):
            px, py = self._cell_xy(cell)
            return cx - lay.cover_w < px < cx + vw and cy - lay.cover_h < py < cy + vh

        vanish = [('Conditional', f'effect=fade start=0 end=0 time=0 reversible=false condition={on}')]
        front_at = {self.front.cell[k]: k for k in range(self.pool_size)
                    if self.front.visible[k] and self.front.shown[k] is not None}
        # Back buffer: the new arrangement, transparent until the flip (see WallWindow._transition).
        self.back.group.setAnimations([('Conditional', f'effect=fade start=0 end=0 time=0 '
                                                       f'reversible=false condition={before}')])
        cells = list(self._slot_cells())
        for k, cell, delay in wave_plan(old, new, cells, seen, centre, lay):
            j = front_at.get(cell)
            if instant:
                if j is not None:
                    self.front.slots[j].setAnimations(vanish)
                continue
            if new.at(*cell) is not None:
                self.back.slots[k].setAnimations(turn_in(delay, on))
            if j is not None:
                self.front.slots[j].setAnimations(turn_out(delay, on))
            longest = max(longest, delay + FADE_LAG_MS + FADE_IN_MS)
        for k, cell in cells:
            self._bind(self.back, k, cell, new.at(*cell))

        if longest and not instant:
            play_sound('kscape-whoosh.wav')
        HOME.setProperty(self.prop_front, str(tok))  # one flip starts every animation above
        self.wall = new
        self.front, self.back = self.back, self.front
        self.shuffle_until = time.time() + longest / 1000.0 + 0.05
