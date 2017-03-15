#!/usr/bin/env python

#
# NetmonScreenlet - <http://ashysoft.wordpress.com/>
#
#	Copyright 2007-2008 Paul Ashton
#
#	This file is part of NetmonScreenlet.
#
#	NetmonScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	NetmonScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with NetmonScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
# - Displays a nice bandwidth monitor
#
# TODO:
# - bandwidth stats with hourly, daily, weekly, monthly etc.
# - SNMP support
# - Alarm when hit a certain amount of data
# - automatic detection of available interfaces
# - smooth scaling changes
# - font options
#
# DONE:
# - Line graph
# - screenlet resizing
# - Graph height set to specific amount, 10meg etc.
#



import gtk, screenlets
from screenlets.options import BoolOption, ColorOption, StringOption, IntOption, FloatOption
from screenlets.options import create_option_from_node
import cairo, pango, gobject, re, os, math, datetime



def niceSpeed( bytes, mbit=False ):
	if mbit:
		bits = bytes * 8
		if bits < 1000: return "%s b" % bits
		elif bits < 1000000: return "%.1f Kb" % (bits / 1000.0)
		elif bits < 1000000000: return "%.2f Mb" % (bits / 1000000.0)
		elif bits < 1000000000000: return "%.3f Gb" % (bits / 1000000000.0)
		else: return "%.3f Tb" % (bits / 1000000000000.0)
	else:
		if bytes < 1024: return "%s B" % bytes
		elif bytes < (1024 * 1024): return "%.1f KB" % (bytes / 1024.0)
		elif bytes < (1024 * 1024 * 1024): return "%.2f MB" % (bytes / 1024.0 / 1024.0)
		elif bytes < (1024 * 1024 * 1024 * 1024): return "%.3f GB" % (bytes / 1024.0 / 1024.0 / 1024.0)
		else: return "%.3f TB" % (bytes / 1024.0 / 1024.0 / 1024.0 / 1024.0)



def log(msg):
	print "(%s) %s" % (datetime.datetime.now(), msg)



class NetmonScreenlet(screenlets.Screenlet):
	"""Shows a nice bandwidth graph on your desktop."""

	# default meta-info for Screenlets
	__name__ = 'NetmonScreenlet'
	__version__ = '0.2'
	__author__ = '2007-2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__
	__requires__ = "0.0.12"

	screenletWidth = 120

	# internals
	width1 = 120
	height1 = 50
	__updateTimer = None
	__guiTimer = None
	__saveTimer = None
	p_layout = None
	lastBytesReceived = 0
	lastBytesSent = 0
	__graphUp = [0 for x in range(width1/2+2)]
	__graphDown = [0 for x in range(width1/2+2)]
	firstRun = True
	__frame = 0
	graph_scale = 1
	deviceWarning = False
	mainInstance = False

	peak = 0
	averageUp = 0
	averageDown = 0
	totalSessionUp = 0
	totalSessionDown = 0
	todayUp = 0
	todayDown = 0
	stats = [0,0]

	#version stuff
	__versionTimer = None
	version_interval = 10000
	checkVersion = True

	# settings
	gui_update_interval = 200
	save_interval = 300000
	device_name = 'eth0'
	text_color = [1.0,1.0,1.0,1.0]
	down_color = [1.0,0.0,0.0,1.0]
	up_color = [0.0,1.0,0.0,1.0]
	back_color = [1.0,0.5,1.0,1.0]
	draw_textshadow = True
	draw_avgbars = True
	graphOverscale = 10
	graphScaleFixed = 0
	showBits = False
	lineGraph = True
	lineGraphFill = True
	lineWidth = 1
	showDownload = True
	showUpload = True


	#Texts...
	textTopLeft = ""
	textTopCenter = ""
	textTopRight = "%down% / %up%"

	textLeftTop = ""
	textLeftCenter = ""
	textLeftBottom = "%peak%"

	textBottomLeft = ""
	textBottomCenter = ""
	textBottomRight = ""

	textRightTop = ""
	textRightCenter = ""
	textRightBottom = ""




	# constructor
	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=self.screenletWidth, height=50, uses_theme=False, **keyword_args)

		self.add_menuitem("", str(self.__name__)+" v"+str(self.__version__)).set_sensitive(False)
		self.add_menuitem("","-")
		self.add_menuitem("website","Visit website")

		self.add_default_menuitems()
		self.add_options_group('Netmon Options', 'Netmon Options')
		self.add_option(StringOption('Netmon Options', 'device_name', self.device_name, 'Device Name', 'Your network device name (Default: eth0)'), realtime=False)
		self.add_option(IntOption('Netmon Options', 'width1', self.width1, 'Width', 'Width of the screenlet',min=10, max=1000),realtime=False)
		self.add_option(IntOption('Netmon Options', 'height1', self.height1, 'Height', 'Height of the screenlet',min=10, max=1000),realtime=False)
		self.add_option(BoolOption('Netmon Options', 'showDownload', self.showDownload, 'Show Download?', 'When enabled graph will show download data'))
		self.add_option(BoolOption('Netmon Options', 'showUpload', self.showUpload, 'Show Upload?', 'When enabled graph will show upload data'))
		self.add_option(ColorOption('Netmon Options', 'text_color', self.text_color, 'Text Color', 'Color of the text'))
		self.add_option(ColorOption('Netmon Options', 'down_color', self.down_color, 'Download Color', 'Color of the download graph'))
		self.add_option(ColorOption('Netmon Options', 'up_color', self.up_color, 'Upload Color', 'Color of the upload graph'))
		self.add_option(ColorOption('Netmon Options', 'back_color', self.back_color, 'Background Color', 'Color of the graph background'))
		self.add_option(BoolOption('Netmon Options', 'draw_textshadow', self.draw_textshadow, 'Text Shadow?', 'Apply a shadow to the text'))
		self.add_option(BoolOption('Netmon Options', 'draw_avgbars', self.draw_avgbars, 'Show average bars', 'Paints lines showing average down/upload'))

		self.add_options_group('More Netmon Options', 'More Netmon Options')
		self.add_option(IntOption('More Netmon Options', 'graphOverscale', self.graphOverscale, 'Graph Overscale Percent', 'Overscale the graph by this percentage',min=0, max=100))
		self.add_option(IntOption('More Netmon Options', 'graphScaleFixed', self.graphScaleFixed, 'Graph Scale (in bytes)', 'Scale of graph (bytes)\n125000 = 1 Megabit\n\nSet to zero for auto-scaling', min=0, max=1000000000000, increment=125000 ))
		self.add_option(BoolOption('More Netmon Options', 'showBits', self.showBits, 'Display bits', 'When enabled show amounts in bits instead of bytes'))
		self.add_option(BoolOption('More Netmon Options', 'lineGraph', self.lineGraph, 'Display as a Line Graph?', 'When enabled show graph in the form of a line'))
		self.add_option(BoolOption('More Netmon Options', 'lineGraphFill', self.lineGraphFill, 'Fill the Line Graph?', 'When enabled fill the graph with your chosen color'))
		self.add_option(IntOption('More Netmon Options', 'lineWidth', self.lineWidth, 'Line width', 'Adjusts the thickness of the line', min=0, max=5 ))
		self.add_option(BoolOption('More Netmon Options', 'checkVersion', self.checkVersion, 'Startup version check?', 'When enabled will check for newer versions on startup.'))

		self.add_options_group('Text Options', 'Available Options:\n%up%, %down%, %peak%, %scale%, %avgup%,\n%avgdown%, %sessup%, %sessdown%,\n%todayup%, %todaydown%')
		self.add_option(StringOption('Text Options', 'textTopLeft', self.textTopLeft, 'Top Left', ''))
		self.add_option(StringOption('Text Options', 'textTopCenter', self.textTopCenter, 'Top Center', 'Default: %down% / %up%'))
		self.add_option(StringOption('Text Options', 'textTopRight', self.textTopRight, 'Top Right', ''))
		self.add_option(StringOption('Text Options', 'textBottomLeft', self.textBottomLeft, 'Bottom Left', ''))
		self.add_option(StringOption('Text Options', 'textBottomCenter', self.textBottomCenter, 'Bottom Center', ''))
		self.add_option(StringOption('Text Options', 'textBottomRight', self.textBottomRight, 'Bottom Right', ''))
		self.add_option(StringOption('Text Options', 'textLeftTop', self.textLeftTop, 'Left Top', ''))
		self.add_option(StringOption('Text Options', 'textLeftCenter', self.textLeftCenter, 'Left Center', 'Default: %peak%'))
		self.add_option(StringOption('Text Options', 'textLeftBottom', self.textLeftBottom, 'Left Bottom', ''))
		self.add_option(StringOption('Text Options', 'textRightTop', self.textRightTop, 'Right Top', ''))
		self.add_option(StringOption('Text Options', 'textRightCenter', self.textRightCenter, 'Right Center', ''))
		self.add_option(StringOption('Text Options', 'textRightBottom', self.textRightBottom, 'Right Bottom', ''))




	def on_init(self):
		if screenlets.VERSION < self.__requires__:
			log("%s requires Screenlets v%s, you have v%s, exiting.." % (self.__name__, self.__requires__, screenlets.VERSION))
			screenlets.show_error(self,"%s requires at least Screenlets v%s to function correctly.\nYou are currently running v%s, please upgrade your Screenlets package." % (self.__name__, self.__requires__, screenlets.VERSION))
			exit()

		#Check we are the main instance
		if self.id == self.session.instances[0].id: self.mainInstance = True

		#start timers..
		self.gui_update_interval = self.gui_update_interval
		if self.mainInstance:
			self.save_interval = self.save_interval
			self.version_interval = self.version_interval


	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "gui_update_interval":
			self.__dict__['gui_update_interval'] = value
			if self.__guiTimer: gobject.source_remove(self.__guiTimer)
			self.__guiTimer = gobject.timeout_add(value, self.updateGUI)
		if name == "save_interval":
			self.__dict__['save_interval'] = value
			if self.__saveTimer: gobject.source_remove(self.__saveTimer)
			self.__saveTimer = gobject.timeout_add(value, self.saveStats)
		if name == "version_interval":
			self.__dict__['version_interval'] = value
			if self.__versionTimer: gobject.source_remove(self.__versionTimer)
			self.__versionTimer = gobject.timeout_add(value, self.versionCheck)
		if name == "width1":
			self.width = value
			self.__graphUp = [0 for x in range(self.width/2+2)]
			self.__graphDown = [0 for x in range(self.width/2+2)]
			log("Changed screenlet width to %s" % value)
		if name == "height1":
			self.height = value
		if name == "device_name":
			self.deviceWarning = False



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
			ver = urllib.urlopen("http://www.meyitzo.pwp.blueyonder.co.uk/netmon.txt").readline().strip()
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



	def saveStats(self):
		if self.stats[0]+self.stats[1] == 0:
			log("Not saving stats as nothing has changed.")
			return True

		date = str(datetime.datetime.now())[:10]
		filename = "%s/stats_%s.dat" % (self.get_screenlet_dir(),self.device_name)
		log("Saving stats to %s.." % filename)
		FILE = None

		if not os.path.exists(filename):
			log("%s does not exist, creating one.." % filename)
			FILE = open(filename,"w")
			today = [[ date, 0, 0 ]]
			FILE.write(str(today))
			FILE.close()
			log("%s created." % filename)

		try:
			FILE = open(filename,"r")
		except:
			log("Couldn't open %s for reading" % filename)
			return True

		if FILE:
			fileIn = FILE.read()
			FILE.close()

			lines = eval(fileIn)

			found = False
			for i in range(len(lines)):
				if date in lines[i]:
					#print "Found today: " + str(lines[i])
					lines[i][1] += self.stats[0]
					lines[i][2] += self.stats[1]
					self.todayDown = lines[i][1]
					self.todayUp = lines[i][2]
					log("Today stats: %s down, %s up" % (self.todayDown, self.todayUp))
					found = True
					break
			if not found:
				log("Didn't find today stats, adding today..")
				lines.append([ date, self.stats[0], self.stats[1] ])

		FILE = open(filename,"w")
		FILE.write(str(lines))
		FILE.close()
		self.stats = [0,0]
		return True



	def addStats(self, down, up):
		self.__graphDown.pop(0)
		self.__graphDown.append(down)
		self.__graphUp.pop(0)
		self.__graphUp.append(up)

		self.totalSessionDown += down
		self.totalSessionUp += up

		self.stats[0] += down
		self.stats[1] += up



	def updateInfo(self):
		devdata = os.popen( "cat /proc/net/dev | grep %s" % self.device_name ).readline()
		device = devdata[devdata.find(":")+1:] #get rid of anything before the colon
		device = re.findall("([\d]+)", device)

		#check the device exists :P
		if len(device) == 0:
			log("Device '%s' was not found" % self.device_name)
			if not self.deviceWarning:
				self.deviceWarning = True
				screenlets.show_error(self, 'The device \'%s\' was not found!\nPlease adjust your settings.' % self.device_name)
			return True

		self.deviceWarning = False

		downCounter = int(device[0])
		upCounter = int(device[8])

		if self.firstRun == True:
			self.firstRun = False
			self.lastBytesReceived = downCounter
			self.lastBytesSent = upCounter

		#Catch the bug with /proc/net/dev's 32bit byte counters *sigh*
		#FIXME - Not accurate, loses any bytes before we hit 32bit ceiling
		if downCounter < self.lastBytesReceived:
			self.lastBytesReceived = 0
			log("FIXME: /proc/net/dev 32bit counter bug (download)");
		if upCounter < self.lastBytesSent:
			self.lastBytesSent = 0
			log("FIXME: /proc/net/dev 32bit counter bug (upload)");

		downDiff = downCounter-self.lastBytesReceived
		upDiff = upCounter-self.lastBytesSent
		self.lastBytesReceived = downCounter
		self.lastBytesSent = upCounter

		self.addStats(downDiff,upDiff)

		if self.showUpload and self.showDownload:
			self.peak = max( max(self.__graphUp), max(self.__graphDown) )
		else:
			if self.showUpload:
				self.peak = max(self.__graphUp)
			else:
				self.peak = max(self.__graphDown)

		self.averageUp = int( sum(self.__graphUp)/len(self.__graphUp) )
		self.averageDown = int( sum(self.__graphDown)/len(self.__graphDown) )

		return True



	def getTextSize( self, ctx, text, size ):
		ctx.save()
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)
		p_fdesc = pango.FontDescription()
		p_fdesc.set_family_static("Free Sans")
		p_fdesc.set_size(size*pango.SCALE)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_markup(text)
		ctx.restore()
		return self.p_layout.get_pixel_size()



	def drawText( self, ctx, x, y, text, size, rgba, align=0, shadow=False ):
		ctx.save()
		if self.p_layout == None: self.p_layout = ctx.create_layout()
		else: ctx.update_layout(self.p_layout)
		p_fdesc = pango.FontDescription()
		p_fdesc.set_family_static("Free Sans")
		p_fdesc.set_size(size*pango.SCALE)
		self.p_layout.set_font_description(p_fdesc)
		self.p_layout.set_markup(text)
		textSize = self.p_layout.get_pixel_size()
		if align == 1: x = x - textSize[0]
		elif align == 2: x = x - textSize[0]/2
		if shadow:
			ctx.translate(x+0.5, y+0.5)
			ctx.set_source_rgba(0, 0, 0, rgba[3])
			ctx.show_layout(self.p_layout)
			ctx.fill()
			ctx.translate(-(x+1), -(y+1))
		ctx.translate(x, y)
		ctx.set_source_rgba(rgba[0], rgba[1], rgba[2], rgba[3])
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()



	def on_draw(self, ctx):
		self.__frame += 1
		if self.__frame > 4:
			self.__frame = 0
			self.updateInfo()

		if self.mainInstance:
			log("%s" % self.__graphDown)

		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)

		#Scale
		if self.graphScaleFixed: tempscale = self.graphScaleFixed
		else: tempscale = self.peak
		self.graph_scale = float((tempscale+(tempscale/100*self.graphOverscale))/self.height)

		#Stop div0 errors..
		if self.graph_scale == 0: self.graph_scale = 1

		#Draw background
		ctx.save()
		ctx.set_source_rgba(self.back_color[0],self.back_color[1],self.back_color[2],self.back_color[3])
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.fill()

		ctx.set_line_width( self.lineWidth )

		offset = -0.4*self.__frame
		ctx.translate( offset, 0 )

		if self.lineGraph:
			#Draw Download
			if self.showDownload:
				ctx.move_to( -2, self.height+2 ) #bottom left
				ctx.line_to( -2, self.height-int(self.__graphDown[0]/self.graph_scale) )
				for i in range(len(self.__graphDown)):
					height = int(self.__graphDown[i]/self.graph_scale)
					ctx.line_to( (i*2), self.height-height )
				ctx.line_to( self.width+4, self.height-height )
				ctx.line_to( self.width+2, self.height+2 ) #bottom right
				ctx.set_source_rgba(self.down_color[0],self.down_color[1],self.down_color[2],self.down_color[3])
				ctx.set_operator(cairo.OPERATOR_ADD)
				if self.lineGraphFill:
					ctx.stroke_preserve()
					ctx.set_source_rgba(self.down_color[0],self.down_color[1],self.down_color[2],self.down_color[3]/2)
					ctx.fill()
				else:
					ctx.stroke()

			#Draw Upload
			if self.showUpload:
				ctx.move_to( -1, self.height )
				ctx.line_to( -1, self.height-int(self.__graphUp[0]/self.graph_scale) )
				for i in range(len(self.__graphUp)):
					height = int(self.__graphUp[i]/self.graph_scale)
					ctx.line_to( i*2, self.height-height )
				ctx.line_to( self.width+2, self.height-height )
				ctx.line_to( self.width+2, self.height+2 ) #bottom right
				ctx.set_source_rgba(self.up_color[0],self.up_color[1],self.up_color[2],self.up_color[3])
				ctx.set_operator(cairo.OPERATOR_ADD)
				if self.lineGraphFill:
					ctx.stroke_preserve()
					ctx.set_source_rgba(self.up_color[0],self.up_color[1],self.up_color[2],self.up_color[3]/2)
					ctx.fill()
				else:
					ctx.stroke()
		else:
			if self.showDownload:
				#Draw Download
				ctx.set_operator(cairo.OPERATOR_SOURCE)
				for i in range(len(self.__graphDown)):
					height = int(self.__graphDown[i]/self.graph_scale)
					ctx.rectangle((i*2), self.height-height, 2, height)
				ctx.set_source_rgba(self.down_color[0],self.down_color[1],self.down_color[2],self.down_color[3])
				ctx.fill()

			if self.showUpload:
				#Draw Upload
				ctx.set_operator(cairo.OPERATOR_ADD)
				for i in range(len(self.__graphUp)):
					height = int(self.__graphUp[i]/self.graph_scale)
					ctx.rectangle((i*2), self.height-height, 2, height)
				ctx.set_source_rgba(self.up_color[0],self.up_color[1],self.up_color[2],self.up_color[3])
				ctx.fill()

		ctx.restore()

		#Draw average bars
		ctx.set_operator(cairo.OPERATOR_OVER)
		if self.draw_avgbars:
			if self.showDownload:
				ctx.set_source_rgba(self.down_color[0],self.down_color[1],self.down_color[2],self.down_color[3])
				ctx.rectangle(0, self.height-(self.averageDown/self.graph_scale), self.width, 1)
				ctx.fill()
			if self.showUpload:
				ctx.set_source_rgba(self.up_color[0],self.up_color[1],self.up_color[2],self.up_color[3])
				ctx.rectangle(0, self.height-(self.averageUp/self.graph_scale), self.width, 1)
				ctx.fill()

		#Draw top text
		if self.textTopLeft: self.drawText( ctx, 0, 0, self.fill_vars(self.textTopLeft), 8, self.text_color, 0, self.draw_textshadow )
		if self.textTopCenter: self.drawText( ctx, self.width/2, 0, self.fill_vars(self.textTopCenter), 8, self.text_color, 2, self.draw_textshadow )
		if self.textTopRight: self.drawText( ctx, self.width, 0, self.fill_vars(self.textTopRight), 8, self.text_color, 1, self.draw_textshadow )

		#Get text height
		h = self.getTextSize(ctx, "1234567890BMKGT", 8)[1]

		#Draw bottom text
		if self.textBottomLeft: self.drawText( ctx, 0, self.height-h, self.fill_vars(self.textBottomLeft), 8, self.text_color, 0, self.draw_textshadow )
		if self.textBottomCenter: self.drawText( ctx, self.width/2, self.height-h, self.fill_vars(self.textBottomCenter), 8, self.text_color, 2, self.draw_textshadow )
		if self.textBottomRight: self.drawText( ctx, self.width, self.height-h, self.fill_vars(self.textBottomRight), 8, self.text_color, 1, self.draw_textshadow )

		#Draw left text
		ctx.save()
		ctx.translate( 0, self.height )
		ctx.rotate( -1.57 ) #90 degrees ccw ;)
		if self.textLeftTop: self.drawText( ctx, self.height, 0, self.fill_vars(self.textLeftTop), 8, self.text_color, 1, self.draw_textshadow )
		if self.textLeftCenter: self.drawText( ctx, self.height/2, 0, self.fill_vars(self.textLeftCenter), 8, self.text_color, 2, self.draw_textshadow )
		if self.textLeftBottom: self.drawText( ctx, 0, 0, self.fill_vars(self.textLeftBottom), 8, self.text_color, 0, self.draw_textshadow )
		ctx.restore()

		#Draw right text
		ctx.save()
		ctx.translate( self.width, 0 )
		ctx.rotate( 1.57 ) #90 degrees cw ;)
		if self.textRightTop: self.drawText( ctx, 0, 0, self.fill_vars(self.textRightTop), 8, self.text_color, 0, self.draw_textshadow )
		if self.textRightCenter: self.drawText( ctx, self.height/2, 0, self.fill_vars(self.textRightCenter), 8, self.text_color, 2, self.draw_textshadow )
		if self.textRightBottom: self.drawText( ctx, self.height, 0, self.fill_vars(self.textRightBottom), 8, self.text_color, 1, self.draw_textshadow )
		ctx.restore()



	def on_draw_shape(self,ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		ctx.set_source_rgba(0,0,0,1)
		ctx.rectangle(0, 0, self.width, self.height)
		ctx.fill()



	def fill_vars(self, str):
		str = str.replace( "%up%", niceSpeed(self.__graphUp[len(self.__graphUp)-1], self.showBits) )
		str = str.replace( "%down%", niceSpeed(self.__graphDown[len(self.__graphDown)-1], self.showBits) )
		str = str.replace( "%peak%", niceSpeed(self.peak, self.showBits) )
		str = str.replace( "%scale%", niceSpeed(int(self.graph_scale*self.height), self.showBits) )
		str = str.replace( "%avgup%", niceSpeed(self.averageUp, self.showBits) )
		str = str.replace( "%avgdown%", niceSpeed(self.averageDown, self.showBits) )
		str = str.replace( "%sessup%", niceSpeed(self.totalSessionUp, self.showBits) )
		str = str.replace( "%sessdown%", niceSpeed(self.totalSessionDown, self.showBits) )
		str = str.replace( "%todayup%", niceSpeed(self.todayUp+self.stats[1], self.showBits) )
		str = str.replace( "%todaydown%", niceSpeed(self.todayDown+self.stats[0], self.showBits) )
		return str



	def on_quit(self):
		#Save the stats :)
		self.saveStats()
		return True



# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(NetmonScreenlet)

