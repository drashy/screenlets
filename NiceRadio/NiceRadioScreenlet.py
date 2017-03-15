#!/usr/bin/env python

#
# NiceRadioScreenlet - <http://ashysoft.wordpress.com/>
#
#	Copyright 2007-2008 Paul Ashton
#
#	This file is part of NiceRadioScreenlet.
#
#	NiceRadioScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	NiceRadioScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with NiceRadiogScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
#
# TODO:
#
# DONE:
#



import gtk, screenlets
from screenlets.options import IntOption, FloatOption, ColorOption, BoolOption, FontOption
from screenlets.options import create_option_from_node
import cairo, pango, gobject, re, os, math, datetime, time
import AshyMPlayer



def log(msg):
	print "(%s) %s" % (datetime.datetime.now(), msg)



class NiceRadioScreenlet(screenlets.Screenlet):
	"""A nice way to listen to net radio."""

	__name__ = 'NiceRadioScreenlet'
	__version__ = '0.1'
	__author__ = '2007-2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__

	# internals
	__updateTimer = None
	__guiTimer = None
	p_layout = None
	mplayer = None
	currentSong = ""
	text = ""
	textPos = 0
	textWidth = 0
	textHeight = 0
	textPause = 0
	textDirection = 0
	textSpeed = 2
	pauseTime = 20
	ctx = None
	mouseInside = False

	# menu
	menuStation = None
	menuStation_subMenu1 = None

	#version stuff
	__versionTimer = None
	version_interval = 10000
	checkVersion = True

	# settings
	gui_update_interval = 100
	update_interval = 1000
	bgColor = [1,0,0,1]
	lineColor = [0,1,0,1]
	font = "sans 8"
	draw_buttons = False #STUPID BUTTONS!!

	stations = [
					"mms://rdp.oninet.pt/antena3::Europe/Antena 3",
					"http://www.ministryofsound.com/asx/radio/mosRadio.asx::Europe/Ministry of Sound",
					"http://www.di.fm/mp3/vocaltrance.pls::DI.fm Vocal Trance",
					"http://www.di.fm/mp3/ambient.pls::DI.fm Ambient",
					"http://www.di.fm/mp3/electro.pls::DI.fm Electro House",
					"http://www.di.fm/mp3/harddance.pls::DI.fm Hard Dance",
					"http://www.sky.fm/mp3/tophits.pls::SKY.fm Top Hits",
					"mms://ftp.blueyonder.co.uk::Blueyonder"
					]



	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=200, height=20, uses_theme=True, **keyword_args)

		self.add_menuitem("", str(self.__name__)+" v"+str(self.__version__)).set_sensitive(False)
		self.add_menuitem("","-")
		self.add_menuitem("website","Visit website")

		self.add_menuitem("","-")
		self.menuStation = self.add_menuitem("", "Radio Stations")
		self.menuStation_subMenu1 = gtk.Menu()

		for a in range(len(self.stations)):
				item = gtk.MenuItem("%s" % self.stations[a].split("::")[1] )
				item.connect("activate", self.menuitem_callback, "open_%s" % a )
				item.show()
				self.menuStation_subMenu1.append(item)

		self.menuStation.set_submenu( self.menuStation_subMenu1 )

		#for a in range(len(self.stations)):
		#	self.add_menuitem("open_%s" % a, self.stations[a].split("::")[1])

		self.add_default_menuitems()
		self.add_options_group('NiceRadio Options', 'Options')
		self.add_option(ColorOption('NiceRadio Options', 'bgColor', self.bgColor, 'Background Color', ''))
		self.add_option(ColorOption('NiceRadio Options', 'lineColor', self.lineColor, 'Outline Color', ''))
		self.add_option(FontOption('NiceRadio Options', 'font', self.font, 'Font', 'Text font'))

		self.add_option(BoolOption('NiceRadio Options', 'checkVersion', self.checkVersion, 'Startup version check?', 'When enabled will check for newer versions on startup.'))



	def on_init(self):
		#start timers..
		self.gui_update_interval = self.gui_update_interval
		self.update_interval = self.update_interval
		self.version_interval = self.version_interval

		self.mplayer = AshyMPlayer.AshyMPlayer()
		#self.mplayer.openStream(self.stations[5].split("::")[0], self.stations[5].split("::")[1])



	def __setattr__(self, name, value):
		screenlets.Screenlet.__setattr__(self, name, value)
		if name == "gui_update_interval":
			self.__dict__['gui_update_interval'] = value
			if self.__guiTimer: gobject.source_remove(self.__guiTimer)
			self.__guiTimer = gobject.timeout_add(value, self.updateGUI)
		if name == "update_interval":
			self.__dict__['update_interval'] = value
			if self.__updateTimer: gobject.source_remove(self.__updateTimer)
			self.__updateTimer = gobject.timeout_add(value, self.updateInfo)
		if name == "version_interval":
			self.__dict__['version_interval'] = value
			if self.__versionTimer: gobject.source_remove(self.__versionTimer)
			self.__versionTimer = gobject.timeout_add(value, self.versionCheck)



	def on_menuitem_select (self, id):
		print id
		if "website" in id:
			self.openWebsite()
		elif "open_" in id:
			stationNum = int(id.split("open_")[1])
			self.mplayer.openStream( self.stations[stationNum].split("::")[0], self.stations[stationNum].split("::")[1] )



	def openWebsite(self):
		log("Opening browser..")
		import webbrowser
		webbrowser.open(self.__website__)



	def versionCheck(self):
		if not self.checkVersion: return False #These are not the droids you are looking for
		log("Checking for new version of %s.." % self.__name__)
		import urllib
		try:
			ver = urllib.urlopen("http://www.meyitzo.pwp.blueyonder.co.uk/niceradio.txt").readline().strip()
		except:
			log("Couldn't contact version server: %s" % ver)
			return False
		if len(ver) > 4:
			#Server had a cow?
			log("Bad response from version server: %s" % ver)
			return False
		if ver > self.__version__:
			log("%s v%s is available. (Currently running v%s)" % (self.__name__, ver, self.__version__))
			if screenlets.show_question(self, 'There is a newer version of %s available!\nDo you want to visit the website?' % self.__name__):
				self.openWebsite()
		else:
			log("You are running the latest version.")
		return False



	def updateGUI(self):
		self.redraw_canvas()
		return True



	def updateInfo(self):
		#Check for song changing..
		if self.currentSong != self.mplayer.currentSong:
			self.currentSong = self.mplayer.currentSong
			self.textPos = 0
			self.textPause = 0
			self.textDirection = 0

		if self.mplayer.status == "Playing":
			self.text = "Playing: %s" % self.mplayer.currentSong.replace("&", "&amp;")
		elif self.mplayer.status == "Error":
			self.text = "Error: %s" % self.mplayer.error
		else:
			self.text = self.mplayer.status

		extents = self.get_text_extents( self.ctx, self.text, self.font )
		self.textWidth = extents[2]
		self.textHeight = extents[3] - extents[1]

		return True



	def draw_rounded_rectangle(self, ctx, x, y, round, width, height):
		ctx.save()
		ctx.translate(x, y)

		ctx.move_to( 0, 0+round )
		ctx.arc( 0+round, 0+round, round, 3.141, 4.712) #top left
		ctx.line_to( 0-round+width, 0 )
		ctx.arc( 0-round+width, 0+round, round, 4.712, 0) #top right
		ctx.line_to( 0+width, 0-round+height )
		ctx.arc( 0-round+width, 0-round+height, round, 0, 1.570) #bottom right
		ctx.line_to( 0+round, 0+height )
		ctx.arc( 0+round, 0-round+height, round, 1.570, 3.141) #bottom left
		ctx.line_to( 0, 0+round )

		ctx.restore()



	def get_text_extents(self, ctx, text, font):
		"""Returns the pixel extents of a given text"""
		ctx.save()
		ctx.move_to(0,0)
		p_layout = ctx.create_layout()
		p_fdesc = pango.FontDescription(font)
		p_layout.set_font_description(p_fdesc)
		p_layout.set_text(text)
		extents, lextents = p_layout.get_pixel_extents()
		ctx.restore()
		return extents



	def drawText( self, ctx, x, y, text, font, align ):
		ctx.save()
		ctx.translate(x, y)

		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)

		p_fdesc = pango.FontDescription(font)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_alignment(align)
		self.p_layout.set_markup(text)

		ctx.show_layout(self.p_layout)
		ctx.restore()



	def draw_text(self, ctx, text, x, y,  font, size, width, allignment,ellipsize = pango.ELLIPSIZE_NONE):
		"""Draws text"""
		ctx.save()
		ctx.translate(x, y)
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)

		self.p_fdesc = pango.FontDescription()
		self.p_fdesc.set_family_static(font)
		self.p_fdesc.set_size(size * pango.SCALE)
		self.p_layout.set_font_description(self.p_fdesc)
		self.p_layout.set_width(width * pango.SCALE)
		self.p_layout.set_alignment(allignment)
		self.p_layout.set_ellipsize(ellipsize)
		self.p_layout.set_markup(text)
		ctx.show_layout(self.p_layout)
		ctx.restore()



	def on_draw(self, ctx):
		if not self.ctx: self.ctx = ctx

		#log("%s" % self.mplayer.currentSong)
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)

		ctx.save()
		ctx.set_line_width(1)

		#Draw background
		self.draw_rounded_rectangle(ctx, 0, 0, 5, self.width, self.height)
		ctx.set_source_rgba(self.bgColor[0],self.bgColor[1],self.bgColor[2],self.bgColor[3])
		ctx.fill_preserve()
		#and the outline
		ctx.set_source_rgba(self.lineColor[0],self.lineColor[1],self.lineColor[2],self.lineColor[3])
		ctx.stroke()

		#Text
		#self.draw_text(ctx, self.text, 5-self.textPos, (self.height-self.textHeight)/2.0, self.font, 8, -1, pango.ALIGN_LEFT)
		self.drawText( ctx, 5-self.textPos, 0, self.text, self.font, pango.ALIGN_LEFT )
		if self.textWidth > self.width:
			self.textPause += 1
			if self.textPause > self.pauseTime:
				if self.textDirection == 0:
					self.textPos += self.textSpeed
				else:
					self.textPos -= self.textSpeed
				if self.textPos > self.textWidth-self.width+10 or self.textPos <= 0:
					self.textDirection = 1-self.textDirection
					self.textPause = 0
		else:
			self.textPos = 0
			self.textDirection = 0

		if self.textPos > self.textWidth:
			self.textPos = 0
			self.textDirection = 0

		#print "textWidth:%s self.width:%s textPause:%s textPos:%s font:%s" % (self.textWidth, self.width, self.textPause, self.textPos, self.font)

		ctx.restore()



	def on_mouse_enter (self, event):
		self.mouseInside = True
		#self.gui_update_interval = 100
		pass

	def on_mouse_leave (self, event):
		self.mouseInside = False
		#self.gui_update_interval = 1000
		pass



	def on_draw_shape(self,ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		ctx.set_source_rgba(0,0,0,1)
		ctx.rectangle( 0, 0, self.width, self.height )
		ctx.fill()



if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(NiceRadioScreenlet)

