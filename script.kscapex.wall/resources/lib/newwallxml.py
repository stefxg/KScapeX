"""KScapeX "New wall test": the cover wall's XML in its new look (newwall.py drives it).

Built from the classic wall's pieces (wallxml.py), so both stay in step; the classic wall's XML
is not touched. What changes, against wallxml's control map:

  slots        no format badge (the selected cover shows it, in the spotlight): two controls
               and one condition fewer per slot, on every frame
  1992         hidden data list holding one item: the selected cover's poster, badge, favourite
               mark, text and clear logo (newwall.py sets them; no GUI lock)
  1001         focus frame, now also:
    1008         dimmer: darkens the whole wall behind the selected cover and its panel, while
                 Window.Property(kscape.spot) is set (it moves with the frame, so it is big
                 enough to cover the view from wherever the frame is)
    1010         spotlight: the frame's bars and a copy of the selected cover with a soft shadow;
                 zooms in (SPOT_ZOOM) while kscape.spot is set. The copy loads in the
                 background, like the slots: Kodi hands it the slot's texture, already loaded
  1900         info panel in smoked glass: translucent theme background, a glow and a line in the
               theme colour along the top, a thin outline; SPOT_GAP narrower than the classic
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
DIM = 'A6000000'                # the wall behind the spotlight: about two thirds darker
DIM_BOX = (-2200, -1300, 4600, 2700)     # (left, top, width, height) around the frame
SHADOW_PAD, SHADOW_DROP = 30, 12
FADE_H = 110                    # bottom fade under the counter
LOGO_H = 76


def spot(info):
    return f'$INFO[Container({SPOT_SRC}).ListItemAbsolute(0).{info}]'


def spot_has(name):
    return f'!String.IsEmpty(Container({SPOT_SRC}).ListItemAbsolute(0).Property({name}))'


def spot_source():
    return f'''		<control type="list" id="{SPOT_SRC}">
			<description>Data for the spotlight (newwall.py): the selected cover's poster, badge, mark, logo</description>
			<left>-4000</left>
			<top>-4000</top>
			<width>10</width>
			<height>10</height>
			<itemlayout width="10" height="10"/>
			<focusedlayout width="10" height="10"/>
		</control>
'''


def focus_frame(L):
    """The amber frame, the dimmer behind it and the spotlit copy of the selected cover."""
    t, tx = L.frame, G.fx(L)
    w, h = L.cover_w + 2 * tx, L.cover_h + 2 * t
    cw, ch = L.cover_w, L.cover_h
    bars = [(0, 0, w, t), (0, h - t, w, t), (0, t, tx, h - 2 * t), (w - tx, t, tx, h - 2 * t)]
    dl, dt, dw, dh = DIM_BOX
    pad = SHADOW_PAD
    out = [f'''			<control type="group" id="1001">
				<description>Focus frame, dimmer and spotlight (newwallxml)</description>
				<width>{w}</width>
				<height>{h}</height>
				<control type="image" id="1008">
					<description>Dimmer: the wall behind the spotlight</description>
					<left>{dl}</left>
					<top>{dt}</top>
					<width>{dw}</width>
					<height>{dh}</height>
					<texture colordiffuse="{DIM}">kscape-white.png</texture>
					<visible>{SPOT}</visible>
					<animation effect="fade" start="0" end="100" time="300">Visible</animation>
					<animation effect="fade" start="100" end="0" time="{SPOT_OUT_MS}">Hidden</animation>
				</control>
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
    synopsis when the film has one."""
    pw, ph = panel_width(L), G.panel_h(L)
    no_logo = f'String.IsEmpty(Container({SPOT_SRC}).ListItemAbsolute(0).Property(logo))'
    text = W.panel_text(L, pw)
    title = '<control type="label" id="1901">'
    if title in text:            # posters (albums keep a textbox title and no logo)
        text = text.replace(title, f'{title}\n\t\t\t\t\t<visible>{no_logo}</visible>', 1)
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
					<description>Smoked glass: the theme's background, translucent</description>
					<width>{pw}</width>
					<height>{ph}</height>
					<texture colordiffuse="kscape_bg_veil">kscape-white.png</texture>
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
{W.slot(10000, L, badge=False)}
{W.slot(20000, L, badge=False)}
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
