"""KScapeX "New wall test": the cover wall's XML in its new look (newwall.py drives it).

Flat by design. Versions 0.18 to 0.21 tried the opposite - a spotlight, drop shadows, a floor
reflection, polished glass, a sheet of plexiglas over the whole wall - and every one of them
fought the artwork: a wall of film posters is already saturated and high-contrast, so anything
laid on top competes with it instead of serving it. What is left carries hierarchy through
colour, weight and spacing alone: no gradient, no shadow, no reflection, no zoom. The amber
frame marks the selection, and the posters are the only thing on screen with any shine.

Built from the classic wall's pieces (wallxml.py), so both stay in step; the classic wall's XML
is not touched. What changes, against wallxml's control map:

  slots        no format badge (the selected cover shows its own, beside the panel): two
               controls and one condition fewer per slot, on every frame. They fade in once,
               column by column, when the window opens (wallxml.slot(opening=True); the
               kscape.opened property, set by newwall.py a moment later, keeps later
               activations from replaying it)
  1992         hidden data list holding one item: the selected film's clear logo, which the
               panel shows in place of its title (newwall.py sets it; no GUI lock)
  1001         focus frame: the classic one, four flat amber bars (wallxml.focus_frame).
               There is nothing behind the panel any more - no fanart, no veil, no scrim - so
               the wall itself stays visible, and the selected cover needs no second copy
               drawn over it
  1900         info panel: a solid dark panel (kscape_bg), nothing along its top, the film's
               clear logo in place of the title when the library has one
               (1901 hides while there is one), and a synopsis that scrolls through its lines
               when it is longer than them
  1965         the item counter as plain text, with no chip behind it

No <visible> tags on Python-driven controls: a visibility condition overrides setVisible().
"""
from . import geometry as G
from . import npchip as np_chip
from . import wallxml as W
from .wallxml import x

SPOT_SRC = 1992                 # the hidden list the panel reads the clear logo from
PANEL_BG = 'kscape_bg'          # solid, not glass: translucency is depth too
LOGO_H = 76


def spot(info):
    return f'$INFO[Container({SPOT_SRC}).ListItemAbsolute(0).{info}]'


def spot_source():
    return f'''		<control type="list" id="{SPOT_SRC}">
			<description>Data for the panel (newwall.py): the selected film's clear logo</description>
			<left>-4000</left>
			<top>-4000</top>
			<width>10</width>
			<height>10</height>
			<itemlayout width="10" height="10"/>
			<focusedlayout width="10" height="10"/>
		</control>
'''


def panel_width(L):
    """The classic width: nothing grows into the gap any more (no zoom on the cover)."""
    return G.panel_w(L)


def panel(L):
    """The classic panel (wallxml.panel), solid instead of glass, with the clear logo above the
    synopsis when the film has one, and a synopsis that scrolls slowly through its lines when it
    is longer than them (only while the panel is up, so it costs nothing at rest)."""
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
				<description>Info panel beside the focused cover (placed by Python)</description>
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
					<description>Solid panel, no gradient and no transparency</description>
					<width>{pw}</width>
					<height>{ph}</height>
					<texture colordiffuse="{PANEL_BG}">kscape-white.png</texture>
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


def count_label(cid=1965):
    """The counter as plain text (window.py places it as the classic chip)."""
    label = '$INFO[Window.Property(kscape.count)]'
    return f'''		<control type="group" id="{cid}">
			<description>Item counter, plain text</description>
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
{W.focus_frame(L)}
{panel(L)}
		</control>
		</control>
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
