#!/usr/bin/env python

#
# ScrollyRSSScreenlet - <http://ashysoft.blogspot.com/>
#
#	Copyright 2007-2008 Paul Ashton
#
#	This file is part of ScrollyRSSScreenlet.
#
#	ScrollyRSSScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	ScrollyRSSScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with ScrollyRSSScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
# - Displays a scrolly RSS feed
#
# TODO:
#
# DONE:
#



import gtk, screenlets, feedparser
from screenlets.options import BoolOption, ColorOption, StringOption, IntOption
from screenlets.options import create_option_from_node
import cairo, pango, gobject, re, os, math, datetime



class ScrollyRSSScreenlet(screenlets.Screenlet):
	"""Displays a scrolly RSS feed"""
	
	# default meta-info for Screenlets
	__name__ = 'ScrollyRSSScreenlet'
	__version__ = '0.1'
	__author__ = 'Paul Ashton (c) 2007-2008'
	__website__ = 'http://ashysoft.blogspot.com/'
	__desc__ = __doc__

	# internals
	__updateTimer = None
	__guiTimer = None
	p_layout = None
	feedText = ""
	xPos = 0
	textWidth = 0

	# settings
	update_interval = 60 * 5 #secs
	gui_update_interval = 50 #ms
	feedURL = "http://newsrss.bbc.co.uk/rss/newsonline_uk_edition/front_page/rss.xml"

	d = None
	#feedparser.parse("")
	#print str(len(d["entries"]))+" entries"
	#feedText = ""
	#for i in range(len(d["entries"])):
	#	feedText += "   -   " + d["entries"][i]["title"] + ""
	#print feedText

	# constructor
	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=200, height=50, uses_theme=False, **keyword_args)

		self.add_default_menuitems()
		#self.add_options_group('Netmon Options', 'Netmon Options')
		#self.add_option(IntOption('Netmon Options', 'screenletWidth', self.screenletWidth, 'Screenlet Width', 'Width of the screenlet in pixels',min=1,max=4096,increment=2), realtime=False)

		self.updateRSS()

		self.gui_update_interval = self.gui_update_interval
		self.update_interval = self.update_interval



	# attribute-"setter", handles setting of attributes
	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "gui_update_interval":
			self.__dict__['gui_update_interval'] = value
			if self.__guiTimer: gobject.source_remove(self.__guiTimer)
			self.__guiTimer = gobject.timeout_add(value, self.updateGUI)
		if name == "update_interval":
			self.__dict__['update_interval'] = value
			if self.__updateTimer: gobject.source_remove(self.__updateTimer)
			self.__updateTimer = gobject.timeout_add(value * 1000, self.updateRSS)



	def updateRSS(self, ctx):
		print "updateRSS()"
		self.rssFeed = feedparser.parse(self.feedURL)
		print str(len(self.rssFeed["entries"]))+" entries found in feed"
		self.feedText = []
		for i in range(len(self.rssFeed["entries"])):
			item = [self.rssFeed["entries"][i]["title"],self.getTextSize( ctx, self.rssFeed["entries"][i]["title"], 10 )]
			self.feedText.append(item)



	def updateGUI(self):
		self.redraw_canvas()
		return True



	def getTextSize( self, ctx, text, size ):
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)
		p_fdesc = pango.FontDescription()
		p_fdesc.set_family_static("Free Sans")
		p_fdesc.set_size(size*pango.SCALE)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_markup(text)

		textSize = self.p_layout.get_pixel_size()
		return textSize[0]



	def drawText( self, ctx, x, y, text, size, rgba, align=0 ):
		ctx.save()
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)
		p_fdesc = pango.FontDescription()
		p_fdesc.set_family_static("Free Sans")
		p_fdesc.set_size(size*pango.SCALE)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_markup(text)
		ctx.set_source_rgba(rgba[0], rgba[1], rgba[2], rgba[3])
		textSize = self.p_layout.get_pixel_size()
		self.textWidth = textSize[0]
		if align == 1: x = x - textSize[0]
		elif align == 2: x = x - textSize[0]/2
		ctx.translate(x, y)
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()



	def on_draw(self, ctx):
		self.ctx = ctx
		self.xPos -= 1
		if self.xPos < -self.textWidth:
			self.xPos = self.width

		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		#Draw background
		ctx.save()
		ctx.set_source_rgba(1,1,1,0.5)
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.fill()
		self.drawText(ctx, self.xPos, 0, self.feedText, 10, [1,1,1,1] )


	def on_draw_shape(self,ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		ctx.set_source_rgba(0,0,0,1)
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.fill()

# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(ScrollyRSSScreenlet)

