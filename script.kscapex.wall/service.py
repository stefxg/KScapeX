"""Service: plays scenes and Demo Scripts (resources/lib/demoservice.py), and keeps the display &
aspect ratio properties the skin reads current (resources/lib/displayui.py). Starts with Kodi."""
import os
import shutil
import threading

import xbmc
import xbmcvfs

from resources.lib.demoservice import run

DISPLAY_CHECK_S = 3.0
PERF_SAMPLE_S = 1.0


def install_splash():
    """Kodi shows special://home/media/splash.png while it starts, before any skin loads: put the
    KScape logo there (next start shows it). Replaces only a splash that is not ours already."""
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'media', 'splash.png')
    dest = xbmcvfs.translatePath('special://home/media/splash.png')
    try:
        if os.path.exists(dest) and os.path.getsize(dest) == os.path.getsize(src):
            return
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(src, dest)
    except OSError as e:
        xbmc.log(f'kscape: installing the splash screen: {e}', xbmc.LOGWARNING)


def follow_display():
    """Publish the display transform at start, then whenever the screen or a display setting
    changes (a resolution change, the settings edited outside KScape's dialogs)."""
    from resources.lib import displayui, versionsui
    versionsui.labels()
    mon = xbmc.Monitor()
    seen = None
    while not mon.abortRequested():
        try:
            now = (displayui.screen(), tuple(sorted(displayui.settings().items())))
            if now != seen:
                seen = now
                displayui.publish()
                displayui.publish_pointer()
                displayui.labels()
        except Exception as e:                       # never take the scene service down with it
            xbmc.log(f'kscape: display properties: {e}', xbmc.LOGWARNING)
        if mon.waitForAbort(DISPLAY_CHECK_S):
            break


def perf_off_once():
    """KScapeX 0.16.2: "Measure performance" is off by default now. Kodi keeps the value an
    earlier version saved (on, the old default), so switch it off once; afterwards the user's
    own choice stands."""
    import xbmcaddon
    from resources.lib import state
    if state.load().get('perf_default_off'):
        return
    try:
        xbmcaddon.Addon('script.kscapex.wall').setSettingBool('perf', False)
        state.save(perf_default_off=True)
    except Exception as e:
        xbmc.log(f'kscape: switching performance measuring off: {e}', xbmc.LOGWARNING)


def sample_performance():
    """Performance test builds: while the add-on setting "perf" is on, show the skin's overlay
    (Window(Home).Property(kscape.perf)) and write a sample line to kodi.log every second
    (resources/lib/perf.py). The setting is read again each second, so it can be switched on
    or off without restarting Kodi."""
    import xbmcgui
    from resources.lib import perf
    home = xbmcgui.Window(10000)
    mon = xbmc.Monitor()
    was_on = False
    while not mon.abortRequested():
        try:
            on = perf.setting()
            perf.set_enabled(on)
            if on != was_on:
                home.setProperty(perf.PROP_ON, '1' if on else '')
                if on:
                    perf.log_env()
                was_on = on
            if on:
                perf.sample()
        except Exception as e:                       # never take the scene service down with it
            xbmc.log(f'kscape: performance sample: {e}', xbmc.LOGWARNING)
        if mon.waitForAbort(PERF_SAMPLE_S):
            break


if __name__ == '__main__':
    install_splash()
    perf_off_once()
    threading.Thread(target=follow_display, daemon=True).start()
    threading.Thread(target=sample_performance, daemon=True).start()
    run()
