#!/usr/bin/env python

#
# HDUsageScreenlet - <http://ashysoft.blogspot.com/>
#
#	Copyright 2008 Paul Ashton
#
#	This file is part of HDUsageScreenlet.
#
#	HDUsageScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	HDUsageScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with HDUsageScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
# - Displays a simple HD usage meter
#
# TODO:
# - Hover to change % to space left
#
# DONE:
#



import gtk, screenlets
from screenlets.options import IntOption, StringOption, BoolOption, ColorOption, FontOption, ListOption
from screenlets.options import create_option_from_node
import cairo, pango, gobject, math, os, datetime



def niceSize( bytes ):
	if bytes < 1024: return "%s B" % bytes
	elif bytes < (1024 * 1024): return "%s KB" % (bytes / 1024)
	elif bytes < (1024 * 1024 * 1024): return "%.1f MB" % (bytes / 1024.0 / 1024.0)
	elif bytes < (1024 * 1024 * 1024 * 1024): return "%.2f GB" % (bytes / 1024.0 / 1024.0 / 1024.0)
	else: return "%.3f TB" % (bytes / 1024.0 / 1024.0 / 1024.0 / 1024.0)



def log(msg):
	print "(%s) %s" % (datetime.datetime.now(), msg)



class HDUsageScreenlet(screenlets.Screenlet):
	"""Displays a simple HD usage meter"""
	
	# default meta-info for Screenlets
	__name__ = 'HDUsageScreenlet'
	__version__ = '0.1'
	__author__ = '2007-2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__
	__requires__ = "0.0.12" #for mousex/y

	# internals
	__updateTimer = None
	__guiTimer = None
	p_layout = None
	devices = []
	dfInfo = []
	
	update_interval = 5000
	gui_update_interval = 1000
	mouseInside = False

	#version stuff
	__versionTimer = None
	version_interval = 10000
	checkVersion = True

	# settings
	rowWidth = 1
	deviceList = ["/::Boot"]
	realNames = False
	barHeight = 14
	barWidth = 150
	containerColor = [0.5,0.5,0.5,1.0]
	barColorBG = [0.3,0.3,0.3,1.0]
	barColorFG = [1.0,0.0,0.0,1.0]
	barColorFG2 = [1.0,1.0,0.0,1.0]
	textColor = [1.0,1.0,1.0,1.0]
	textFont = "Sans 8"
	hideErrors = True
	
	# constructor
	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=30, height=30, uses_theme=False, **keyword_args)

		self.add_menuitem("", str(self.__name__)+" v"+str(self.__version__)).set_sensitive(False)
		self.add_menuitem("","-")
		self.add_menuitem("website","Visit website")

		self.add_default_menuitems()
		self.add_options_group('HDUsage Options', 'HDUsage Options')
		#self.add_option(StringOption('HDUsage Options', 'deviceList', self.deviceList, 'Devices (see tooltip for info)', 'Semi-colon seperated list of devices to display ie: \'/;/sdb;/dev\'.\n\nYou can also give the devices a custom name by using a double-colon ie: \'/::My Main Drive\''),realtime=False)
		self.add_option(ListOption('HDUsage Options', 'deviceList', self.deviceList, 'Devices', 'You can also give the devices a custom name by using a double-colon ie: \'/::My Main Drive\''))
		self.add_option(IntOption('HDUsage Options', 'rowWidth', self.rowWidth, 'Bars per row', 'Display how many bars per row?',min=1,max=100))
		self.add_option(IntOption('HDUsage Options', 'barWidth', self.barWidth, 'Bar Width', 'How wide do you want the bars (default:200)',min=1,max=500),realtime=False)
		self.add_option(IntOption('HDUsage Options', 'barHeight', self.barHeight, 'Bar Height', 'How high do you want the bars (default:20)',min=1,max=500),realtime=False)
		self.add_option(BoolOption('HDUsage Options', 'realNames', self.realNames, 'Display Device Names?', 'Display device names instead of folder names'))
		self.add_option(BoolOption('HDUsage Options', 'hideErrors', self.hideErrors, 'Hide devices not found', 'Hide any device that is not found'))
		self.add_option(BoolOption('HDUsage Options', 'checkVersion', self.checkVersion, 'Startup version check?', 'When enabled will check for newer versions on startup.'))
		self.add_options_group('Appearance Options', 'Appearance Options')
		self.add_option(ColorOption('Appearance Options', 'containerColor', self.containerColor, 'Container Color', 'Color of the bar container'))
		self.add_option(ColorOption('Appearance Options', 'barColorBG', self.barColorBG, 'Bar Background Color', 'Color of the bars background'))
		self.add_option(ColorOption('Appearance Options', 'barColorFG', self.barColorFG, 'Bar Color 1', 'Color of the bar nearing 0%'))
		self.add_option(ColorOption('Appearance Options', 'barColorFG2', self.barColorFG2, 'Bar Color 2', 'Color of the bar nearing 100%'))
		self.add_option(ColorOption('Appearance Options', 'textColor', self.textColor, 'Text Color', 'Color of the text'))
		self.add_option(FontOption('Appearance Options', 'textFont', self.textFont, 'Text Font', 'Font used for the text'))

		self.update_interval = self.update_interval
		self.gui_update_interval = self.gui_update_interval
		self.version_interval = self.version_interval

	
	
	def on_init(self):
		if screenlets.VERSION < self.__requires__:
			log("%s requires Screenlets v%s, you have v%s, exiting.." % (self.__name__, self.__requires__, screenlets.VERSION))
			screenlets.show_error(self,"%s requires at least Screenlets v%s to function correctly.\nYou are currently running v%s, please upgrade your Screenlets package." % (self.__name__, self.__requires__, screenlets.VERSION))
			exit()

		self.updateDriveInfo()

		
	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "update_interval":
			self.__dict__['update_interval'] = value
			if self.__updateTimer: gobject.source_remove(self.__updateTimer)
			self.__updateTimer = gobject.timeout_add(value, self.updateDriveInfo)
			#log("Set '%s' to '%s'" % (name, value))
		if name == "gui_update_interval":
			self.__dict__['gui_update_interval'] = value
			if self.__guiTimer: gobject.source_remove(self.__guiTimer)
			self.__guiTimer = gobject.timeout_add(value, self.drawGUI)
			#log("Set '%s' to '%s'" % (name, value))
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
			ver = urllib.urlopen("http://www.meyitzo.pwp.blueyonder.co.uk/hdusage.txt").readline().strip()
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



	def getName(self, text):
		a = text.split("::")
		if len(a)>1: return a[1]
		else: return a[0]



	def getDev(self, text):
		return text.split("::")[0]



	def getInfo(self, req):
		for i in range(len(self.dfInfo)):
			line = self.dfInfo[i].strip().split(" ")
			for x in range(line.count("")): line.remove("")
			line.append(req)
			reqdev = self.getDev(req)
			if reqdev == line[0] or reqdev == line[5]:
				return line
		return ["%s" % reqdev, "", "", "", "-1%", "", "%s" % self.getName(req)]



	def updateDriveInfo(self):
		self.dfInfo = os.popen( "df -B 1 2>&1" ).readlines()

		self.devices = []
		for i in range(len(self.deviceList)):
			info = self.getInfo( self.deviceList[i] )
			if self.hideErrors and "-1%" in info[4]:
				continue
			self.devices.append( info )
		return True



	def drawGUI(self):
		self.redraw_canvas()
		return True



	def getTextSize( self, ctx, text, size ):
		ctx.save()
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)
		p_fdesc = pango.FontDescription(self.textFont)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_markup(text)
		ctx.restore()
		return self.p_layout.get_pixel_size()
		
		

	def drawText( self, ctx, x, y, text, size, rgba, align=0 ):
		ctx.save()
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)
		p_fdesc = pango.FontDescription(self.textFont)
		#p_fdesc.set_family_static()
		#p_fdesc.set_size(size*pango.SCALE)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_markup(text)
		ctx.set_source_rgba(rgba[0], rgba[1], rgba[2], rgba[3])
		if align:
			textSize = self.p_layout.get_pixel_size()
			self.textWidth = textSize[0]
			if align == 1: x = x - textSize[0]
			elif align == 2: x = x - textSize[0]/2
		ctx.translate(x, y)
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()



	def checkScreenletSize( self, size ):
		""" Checks screenlet size and if different resizes. """
		x = int(size[0])
		y = int(size[1])
		
		if x < 1 or y < 1:
			log("Invalid size %sx%s" % (x,y))
			return False
		
		#Both width and height need to change
		if x != self.width and y != self.height:
			log("Resizing screenlet to %sx%s" % (x,y))
			self.__dict__['width'] = x
			#self.width = x
			self.height = y
			return True

		#Only width needs to change
		if x != self.width:
			log("Resizing width to %s" % x)
			self.width = x
			return True

		#Only height needs to change
		if y != self.height:
			log("Resizing height to %s" % y)
			self.height = y
			return True
			
		return False
	


	def draw_round_rect( self, ctx, x, y, w, h, r=0, fill=True ):
		""" Draw a pretty rounded rectangle. """
		ctx.move_to( x, y+r )
		ctx.arc( x+r, y+r, r, 3.141, 4.712) #top left
		ctx.line_to( x-r+w, y )
		ctx.arc( x-r+w, y+r, r, 4.712, 0) #top right
		ctx.line_to( x+w, y-r+h )
		ctx.arc( x-r+w, y-r+h, r, 0, 1.570) #bottom right
		ctx.line_to( x+r, y+h )
		ctx.arc( x+r, y-r+h, r, 1.570, 3.141) #bottom left
		ctx.line_to( x, y+r )
		if fill: ctx.fill()
		else: ctx.stroke()
		


	def on_draw(self, ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_SOURCE)

		if( len(self.devices) < self.rowWidth ):
			w = len(self.devices)
			h = 1
		else:
			w = self.rowWidth
			h = int(math.ceil(float(len(self.devices))/float(self.rowWidth)))

		#Resize screenlet if necessary
		newWidth = 5 + ((self.barWidth+5)*w) * self.scale
		newHeight = 5 + ((self.barHeight+5)*h) * self.scale
		self.checkScreenletSize( [newWidth, newHeight] )

		#Background
		ctx.set_source_rgba(self.containerColor[0],self.containerColor[1],self.containerColor[2],self.containerColor[3])
		self.draw_round_rect( ctx, 0, 0, 5+(self.barWidth+5)*w, 5+(self.barHeight+5)*h, 5, True )

		#Bars
		x = y = 0
		for i in range(len(self.devices)):
			ctx.save()
			#ctx.translate( 5+(x*(self.barWidth+5)), 5+(y*(self.barHeight+5)) )
			xoffset = 5+(x*(self.barWidth+5))
			yoffset = 5+(y*(self.barHeight+5))

			#Draw background bar
			perc = (self.barWidth/100.0)*int(self.devices[i][4][:-1])
			ctx.set_source_rgba(self.barColorBG[0],self.barColorBG[1],self.barColorBG[2],self.barColorBG[3])
			self.draw_round_rect( ctx, xoffset, yoffset, self.barWidth, self.barHeight, 2, True )
			#ctx.rectangle(perc+xoffset, yoffset, self.barWidth-perc, self.barHeight)
			#ctx.fill()
			log("device = %s perc = %s" % (self.devices[i], perc) )
			#Draw foreground bar
			if perc > 0:
				#r = self.barColorFG[0] + (((self.barColorFG2[0]-self.barColorFG[0])/100.0)*perc)
				#g = self.barColorFG[1] + (((self.barColorFG2[1]-self.barColorFG[1])/100.0)*perc)
				#b = self.barColorFG[2] + (((self.barColorFG2[2]-self.barColorFG[2])/100.0)*perc)
				#a = self.barColorFG[3] + (((self.barColorFG2[3]-self.barColorFG[3])/100.0)*perc)
				
				r = ((self.barColorFG[0]/100.0)*(100.0-perc)) + ((self.barColorFG2[0]/100.0)*perc)
				g = ((self.barColorFG[1]/100.0)*(100.0-perc)) + ((self.barColorFG2[1]/100.0)*perc)
				b = ((self.barColorFG[2]/100.0)*(100.0-perc)) + ((self.barColorFG2[2]/100.0)*perc)
				a = ((self.barColorFG[3]/100.0)*(100.0-perc)) + ((self.barColorFG2[3]/100.0)*perc)
				ctx.set_source_rgba(r,g,b,a)
				self.draw_round_rect( ctx, xoffset, yoffset, perc, self.barHeight, 2, True )

			#Text
			if self.realNames:
				devName = self.devices[i][0]
			else:
				devName = self.getName(self.devices[i][6])
			if self.devices[i][4] == "-1%":
				devName = "%s not found" % devName
			
			textHeight = self.getTextSize( ctx, self.devices[i][0], 10 )[1]
			ty = (self.barHeight-textHeight)/2.0

			if self.mouseInside and self.mousex >= xoffset and self.mousex < xoffset+self.barWidth and self.mousey >= yoffset and self.mousey < yoffset+self.barHeight:
				self.drawText(ctx, self.barWidth-3+xoffset, ty+yoffset, "%s free" % niceSize(int(self.devices[i][3])), 10, self.textColor, 1 )
			else: 
				self.drawText(ctx, 3+xoffset, ty+yoffset, "%s" % devName, 10, self.textColor )

				if self.devices[i][4] != "-1%":
					self.drawText(ctx, self.barWidth-3+xoffset, ty+yoffset, "%s" % self.devices[i][4], 10, self.textColor, 1 )

			ctx.restore()
			x += 1
			if x >= self.rowWidth:
				x = 0
				y += 1



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

		ctx.set_source_rgba(1,1,1,1)
		ctx.rectangle(0, 0, self.width/self.scale, self.height/self.scale)
		ctx.fill()


# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(HDUsageScreenlet)

