"""KScapeX "New wall test": the cover wall's XML in its new look (newwall.py drives it).

Built from the classic wall's pieces (wallxml.py), so both stay in step; the classic wall's XML
is not touched. What changes, against wallxml's control map:

  slots        no format badge (the selected cover shows it, in the spotlight): two controls
               and one condition fewer per slot, on every frame
  slots        the opening cascade: each cover fades and grows in once, column by column, when
               the window opens (wallxml.slot(opening=True); Window.Property(kscape.opened),
               set by newwall.py a moment later, keeps later activations from replaying it)
  1992         hidden data list holding one item: the selected cover's poster, badge, favourite
               mark, text, clear logo and fanart (newwall.py sets them; no GUI lock)
  1009         backdrop while Window.Property(kscape.spot) is set: the selected film's fanart
               over the whole view - the covers ghost through it - under a dark veil and a
               vignette. It sits inside the camera, between the covers and the spotlight;
               newwall.py parks it at the camera's position when the panel opens (the camera
               stands still while the panel is up), so it fills the view
  1001         focus frame, now also:
    1010         spotlight: the frame's bars and a copy of the selected cover - soft shadow,
                 floor reflection (the poster mirrored through kscape-reflect.png), a light
                 glint that crosses it once (kscape-gloss.png) - zooming in (SPOT_ZOOM) while
                 kscape.spot is set. The copy loads in the background, like the slots: Kodi
                 hands it the slot's texture, already loaded
  1900         info panel in smoked glass: the theme's background at 90% (kscape_bg_shade), a
               glow and a line in the theme colour along the top, a thin outline; SPOT_GAP
               narrower than the classic
               one, so the zoomed frame never slides under it. 1906 the film's clear logo in
               place of the title (1901 hides while there is one)
  1966         dark fade along the bottom of the view; the counter (1965) sits on it as plain
               text, without its box
"""
from . import geometry as G
from . import npchip as np_chip
from . import wallxml as W
from .wallxml import AMBER, BADGE_H, BADGE_MIN_W, CARD, HEART, HEART_BOX, x

SPOT = '!String.IsEmpty(Window.Property(kscape.spot))'
SPOT_SRC = 1992
SPOT_ZOOM = 108                 # percent: the selected cover while it is in the spotlight
SPOT_GAP = 14                   # px between the zoomed frame and the panel (>= the zoom's growth)
SPOT_IN_MS, SPOT_OUT_MS = 240, 160
BACK_IN_MS, BACK_OUT_MS = 550, 350       # the fanart backdrop's fades
FANART_ALPHA = 'D8FFFFFF'       # the fanart over the covers: they ghost through at ~15%
VEIL = 'B4000000'               # dark veil over the fanart, so the spotlight and panel carry
SHADOW_PAD, SHADOW_DROP = 30, 12
REFLECT_FRACTION = 0.45         # of the cover's height (kscape-reflect.png fades it out sooner)
FADE_H = 110                    # bottom fade under the counter
LOGO_H = 76


def spot(info):
    return f'$INFO[Container({SPOT_SRC}).ListItemAbsolute(0).{info}]'


def spot_has(name):
    return f'!String.IsEmpty(Container({SPOT_SRC}).ListItemAbsolute(0).Property({name}))'


def spot_source():
    return f'''		<control type="list" id="{SPOT_SRC}">
			<description>Data for the spotlight (newwall.py): the selected cover's poster, badge, mark, logo, fanart</description>
			<left>-4000</left>
			<top>-4000</top>
			<width>10</width>
			<height>10</height>
			<itemlayout width="10" height="10"/>
			<focusedlayout width="10" height="10"/>
		</control>
'''


def backdrop(L):
    """The selected film's fanart filling the view while the panel is up, behind the spotlight:
    the image eases back from 106% once, a veil and a vignette darken it, and the covers ghost
    through (FANART_ALPHA). With no fanart, the veil and vignette still dim the wall."""
    vw, vh = G.view_size(L)
    return f'''			<control type="group" id="1009">
				<description>Backdrop: fanart, veil and vignette while the panel is up (newwall.py parks it at the camera)</description>
				<visible>{SPOT}</visible>
				<animation effect="fade" start="0" end="100" time="{BACK_IN_MS}">Visible</animation>
				<animation effect="fade" start="100" end="0" time="{BACK_OUT_MS}">Hidden</animation>
				<control type="image">
					<width>{vw}</width>
					<height>{vh}</height>
					<aspectratio>scale</aspectratio>
					<fadetime>400</fadetime>
					<texture background="true" colordiffuse="{FANART_ALPHA}">{spot('Property(fanart)')}</texture>
					<animation effect="zoom" start="106" end="100" center="auto" time="1600" tween="sine" easing="out" reversible="false" condition="{SPOT}">Conditional</animation>
				</control>
				<control type="image">
					<width>{vw}</width>
					<height>{vh}</height>
					<texture colordiffuse="{VEIL}">kscape-white.png</texture>
				</control>
				<control type="image">
					<width>{vw}</width>
					<height>{vh}</height>
					<texture>kscape-vignette.png</texture>
				</control>
			</control>'''


def focus_frame(L):
    """The amber frame and the spotlit copy of the selected cover (shadow, reflection, glint)."""
    t, tx = L.frame, G.fx(L)
    w, h = L.cover_w + 2 * tx, L.cover_h + 2 * t
    cw, ch = L.cover_w, L.cover_h
    bars = [(0, 0, w, t), (0, h - t, w, t), (0, t, tx, h - 2 * t), (w - tx, t, tx, h - 2 * t)]
    pad = SHADOW_PAD
    out = [f'''			<control type="group" id="1001">
				<description>Focus frame and spotlight (newwallxml)</description>
				<width>{w}</width>
				<height>{h}</height>
				<control type="group" id="1010">
					<description>Spotlight: zooms the frame and the copy of the cover</description>
					<width>{w}</width>
					<height>{h}</height>
					<animation effect="zoom" start="100" end="{SPOT_ZOOM}" center="auto" time="{SPOT_IN_MS}" tween="cubic" easing="out" condition="{SPOT}">Conditional</animation>
					<control type="group">
						<description>Copy of the selected cover (shown at once, gone at once: it travels with the frame)</description>
						<left>{tx}</left>
						<top>{t}</top>
						<width>{cw}</width>
						<height>{ch}</height>
						<visible>{SPOT}</visible>
						<control type="image">
							<left>{-x(pad)}</left>
							<top>{-pad + SHADOW_DROP}</top>
							<width>{cw + 2 * x(pad)}</width>
							<height>{ch + 2 * pad}</height>
							<texture border="32">kscape-shadow.png</texture>
						</control>
						<control type="image">
							<width>{cw}</width>
							<height>{ch}</height>
							<texture colordiffuse="{CARD}">kscape-white.png</texture>
						</control>
						<control type="textbox">
							<left>{x(12)}</left>
							<top>12</top>
							<width>{cw - x(24)}</width>
							<height>{ch - 24}</height>
							<align>center</align>
							<aligny>center</aligny>
							<font>kscape_small</font>
							<textcolor>FFC8C8D0</textcolor>
							<label>{spot('Property(text)')}</label>
						</control>
						<control type="image">
							<width>{cw}</width>
							<height>{ch}</height>
							<aspectratio>scale</aspectratio>
							<texture background="true">{spot('Art(poster)')}</texture>
						</control>
						<control type="image">
							<description>Floor reflection: the poster mirrored, fading out (kscape-reflect.png)</description>
							<top>{ch + 6}</top>
							<width>{cw}</width>
							<height>{int(ch * REFLECT_FRACTION / 0.45)}</height>
							<aspectratio>scale</aspectratio>
							<texture background="true" flipy="true" diffuse="kscape-reflect.png" colordiffuse="8CFFFFFF">{spot('Art(poster)')}</texture>
						</control>
						<control type="image">
							<description>Light glint: crosses the cover once when the spotlight comes on</description>
							<width>{cw}</width>
							<height>{ch}</height>
							<texture>kscape-gloss.png</texture>
							<animation effect="fade" start="0" end="100" delay="350" time="280" tween="sine" easing="out" reversible="false" condition="{SPOT}">Conditional</animation>
							<animation effect="fade" start="100" end="0" delay="700" time="450" tween="sine" easing="in" reversible="false" condition="{SPOT}">Conditional</animation>
						</control>
						<control type="grouplist">
							<left>{x(8)}</left>
							<top>{ch - BADGE_H - 8}</top>
							<width>{cw - 2 * x(8)}</width>
							<height>{BADGE_H}</height>
							<orientation>horizontal</orientation>
							<align>right</align>
							<itemgap>0</itemgap>
							<visible>{spot_has('badge')}</visible>
							<control type="button">
								<pulseonselect>false</pulseonselect>
								<width min="{x(BADGE_MIN_W)}" max="{cw - 2 * x(8)}">auto</width>
								<height>{BADGE_H}</height>
								<textoffsetx>{x(10)}</textoffsetx>
								<align>center</align>
								<aligny>center</aligny>
								<font>kscape_badge</font>
								<textcolor>{AMBER}</textcolor>
								<disabledcolor>{AMBER}</disabledcolor>
								<enable>false</enable>
								<texturenofocus border="2" colordiffuse="{AMBER}">kscape-badge-box.png</texturenofocus>
								<texturefocus border="2" colordiffuse="{AMBER}">kscape-badge-box.png</texturefocus>
								<label>{spot('Property(badge)')}</label>
							</control>
						</control>
						<control type="group">
							<left>{cw - x(HEART_BOX) - x(8)}</left>
							<top>8</top>
							<visible>{spot_has('fav')}</visible>
							<control type="image">
								<width>{x(HEART_BOX)}</width>
								<height>{HEART_BOX}</height>
								<texture colordiffuse="C8141210">kscape-white.png</texture>
							</control>
							<control type="image">
								<left>{(x(HEART_BOX) - x(HEART)) // 2}</left>
								<top>{(HEART_BOX - HEART) // 2 + 1}</top>
								<width>{x(HEART)}</width>
								<height>{HEART}</height>
								<texture colordiffuse="{AMBER}">kscape-heart.png</texture>
							</control>
						</control>
					</control>''']
    for n, (bx, by, bw, bh) in enumerate(bars):
        out.append(f'''					<control type="image" id="{1002 + n}">
						<left>{bx}</left>
						<top>{by}</top>
						<width>{bw}</width>
						<height>{bh}</height>
						<texture colordiffuse="{AMBER}">kscape-white.png</texture>
					</control>''')
    out.append('''				</control>
			</control>''')
    return '\n'.join(out)


def panel_width(L):
    return G.panel_w(L) - SPOT_GAP


def panel(L):
    """The classic panel (wallxml.panel) in smoked glass, with the clear logo above the
    synopsis when the film has one, and a synopsis that scrolls slowly through its lines when
    it is longer than them (only while the panel is up, so it costs nothing at rest)."""
    pw, ph = panel_width(L), G.panel_h(L)
    no_logo = f'String.IsEmpty(Container({SPOT_SRC}).ListItemAbsolute(0).Property(logo))'
    text = W.panel_text(L, pw)
    title = '<control type="label" id="1901">'
    if title in text:            # posters (albums keep a textbox title and no logo)
        text = text.replace(title, f'{title}\n\t\t\t\t\t<visible>{no_logo}</visible>', 1)
    body = '<control type="textbox" id="1902">'
    scroll = ('<autoscroll delay="4000" time="6000" repeat="9000">'
              '!String.IsEmpty(Window.Property(kscape.panel.open))</autoscroll>')
    text = text.replace(body, f'{body}\n\t\t\t\t\t{scroll}', 1)
    return f'''			<control type="group" id="1900">
				<description>Info panel in smoked glass beside the focused cover (placed by Python)</description>
				<left>-4000</left>
				<width>{pw}</width>
				<height>{ph}</height>
				<control type="grouplist">
					<description>Clipping box: the body slides into it from the cover's side</description>
					<width>{pw}</width>
					<height>{ph}</height>
					<orientation>vertical</orientation>
					<usecontrolcoords>true</usecontrolcoords>
					<itemgap>0</itemgap>
					<control type="group" id="1905">
						<description>Panel body: shown while Window.Property(kscape.panel.open) is set</description>
						<width>{pw}</width>
						<height>{ph}</height>
						<visible>!String.IsEmpty(Window.Property(kscape.panel.open))</visible>
{W.panel_animations()}
				<control type="image" id="1903">
					<description>Smoked glass: the theme's background at 90%</description>
					<width>{pw}</width>
					<height>{ph}</height>
					<texture colordiffuse="kscape_bg_shade">kscape-white.png</texture>
				</control>
				<control type="image">
					<description>Glow of the theme colour from the top</description>
					<width>{pw}</width>
					<height>{ph * 3 // 5}</height>
					<texture colordiffuse="kscape_blue_quiet">kscape-fade.png</texture>
				</control>
				<control type="image">
					<width>{pw}</width>
					<height>{ph}</height>
					<texture border="2" colordiffuse="30FFFFFF">kscape-glass-border.png</texture>
				</control>
				<control type="image">
					<width>{pw}</width>
					<height>3</height>
					<texture colordiffuse="kscape_blue">kscape-white.png</texture>
				</control>
				<control type="image" id="1906">
					<description>Clear logo in place of the title</description>
					<left>{x(34)}</left>
					<top>{L.frame + 10}</top>
					<width>{pw - 2 * x(34)}</width>
					<height>{LOGO_H}</height>
					<aspectratio align="left" aligny="center">keep</aspectratio>
					<fadetime>150</fadetime>
					<texture background="true">{spot('Property(logo)')}</texture>
					<visible>!{no_logo}</visible>
				</control>
{text}
					</control>
				</control>
			</control>'''


def bottom_fade(L):
    vw, vh = G.view_size(L)
    return f'''			<control type="image" id="1966">
				<description>Dark fade along the bottom of the view, under the counter</description>
				<top>{vh - FADE_H}</top>
				<width>{vw}</width>
				<height>{FADE_H}</height>
				<texture colordiffuse="kscape_bg_shade" flipy="true">kscape-fade.png</texture>
			</control>
'''


def count_label(cid=1965):
    """The counter as plain text on the bottom fade (window.py places it as the classic chip)."""
    label = '$INFO[Window.Property(kscape.count)]'
    return f'''		<control type="group" id="{cid}">
			<description>Item counter, plain text on the bottom fade</description>
			<animation effect="fade" start="0" end="100" time="250">Visible</animation>
			<visible>!String.IsEmpty(Window.Property(kscape.count))</visible>
			<control type="grouplist">
				<width>{np_chip.COUNT_W}</width>
				<height>{np_chip.COUNT_H}</height>
				<orientation>horizontal</orientation>
				<align>right</align>
				<usecontrolcoords>true</usecontrolcoords>
				<control type="label">
					<width>auto</width>
					<height>{np_chip.COUNT_H}</height>
					<aligny>center</aligny>
					<font>kscape_small</font>
					<textcolor>kscape_text_dim</textcolor>
					<shadowcolor>FF000000</shadowcolor>
					<label>{label}</label>
				</control>
			</control>
		</control>
'''


def build(L, sx=1.0):
    """The new wall's XML for layout `L` on a screen stretched by `sx`."""
    W.SX = sx
    try:
        return _build(L)
    finally:
        W.SX = 1.0


def _build(L):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- GENERATED by tools/gen_wall_xml.py from resources/lib/newwallxml.py ({L.name} covers, New wall test). Do not edit by hand. -->
<window>
	<defaultcontrol always="true">900</defaultcontrol>
	<controls>
		<control type="image">
			<width>{G.SCREEN_W}</width>
			<height>{G.SCREEN_H}</height>
			<texture colordiffuse="FF060607">kscape-white.png</texture>
		</control>
		<control type="button" id="900">
			<pulseonselect>false</pulseonselect>
			<description>Focus sink: the window handles all navigation itself</description>
			<left>-200</left>
			<top>-200</top>
			<width>1</width>
			<height>1</height>
			<texturefocus/>
			<texturenofocus/>
		</control>
{W.sources()}{spot_source()}		<control type="group" id="998">
			<description>Viewport: the screen, or a CinemaScope band (window.py places it)</description>
		<control type="group" id="1000">
			<description>Camera</description>
{W.slot(10000, L, badge=False, opening=True)}
{W.slot(20000, L, badge=False, opening=True)}
{backdrop(L)}
{focus_frame(L)}
{panel(L)}
		</control>
{bottom_fade(L)}		</control>
{W.masks()}
		<control type="image" id="1951">
			<description>KScape logo while the library loads: Python sets Window.Property(kscape.loading).</description>
			<left>360</left>
			<top>428</top>
			<width>1200</width>
			<height>225</height>
			<aspectratio>keep</aspectratio>
			<texture>kscape-logo.png</texture>
			<visible>!String.IsEmpty(Window.Property(kscape.loading))</visible>
			<animation effect="fade" start="0" end="100" delay="450" time="400">Visible</animation>
			<animation effect="fade" start="100" end="35" time="900" tween="sine" easing="inout" pulse="true" condition="!String.IsEmpty(Window.Property(kscape.loading))">Conditional</animation>
		</control>
		<control type="label" id="1950">
			<description>Status: loading, empty library, no favourites (two lines)</description>
			<left>260</left>
			<top>440</top>
			<width>1400</width>
			<height>200</height>
			<align>center</align>
			<aligny>center</aligny>
			<font>kscape_title</font>
			<textcolor>FFE6E6EA</textcolor>
			<wrapmultiline>true</wrapmultiline>
		</control>
{W.caption()}{count_label()}{np_chip.chip(cid=1980)}	</controls>
</window>
'''
