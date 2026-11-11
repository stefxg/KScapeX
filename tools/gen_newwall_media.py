"""Generate the sound of the "New wall test" view (script.kscapex.wall/resources/lib/
newwall.py), into resources/sounds:

  kscape-whoosh.wav   soft noise sweep played when the wall rearranges (xbmc.playSFX)

The view used to need textures too - a drop shadow, a vignette, a glint, a floor reflection
mask, a sheen, a sheet of plexiglas. The wall is flat now (newwallxml.py), so they are all
gone, and the only thing left to build is the sound.

Usage: python3 tools/gen_newwall_media.py
"""
import math
import os
import random
import struct
import wave as wavemod

ADDON = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'script.kscapex.wall')
SOUNDS = os.path.join(ADDON, 'resources', 'sounds')


def whoosh(path, ms=380, rate=44100, loud=0.22):
    """Soft band-swept noise with a sine-squared envelope: the wave's sound."""
    rng = random.Random(9599)
    n = int(rate * ms / 1000)
    raw, value = [], 0.0
    for _ in range(n):                              # brownish noise (random walk, re-centred)
        value += rng.uniform(-1, 1) * 0.28
        value *= 0.985
        raw.append(value)
    out = []
    for i in range(n):
        p = i / (n - 1)
        span = max(1, int(26 * (1.0 - 0.82 * p)))    # narrowing average: pitch rises through the sweep
        lo, hi = max(0, i - span), min(n, i + span + 1)
        sample = sum(raw[lo:hi]) / (hi - lo)
        env = math.sin(math.pi * min(1.0, p * 1.12)) ** 2
        out.append(sample * env)
    top = max(abs(s) for s in out) or 1.0
    frames = b''.join(struct.pack('<h', int(32767 * loud * s / top)) for s in out)
    with wavemod.open(path, 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(rate)
        f.writeframes(frames)


def main():
    os.makedirs(SOUNDS, exist_ok=True)
    path = os.path.join(SOUNDS, 'kscape-whoosh.wav')
    whoosh(path)
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
