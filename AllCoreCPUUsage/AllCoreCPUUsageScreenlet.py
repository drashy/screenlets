#!/usr/bin/env python

#
# AllCoreCPUUsageScreenlet - <http://ashysoft.blogspot.com/>
#
#	Copyright 2008 Paul Ashton
#
#	This file is part of AllCoreCPUUsageScreenlet.
#
#	AllCoreCPUUsageScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	AllCoreCPUUsageScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with AllCoreCPUUsageScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
# - Displays a simple cpu meter (ALL cores!)
#
# TODO:
# - Add 'All' meter
#
# DONE:
#



import gtk, screenlets
from screenlets.options import IntOption, BoolOption, ColorOption
from screenlets.options import create_option_from_node
import cairo, pango, gobject, math



class AllCoreCPUUsageScreenlet(screenlets.Screenlet):
	"""Displays a simple cpu meter"""
	
	# default meta-info for Screenlets
	__name__ = 'AllCoreCPUUsageScreenlet'
	__version__ = '0.4'
	__author__ = '2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__

	# internals
	__updateTimer = None
	p_layout = None
	cpuCount = 0
	cpu = None
	oldcpu = None
	cpuGraph = None

	# settings
	update_interval = 1 #secs
	style = 0
	rowWidth = 4
	zeroNaming = True
	showTextShadow = True
	textColor = [1,1,1,1]
	#showAllCPU = False
	
	#theme
	colorBorder = [0.5,0.5,0.5,0.5]
	colorFG = [0,0,0,0.3515]
	colorGraph = [0,1,0,1]
	colorText = [1,1,1,1]
	colorShadow = [0,0,0,1]



	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=50, height=50, uses_theme=True, **keyword_args)
		self.theme_name = "default"

		self.add_default_menuitems()
		self.add_options_group('Screenlet Options', 'Screenlet Options')
		self.add_option(IntOption('Screenlet Options', 'rowWidth', self.rowWidth, 'CPU\'s per row', 'Display how many CPU\'s per row?',min=1,max=500))
		self.add_option(IntOption('Screenlet Options', 'style', self.style, 'Style: Normal=0 Graph=1', 'Display style', min=0, max=1))
		self.add_option(BoolOption('Screenlet Options', 'zeroNaming', self.zeroNaming, 'Begin CPU Names at 0?', 'When disabled CPU names will begin at 1'))
		#self.add_option(BoolOption('Screenlet Options', 'showAllCPU', self.showAllCPU, 'Show overall CPU', 'Displays the overall CPU usage'))
		self.add_option(BoolOption('Screenlet Options', 'showTextShadow', self.showTextShadow, 'Text Shadow', 'Render text with a shadow'))
		
		self.add_options_group('Color Options', 'Color Options')
		self.add_option(ColorOption('Color Options', 'colorBorder', self.colorBorder, 'Border Color', ''))
		self.add_option(ColorOption('Color Options', 'colorFG', self.colorFG, 'Foreground Color', ''))
		self.add_option(ColorOption('Color Options', 'colorText', self.colorText, 'Text Color', ''))
		self.add_option(ColorOption('Color Options', 'colorShadow', self.colorShadow, 'Text Shadow Color', ''))
		self.add_option(ColorOption('Color Options', 'colorText', self.colorText, 'Text Color', 'Render text with this color'))

		self.cpuCount = self.CountCPUs()
		self.cpu = [0 for x in range(self.cpuCount)]
		self.oldcpu = [0 for x in range(self.cpuCount)]
		self.cpuGraph = [[0,0,0,0,0,0,0,0,0,0] for x in range(self.cpuCount) ]

		self.update_interval = self.update_interval



	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "update_interval":
			self.__dict__['update_interval'] = value
			if self.__updateTimer: gobject.source_remove(self.__updateTimer)
			self.__updateTimer = gobject.timeout_add(value * 1000, self.updateGUI)



	def CountCPUs(self):
		f = open("/proc/stat", "r")
		s = f.readlines()
		f.close()

		cpuCount = 0
		for i in s:
			if "cpu" in i:
				cpuCount += 1
		return cpuCount-1
		


	def updateGUI(self):
		f = open("/proc/stat", "r")
		s = f.readlines()
		f.close()
		for i in range(len(self.cpu)):
			self.cpu[i] = 0 

		for i in s:
			if "cpu" in i: #check for cpu line
				info = i.strip().split(" ")
				if info[0] == "cpu" and info[1] == "": #skip 'overall' cpu usage
					continue
				cpuNum = int(info[0][3:]) #get cpu number
				if cpuNum < len(self.cpu):
					if self.cpu[cpuNum] > 100: self.cpu[cpuNum]=100
					if self.cpu[cpuNum] < 0: self.cpu[cpuNum]=0
					if self.style == 1: #Graph style
						self.cpuGraph[cpuNum].pop(0) # get rid of old value
						self.cpuGraph[cpuNum].append( int(info[1]) + int(info[3]) - self.oldcpu[cpuNum] ) #add new one
					self.cpu[cpuNum] = int(info[1]) + int(info[3]) - self.oldcpu[cpuNum]
					self.oldcpu[cpuNum] = int(info[1]) + int(info[3]) #save value for next time

		self.redraw_canvas()
		return True



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



	def checkScreenletSize( self, size ):
		""" Checks screenlet size and if different resizes. """
		x = int(size[0])
		y = int(size[1])
		
		if x < 1 or y < 1:
			print "Invalid size %sx%s" % (x,y)
			return False
		
		#Both width and height need to change
		if x != self.width and y != self.height:
			print "Resizing screenlet to %sx%s" % (x,y)
			self.__dict__['width'] = x
			#self.width = x
			self.height = y
			return True

		#Only width needs to change
		if x != self.width:
			print "Resizing width to %s" % x
			self.width = x
			return True

		#Only height needs to change
		if y != self.height:
			print "Resizing height to %s" % y
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

		if( self.cpuCount < self.rowWidth ):
			w = self.cpuCount
			h = 1
		else:
			w = self.rowWidth
			h = int(math.ceil(float(self.cpuCount)/float(self.rowWidth)))

		#Resize screenlet if necessary
		self.checkScreenletSize( ((5+(w*45)) * self.scale, (5+(h*45)) * self.scale) )

		if self.theme:
			#Background
			ctx.set_source_rgba(self.colorBorder[0],self.colorBorder[1],self.colorBorder[2],self.colorBorder[3])
			self.draw_round_rect( ctx, 0, 0, 5+(w*45), 5+(h*45), r=5, fill=True )

			if self.style==1:
				#Graph style
				x = y = 0
				for i in range(self.cpuCount):
					ctx.save()
					#Graph bg
					ctx.set_source_rgba(self.colorFG[0],self.colorFG[1],self.colorFG[2],self.colorFG[3])
					self.draw_round_rect( ctx, 5+(x*45), 5+(y*45), 40, 40, 5, True )
					
					#Graph fg
					ctx.save()
					ctx.translate( 5+(x*45), 5+(y*45) )
					for g in range(len(self.cpuGraph[i])):
						ctx.rectangle(g*4, 40-float(self.cpuGraph[i][g]/100.0)*40.0, 4, 41)
					ctx.clip()
					self.theme['cpu_fill.svg'].render_cairo(ctx)
					#self.draw_round_rect( ctx, 5+(x*45), 5+(y*45), 40, 40, 5, True )
					ctx.restore()

					cpuName = i
					if not self.zeroNaming: cpuName += 1
					
					if self.showTextShadow:
						self.drawText(ctx, 5+(x*45)+21, 5+(y*45)+6, "CPU%d" % cpuName, 7, self.colorShadow, 2 )
						self.drawText(ctx, 5+(x*45)+21, 5+(y*45)+21, "%s%%" % self.cpu[i], 9, self.colorShadow, 2 )
		
					self.drawText(ctx, 5+(x*45)+20, 5+(y*45)+5, "CPU%d" % cpuName, 7, self.colorText, 2 )			
					self.drawText(ctx, 5+(x*45)+20, 5+(y*45)+20, "%s%%" % self.cpu[i], 9, self.colorText, 2 )
					ctx.restore()
					x += 1
					if x >= self.rowWidth:
						x = 0
						y += 1
			else:
				#Digital style
				x = 0
				y = 0
				for i in range(self.cpuCount):
					ctx.save()
					#Graph bg
					thisx = 5+(x*45)
					thisy = 5+(y*45)
					ctx.set_source_rgba(self.colorFG[0],self.colorFG[1],self.colorFG[2],self.colorFG[3])
					self.draw_round_rect( ctx, thisx, thisy, 40, 40, 5, True )
					
					#Graph fg
					if self.cpu[i]:
						ctx.save()
						ctx.translate( thisx, thisy )
						ctx.rectangle(0, 40-float(self.cpu[i]/100.0)*40.0, 40, 41)
						ctx.clip()
						self.theme['cpu_fill.svg'].render_cairo(ctx)
						ctx.restore()
						
					cpuName = i
					if not self.zeroNaming: cpuName += 1
					
					if self.showTextShadow:
						self.drawText(ctx, thisx+21, thisy+6, "CPU%d" % cpuName, 7, self.colorShadow, 2 )
						self.drawText(ctx, thisx+21, thisy+21, "%s%%" % self.cpu[i], 9, self.colorShadow, 2 )
		
					self.drawText(ctx, thisx+20, thisy+5, "CPU%d" % cpuName, 7, self.colorText, 2 )			
					self.drawText(ctx, thisx+20, thisy+20, "%s%%" % self.cpu[i], 9, self.colorText, 2 )
					ctx.restore()
					x += 1
					if x >= self.rowWidth:
						x = 0
						y += 1



	def on_draw_shape(self,ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		if self.theme:
			ctx.set_source_rgba(1,1,1,1)
			ctx.rectangle(0, 0, self.width, self.height)
			ctx.fill()


# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(AllCoreCPUUsageScreenlet)

