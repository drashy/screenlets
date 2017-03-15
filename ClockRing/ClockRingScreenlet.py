#!/usr/bin/env python

#
# ClockRingScreenlet - <http://ashysoft.wordpress.com/>
#
#	Copyright 2007-2008 Paul Ashton
#
#	This file is part of ClockRingScreenlet.
#
#	ClockRingScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	ClockRingScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with ClockRingScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
#
# TODO:
#
# DONE:
#



import gtk, screenlets
from screenlets.options import IntOption, FloatOption, ColorOption, BoolOption
from screenlets.options import create_option_from_node
import cairo, pango, gobject, re, os, math, datetime, time



def log(msg):
	print "(%s) %s" % (datetime.datetime.now(), msg)



class ClockRingScreenlet(screenlets.Screenlet):
	"""A ring to tell you the time."""
	
	# default meta-info for Screenlets
	__name__ = 'ClockRingScreenlet'
	__version__ = '0.3'
	__author__ = '2007-2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__

	# internals
	__updateTimer = None
	__guiTimer = None
	p_layout = None
	hour = 0
	mins = 0
	secs = 0

	#version stuff
	__versionTimer = None
	version_interval = 10000
	checkVersion = True

	# settings
	gui_update_interval = 1000 #ms
	hourColor = [1,0,0,1]
	minsColor = [0,1,0,1]
	secsColor = [0,0,1,1]
	hourBGColor = [0.5,0.5,0.5,1]
	minsBGColor = [0.5,0.5,0.5,1]
	secsBGColor = [0.5,0.5,0.5,1]
	size = 100
	thickness = 24.0
	ringSpacing = 26.0
	blockSpacing = 1.0
	hourMiddle = False
	allHours = False
	allMins = False
	allSecs = False
	offsetBlocks = False


	# constructor
	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=200, height=200, uses_theme=False, **keyword_args)

		self.add_menuitem("", str(self.__name__)+" v"+str(self.__version__)).set_sensitive(False)
		self.add_menuitem("","-")
		self.add_menuitem("website","Visit website")

		self.add_default_menuitems()
		self.add_options_group('ClockRing Options', 'Options')
		self.add_option(ColorOption('ClockRing Options', 'hourColor', self.hourColor, 'Hour Color', ''))
		self.add_option(ColorOption('ClockRing Options', 'minsColor', self.minsColor, 'Mins Color', ''))
		self.add_option(ColorOption('ClockRing Options', 'secsColor', self.secsColor, 'Secs Color', ''))

		self.add_option(ColorOption('ClockRing Options', 'hourBGColor', self.hourBGColor, 'Hour BG Color', ''))
		self.add_option(ColorOption('ClockRing Options', 'minsBGColor', self.minsBGColor, 'Mins BG Color', ''))
		self.add_option(ColorOption('ClockRing Options', 'secsBGColor', self.secsBGColor, 'Secs BG Color', ''))
		self.add_option(IntOption('ClockRing Options', 'size', self.size, 'Size', '', min=0, max=100))
		self.add_option(FloatOption('ClockRing Options', 'thickness', self.thickness, 'Ring Thickness', '',min=0.0, max=500.0, increment=0.1))
		self.add_option(FloatOption('ClockRing Options', 'ringSpacing', self.ringSpacing, 'Ring Spacing', '',min=0.0, max=500.0, increment=0.1))
		self.add_option(FloatOption('ClockRing Options', 'blockSpacing', self.blockSpacing, 'Block Spacing', '',min=0.0, max=6.0, increment=0.1))
		self.add_option(BoolOption('ClockRing Options', 'hourMiddle', self.hourMiddle, 'Put hours in middle of ring', ''))
		self.add_option(BoolOption('ClockRing Options', 'allHours', self.allHours, 'Light all hours', ''))
		self.add_option(BoolOption('ClockRing Options', 'allMins', self.allMins, 'Light all mins', ''))
		self.add_option(BoolOption('ClockRing Options', 'allSecs', self.allSecs, 'Light all secs', ''))
		self.add_option(BoolOption('ClockRing Options', 'offsetBlocks', self.offsetBlocks, 'Offset blocks', 'When enabled will align blocks with 0 degrees'))
		self.add_option(BoolOption('ClockRing Options', 'checkVersion', self.checkVersion, 'Startup version check?', 'When enabled will check for newer versions on startup.'))



	def on_init(self):
		self.updateClock()
		
		#start timers..
		self.gui_update_interval = self.gui_update_interval
		self.version_interval = self.version_interval



	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "gui_update_interval":
			self.__dict__['gui_update_interval'] = value
			if self.__guiTimer: gobject.source_remove(self.__guiTimer)
			self.__guiTimer = gobject.timeout_add(value, self.updateGUI)
		if name == "version_interval":
			self.__dict__['version_interval'] = value
			if self.__versionTimer: gobject.source_remove(self.__versionTimer)
			self.__versionTimer = gobject.timeout_add(value, self.versionCheck)



	def on_menuitem_select (self, id):
		if "website" in id:
			self.openWebsite()



	def openWebsite(self):
		log("Opening browser..")
		import webbrowser
		webbrowser.open(self.__website__)



	def versionCheck(self):
		if not self.checkVersion: return False #These are not the droids you are looking for
		log("Checking for new version of %s.." % self.__name__)
		import urllib
		try:
			ver = urllib.urlopen("http://www.meyitzo.pwp.blueyonder.co.uk/clockring.txt").readline().strip()
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
		self.updateClock()
		self.redraw_canvas()
		return True



	def updateClock(self):
		tempTime = time.localtime()
		self.hour = tempTime[3] % 12
		self.mins = tempTime[4]
		self.secs = tempTime[5]
		return True



	def on_draw(self, ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_ADD)

		ctx.save()
		startrad = self.size-(self.thickness/2.0)
		
		ctx.set_line_width( self.thickness )
		#Hour
		for i in range(12):
			if i == self.hour or (i<=self.hour and self.allHours): col = self.hourColor
			else: col = self.hourBGColor
			if self.hourMiddle: radius = startrad-(self.ringSpacing*2.0)
			else: radius = startrad
			if self.offsetBlocks:
				pos = -90+(self.blockSpacing/2.0)+(i*30)
			else:
				pos = -105+(self.blockSpacing/2.0)+(i*30)
			
			ctx.arc( 100, 100, radius, math.radians(pos), math.radians(pos+30-self.blockSpacing) )
			ctx.set_source_rgba(col[0],col[1],col[2],col[3])
			ctx.stroke()
		
		#mins
		for i in range(60):
			if i == self.mins or (i<=self.mins and self.allMins): col = self.minsColor
			else: col = self.minsBGColor
			if self.offsetBlocks:
				pos = -90+(self.blockSpacing/2.0)+(i*6)
			else:
				pos = -93+(self.blockSpacing/2.0)+(i*6)
			
			ctx.arc( 100, 100, startrad-self.ringSpacing, math.radians(pos), math.radians(pos+6-self.blockSpacing) )
			ctx.set_source_rgba(col[0],col[1],col[2],col[3])
			ctx.stroke()
		
		#secs
		for i in range(60):
			if i == self.secs or (i<=self.secs and self.allSecs): col = self.secsColor
			else: col = self.secsBGColor
			if self.hourMiddle: radius = startrad
			else: radius = startrad-(self.ringSpacing*2.0)
			if self.offsetBlocks:
				pos = -90+(self.blockSpacing/2.0)+(i*6)
			else:
				pos = -93+(self.blockSpacing/2.0)+(i*6)
			
			ctx.arc( 100, 100, radius, math.radians(pos), math.radians(pos+6-self.blockSpacing) )
			ctx.set_source_rgba(col[0],col[1],col[2],col[3])
			ctx.stroke()
		
		ctx.restore()

		

	def on_draw_shape(self,ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		ctx.set_source_rgba(0,0,0,1)
		ctx.arc( 100, 100, self.size-(self.thickness/2.0), math.radians(0), math.radians(360) )
		ctx.fill()

# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(ClockRingScreenlet)

