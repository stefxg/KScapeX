"""Performance measurements for the Ugoos AM6B+ (CoreELEC avdvplus) test builds.

Everything is written to kodi.log as one line per event, at INFO level (no debug logging needed,
which would itself slow Kodi down):

    kscape.perf <event> key=value key=value ...

Events
  env            once at service start: Kodi build, screen, memory (service.py)
  sample         once a second: FPS, CPU, memory, temperature, the window and what the wall is
                 doing (phase: move, shuffle, idle) (service.py)
  library.load   a library read: items, source (cache or library), ms
  window.open    a KScape window shown: xml_ms (Kodi loading its XML, from doModal to onInit)
                 and init_ms (our onInit), total_ms
  wall.move      summary of the cover-wall moves when the wall closes: n, mean, p50, p95, max ms
                 (Python time per key press, GUI lock waits included), slot moves per press
  wall.move.slow one move that took more than SLOW_MOVE_MS
  wall.shuffle   preparing a related-cover shuffle: ms, slots
  wall.panel     showing the synopsis panel: ms

The measurements are on while the add-on setting "perf" is on (Settings > Performance); the
service then also sets Window(Home).Property(kscape.perf), which shows the skin's overlay
(Custom_1191_KScapePerf.xml). Off: nothing is logged and the overlay is hidden.
"""
import time

import xbmc
import xbmcaddon
import xbmcgui

ADDON_ID = 'script.kscapex.wall'
HOME = xbmcgui.Window(10000)
PREFIX = 'kscape.perf'
PROP_ON = 'kscape.perf'              # overlay shown (set by the service)
PROP_VIEW = 'kscape.perf.view'       # the KScape window on top, as the samples report it
PROP_PHASE = 'kscape.perf.phase'     # what the wall is doing: move, shuffle, idle
PROP_LAST = 'kscape.perf.last'       # the last measurement, for the overlay
SLOW_MOVE_MS = 40.0

_enabled = None


def setting():
    """The add-on setting, read now (the service calls this every second)."""
    try:
        return xbmcaddon.Addon(ADDON_ID).getSettingBool('perf')
    except Exception:
        return False


def enabled():
    """The setting, read once per script run (a RunScript is a fresh interpreter)."""
    global _enabled
    if _enabled is None:
        _enabled = setting()
    return _enabled


def set_enabled(on):
    """The service, which runs for the whole session, re-reads the setting every second."""
    global _enabled
    _enabled = bool(on)


def now():
    return time.perf_counter()


def ms_since(t0):
    return (time.perf_counter() - t0) * 1000.0


def _fmt(v):
    if isinstance(v, float):
        return f'{v:.1f}'
    text = str(v)
    return text.replace(' ', '_') if text else '-'


def log(event, **fields):
    if not enabled():
        return
    parts = ' '.join(f'{k}={_fmt(v)}' for k, v in fields.items())
    xbmc.log(f'{PREFIX} {event} {parts}', xbmc.LOGINFO)


_last = None


def show(text, defer=False):
    """The overlay's last-measurement line. A window property write waits for Kodi's GUI lock
    (about a frame), so on a key press it is deferred: the wall's background loop writes it
    (flush), and the press measures only the wall's own work."""
    global _last
    if not enabled():
        return
    if defer:
        _last = text
    else:
        _last = None
        HOME.setProperty(PROP_LAST, text)


def flush():
    global _last
    text, _last = _last, None
    if text is not None:
        HOME.setProperty(PROP_LAST, text)


_phase = None


def phase(name):
    """What the wall is doing (written only when it changes: the wall's loop calls this 20
    times a second)."""
    global _phase
    if enabled() and _phase != name:
        _phase = name
        HOME.setProperty(PROP_PHASE, name)


def view(name):
    if enabled():
        HOME.setProperty(PROP_VIEW, name)


# ---- window opening ----------------------------------------------------------------------------

def opening(window):
    """modal.run, just before doModal(): start the window's clock."""
    if enabled():
        window._perf_t0 = now()


def init(window):
    """First line of onInit: Kodi has loaded the window's XML."""
    t0 = getattr(window, '_perf_t0', None)
    if t0 is not None and getattr(window, '_perf_t1', None) is None:
        window._perf_t1 = now()


def ready(window, name, **fields):
    """End of the first onInit: log how long the window took to show."""
    t0 = getattr(window, '_perf_t0', None)
    t1 = getattr(window, '_perf_t1', None)
    if t0 is None:
        return
    window._perf_t0 = None
    window._perf_name = name
    t2 = now()
    xml_ms = (t1 - t0) * 1000.0 if t1 else 0.0
    init_ms = (t2 - t1) * 1000.0 if t1 else 0.0
    total = (t2 - t0) * 1000.0
    log('window.open', name=name, xml_ms=xml_ms, init_ms=init_ms, total_ms=total, **fields)
    show(f'{name} : {total:.0f} ms')
    view(name)


def closed(below):
    """modal.run, after doModal(): the window beneath (or Home) is on top again."""
    global _phase
    if enabled():
        HOME.setProperty(PROP_VIEW, getattr(below, '_perf_name', '') if below else 'home')
        HOME.setProperty(PROP_PHASE, '')
        _phase = None


# ---- statistics --------------------------------------------------------------------------------

class Stats:
    """Durations (ms) of one kind of event, summarised when the window closes."""

    def __init__(self, event):
        self.event = event
        self.values = []
        self.extra = []

    def add(self, ms, extra=0):
        self.values.append(ms)
        self.extra.append(extra)

    def summary(self, **fields):
        if not self.values:
            return
        v = sorted(self.values)
        n = len(v)

        def pct(p):
            return v[min(n - 1, int(round(p * (n - 1))))]

        log(self.event, n=n, mean=sum(v) / n, p50=pct(0.5), p95=pct(0.95), max=v[-1],
            calls_mean=sum(self.extra) / n, **fields)


# ---- service: environment and samples ----------------------------------------------------------

def _info(label):
    return xbmc.getInfoLabel(label)


def log_env():
    log('env', kodi=_info('System.BuildVersion'), built=_info('System.BuildDate'),
        os=_info('System.OSVersionInfo'), kernel=_info('System.KernelVersion'),
        screen=_info('System.ScreenResolution'), width=_info('System.ScreenWidth'),
        height=_info('System.ScreenHeight'), mem_total=_info('System.Memory(total)'),
        skin=xbmc.getSkinDir())


def sample():
    win = xbmcgui.getCurrentWindowId()
    dlg = xbmcgui.getCurrentWindowDialogId()
    name = 'home' if win == 10000 else (HOME.getProperty(PROP_VIEW) or str(win))
    log('sample', fps=_info('System.FPS'), cpu=_info('System.CpuUsage'),
        mem=_info('System.Memory(used.percent)'), temp=_info('System.CPUTemperature'),
        win=win, dlg=dlg, view=name, phase=HOME.getProperty(PROP_PHASE) or '-',
        video=int(xbmc.getCondVisibility('Player.HasVideo')))
