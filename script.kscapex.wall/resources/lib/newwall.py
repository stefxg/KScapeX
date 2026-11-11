"""KScapeX "New wall test": the cover wall in a new look, beside the classic one.

C > New wall test switches a library's wall (movies or TV shows) to this look and back
(window.open_wall); the choice is kept per library. Everything else is the classic wall
(WallWindow): navigation, menus, list view, info screen. What changes:

  Opening    the covers cascade in, column by column, once (the XML's WindowOpen animations;
             the kscape.opened property, set 3 s later, keeps returns from replaying them).
  Badges     the covers carry no format badge; the selected cover shows its own, once the
             wall rests on it (newwallxml.py drops them from the slots, which Kodi then no
             longer processes every frame).
  Backdrop   with the synopsis panel, the selected film's fanart fills the view behind the
             spotlight, darkened and vignetted, with a slow settle; the wall ghosts through.
             The fanart comes with the clear logo, one JSON-RPC call per film, cached.
  Spotlight  the selected cover comes forward (zoom, soft shadow, a floor reflection, a light
             glint); everything goes at the next key press.
  Panel      smoked glass in the theme's colours at 90%, the film's clear logo in place of its
             title when the library has one.
  Counter    plain text on a dark fade along the bottom of the wall.
  Shuffle    the covers that change cross-fade where they stand, in a wave that spreads from
             the selected cover, instead of flying across the wall, which left empty cells on
             the way; a soft whoosh (xbmc.playSFX) marks it. The panel steps aside while the
             wave runs and comes back after it.

Cost on the AM6B+: the spotlight and backdrop are one property write and one setPosition when
the panel opens, one property write when it closes (everything else comes from a hidden list
item, which takes no GUI lock); the wave makes the same number of control calls as the classic
flight.
"""
import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcgui

from . import geometry as G
from . import moviesets as MS
from . import newwallxml as NX
from .library import rpc
from .wallmodel import wave_delay
from .window import HOME, WallWindow, _is

WAVE_STEP_MS = 55               # the wave's delay per cover width of distance
FADE_OUT_MS = 240               # the old cover fades away...
FADE_IN_MS = 340                # ...as the new one fades in over it (an overlap: no gap)
FADE_LAG_MS = 90                # how far the new cover trails the old one
OPENED_AFTER_S = 3.0            # kscape.opened set this long after the open (opening cascade)
NO_ART = {'logo': '', 'fanart': ''}


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


def art_of(kind, item):
    """{'logo', 'fanart'} of a library movie, movie set or TV show ('' where it has none)."""
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
            return dict(NO_ART)
    except (ValueError, TypeError, AttributeError) as e:
        xbmc.log(f'kscape.newwall: no artwork for {getattr(item, "key", "?")}: {e}', xbmc.LOGWARNING)
        return dict(NO_ART)
    art = d.get('art') or {}
    return {'logo': art.get('clearlogo') or '', 'fanart': art.get('fanart') or ''}


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
    """The new cover fades in over the old one, a touch behind it, growing the last few percent."""
    start = delay + FADE_LAG_MS
    return [('Conditional', f'effect=fade start=0 end=100 delay={start} '
                            f'time={FADE_IN_MS} tween=sine easing=out reversible=false condition={on}'),
            ('Conditional', f'effect=zoom start=96 end=100 center=auto delay={start} '
                            f'time={FADE_IN_MS} tween=cubic easing=out reversible=false condition={on}')]


class NewWallWindow(WallWindow):

    def onInit(self):
        first = not self.ready
        if first:
            # The spotlight's data: one offscreen item, updated without the GUI lock.
            self.spot_item = xbmcgui.ListItem(offscreen=True)
            self.getControl(NX.SPOT_SRC).addItems([self.spot_item])
            self.spot_on = False
            self.backdrop = self.getControl(1009)    # parked at the camera when the panel opens
            self.art = {}                    # item key -> {'logo', 'fanart'} ('' for none)
            self.art_for = None              # the item whose artwork is wanted now
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

    # ---- spotlight and panel ----------------------------------------------------------------

    def _panel_place(self):
        """The classic place, narrower by SPOT_GAP on the cover's side (newwallxml.panel): the
        zoomed frame grows into the gap instead of sliding under the panel."""
        cells, px = super()._panel_place()
        if cells[0][0] > self.focus[0]:
            px += NX.SPOT_GAP
        return cells, px

    def _show_panel(self):
        if self.shuffle_until:
            return                       # the wave first: the dwell loop brings the panel back
        item = self.wall.at(*self.focus)
        if not item:
            return
        self._spot(item)
        self.backdrop.setPosition(int(self.cam[0]), int(self.cam[1]))   # fill the view (camera
        super()._show_panel()                                           # rests while it shows)
        if self.panel_rect:
            px, py, pw, ph = self.panel_rect
            self.panel_rect = (px, py, pw - NX.SPOT_GAP, ph)
        self.setProperty('kscape.spot', '1')
        self.spot_on = True

    def _hide_panel(self):
        if self.spot_on:
            self.setProperty('kscape.spot', '')    # at once: the copy must not travel with the frame
            self.spot_on = False
        super()._hide_panel()

    def _spot(self, item):
        li = self.spot_item
        li.setArt({'poster': item.poster})
        li.setProperty('text', '' if item.poster else self.kind.fallback(item))
        li.setProperty('badge', self.kind.cover_badge(item, self.show_badges) or '')
        li.setProperty('fav', '1' if self._is_favourite(item) else '')
        self.art_for = item.key
        art = self.art.get(item.key)
        if art is not None:
            li.setProperty('logo', art['logo'])
            li.setProperty('fanart', art['fanart'])
            return
        li.setProperty('logo', '')
        li.setProperty('fanart', '')
        threading.Thread(target=self._fetch_art, args=(item,), daemon=True).start()

    def _fetch_art(self, item):
        art = art_of(self.kind, item)
        self.art[item.key] = art
        if self.art_for == item.key and not self.closing:
            self.spot_item.setProperty('logo', art['logo'])
            self.spot_item.setProperty('fanart', art['fanart'])

    def _favourites_changed(self):
        super()._favourites_changed()
        item = self.wall.at(*self.focus)
        if self.spot_on and item:
            self.spot_item.setProperty('fav', '1' if self._is_favourite(item) else '')

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
