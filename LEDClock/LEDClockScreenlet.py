#!/usr/bin/env python

#
# LEDClockScreenlet - <http://ashysoft.blogspot.com/>
#
#	Copyright 2007 Paul Ashton
#
#	This file is part of LEDClockScreenlet.
#
#	LEDClockScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	LEDClockScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with LEDClockScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
# - Displays a TIX-like clock on your desktop :)
#
# TODO:
#
# DONE:
# - User-defined colored blocks
#

import screenlets
from screenlets.options import BoolOption, IntOption, ColorOption, FloatOption
from screenlets.options import create_option_from_node
import cairo
import re, random, time
import gobject

class LEDClockScreenlet(screenlets.Screenlet):
	"""Displays a TIX-like clock on your desktop :)"""
	
	# default meta-info for Screenlets
	__name__ = 'LEDClockScreenlet'
	__version__ = '0.5'
	__author__ = '2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__

	# internals
	__timeout = None
	p_layout = None	
	timerReset = False
	currentTime = [ 0, 0, 0 ]


	# settings
	update_interval = 1
	shuffleLights = True
	twentyfourHours = True
	showSecs = True
	blockRoundness = 2
	
	bgColor = [ 1, 1, 1, 0.2 ]
	fgColor1 = [ 1, 0, 0, 0.7 ]
	fgColor2 = [ 0, 1, 0, 0.7 ]
	fgColor3 = [ 0, 0, 1, 0.7 ]

	blockShadow = True
	shadowColor = [ 0, 0, 0, 0.5 ]
	shadowOffset = 0.5
	allOneColor = False
	

	# constructor
	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=211, height=36, uses_theme=False, **keyword_args)

		self.add_default_menuitems()
		self.add_options_group('Appearance', 'Appearance Options')
		self.add_option(BoolOption('Appearance', 'shuffleLights', self.shuffleLights, 'Shuffle lights?', 'Do you want the lights shuffled?'))
		self.add_option(BoolOption('Appearance', 'twentyfourHours', self.twentyfourHours, '24 Hour mode?', '24 Hour or 12 Hour mode?'))
		self.add_option(BoolOption('Appearance', 'showSecs', self.showSecs, 'Show Seconds', 'Do you want seconds to display on your clock?'))
		self.add_option(IntOption('Appearance', 'blockRoundness', self.blockRoundness, 'Roundness', 'How round you want the blocks',min=0,max=5))

		#self.add_option(ColorOption('Appearance', 'fgColor', self.fgColor, 'Foreground Color', 'Color of the foreground blocks'))

		self.add_option(BoolOption('Appearance', 'blockShadow', self.blockShadow, 'Show Shadow', 'Display a shadow under blocks?'))
		self.add_option(ColorOption('Appearance', 'shadowColor', self.shadowColor, 'Shadow Color', 'Color of the shadow'))
		self.add_option(FloatOption('Appearance', 'shadowOffset', self.shadowOffset, 'Shadow Offset', 'Position of shadow',min=-2.0,max=2.0,increment=0.1))

		self.add_options_group('Colors', 'Appearance Options')
		self.add_option(BoolOption('Colors', 'allOneColor', self.allOneColor, 'All one color', 'Display all blocks in one color?'))
		self.add_option(ColorOption('Colors', 'fgColor1', self.fgColor1, '\'Hours\' Color', 'Color of the Hours blocks'))
		self.add_option(ColorOption('Colors', 'fgColor2', self.fgColor2, '\'Minutes\' Color', 'Color of the Minutes blocks'))
		self.add_option(ColorOption('Colors', 'fgColor3', self.fgColor3, '\'Seconds\' Color', 'Color of the Seconds blocks'))
		self.add_option(ColorOption('Colors', 'bgColor', self.bgColor, 'Background Color', 'Color of the background blocks'))

		self.update_interval = self.update_interval



	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "update_interval":
			if value > 0:
				self.__dict__['update_interval'] = value
				if self.__timeout: gobject.source_remove(self.__timeout)
				self.__timeout = gobject.timeout_add(int(value * 1000), self.updateClock)
			else:
				# TODO: raise exception!!!
				self.__dict__['update_interval'] = 1
				pass

		if name == "showSecs":
			self.updateClock()
			if value == True:
				self.update_interval = 1
			else:
				self.update_interval = 60-self.currentTime[2]
				self.timerReset = True



	def updateClock(self):
		if self.timerReset == True:
			self.update_interval = 60
			self.timerReset = False

		tempTime = time.localtime()
		if self.twentyfourHours: timeFormat = "%H"
		else: timeFormat = "%I"
		self.currentTime[0] = int(time.strftime(timeFormat, time.localtime()))
		self.currentTime[1] = tempTime[4]
		self.currentTime[2] = tempTime[5]
		self.redraw_canvas()
		return True



	def set_source_rgba_list( self, ctx, rgbaList ):
		""" Set color from a list/tuple. """
		t = type(rgbaList)
		if t == type([]) or t == type(()): #Make sure its a list/tuple
			ctx.set_source_rgba( rgbaList[0], rgbaList[1], rgbaList[2], rgbaList[3] )
		else:
			print "set_source_rgba_list: supplied object is not a list/tuple! (%s)" % t



	def block(self, ctx, number, color):
		#Draw the block..
		lightArray = [0, 0, 0, 0, 0, 0, 0, 0, 0]
		for i in range(0,number):
			lightArray[i] = 1

		if self.shuffleLights: random.shuffle( lightArray )
		
		for y in range(0,3):
			for x in range(0,3):
				ctx.save()
				#Shadow
				if self.blockShadow:
					ctx.set_operator(cairo.OPERATOR_OVER)
					self.set_source_rgba_list( ctx, self.shadowColor )
					self.draw_round_rect(ctx, x*11+self.shadowOffset, y*11+self.shadowOffset, 10, 10, self.blockRoundness )

				#Blocks					
				ctx.set_operator(cairo.OPERATOR_SOURCE)
				if lightArray[x+(y*3)]:
					self.set_source_rgba_list( ctx, color )
					self.draw_round_rect(ctx, x*11, y*11, 10, 10, self.blockRoundness )
				else:
					self.set_source_rgba_list( ctx, self.bgColor )
					self.draw_round_rect(ctx, x*11, y*11, 10, 10, self.blockRoundness )
				ctx.restore()
				
				
				
	def maketime(self, number):
		if number < 10:
			return [0, number]
		else:
			return [ int(str(number)[:1]), int(str(number)[1:]) ]



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
		ctx.set_operator(cairo.OPERATOR_OVER)
		ctx.save()
		ctx.translate( 2, 2 )
		
		#Do hours
		hours = self.maketime(self.currentTime[0])
		self.block( ctx, hours[0],self.fgColor1 )
		ctx.translate( 35, 0 )
		self.block( ctx, hours[1],self.fgColor1 )

		#Do mins
		if self.allOneColor: color = self.fgColor1
		else: color = self.fgColor2
		
		mins = self.maketime(self.currentTime[1])
		for i in range(0,2):
			ctx.translate( 35, 0 )
			self.block( ctx, mins[i],color )

		#Do Secs
		if self.allOneColor: color = self.fgColor1
		else: color = self.fgColor3
		
		if self.showSecs:
			secs = self.maketime(self.currentTime[2])
			for i in range(0,2):
				ctx.translate( 35, 0 )
				self.block( ctx, secs[i],color )

		ctx.restore()



	def on_draw_shape(self,ctx):
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		self.draw_round_rect( ctx, 0, 0, 10, 10 )

# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(LEDClockScreenlet)

