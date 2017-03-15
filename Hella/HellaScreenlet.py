#!/usr/bin/env python

#
# HellaScreenlet - <http://ashysoft.blogspot.com/>
#
#	Copyright 2007 Paul Ashton
#
#	This file is part of HellaScreenlet.
#
#	HellaScreenlet is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	HellaScreenlet is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with HellaScreenlet.  If not, see <http://www.gnu.org/licenses/>.
#
#
# INFO:
# - Screenlet interface to the excellent NZB leeching software, HellaNZB.
#
# TODO:
# - Start/Restart Hella
# - Click to change display MB<>ETA
# - Drag & Drop of NZB's
# - Queue list??
# - Nicer skins
# - Parsing of hellanzb.conf
# - - Check if NZB's are waiting
# - Speed limiting
# - Average Speed on 'Download Complete' popup
#
# DONE:
# - "Force" options
# - Nicer (ie. less fluctuating) ETA/Speed
# - added 'days' in eta
# - notifications of downloads complete
# - Pause
# - Cancel Current Download
# - Cancel all
#


import gtk, gtk.glade, screenlets, cairo, pango, gobject, re, os, random, xmlrpclib, sys
from screenlets.options import FloatOption, BoolOption, StringOption, create_option_from_node
from screenlets.utils import Notifier

def prettyEta(etaSeconds):
	days = int(etaSeconds / (60 * 60 * 24))
	hours = int((etaSeconds - (days * 60 * 60 *24)) / (60 * 60))
	minutes = int((etaSeconds - (days * 60 * 60 *24) - (hours * 60 * 60)) / 60)
	seconds = etaSeconds - (days * 60 * 60 *24) - (hours * 60 * 60) - (minutes * 60)
	if days:
		return '%dd %dh %dm %ds' % (days, hours, minutes, seconds)
	elif hours:
		return '%dh %dm %ds' % (hours, minutes, seconds)
	elif minutes:
		return '%dm %ds' % (minutes, seconds)
	else:
		return '%ds' % seconds



class HellaScreenlet(screenlets.Screenlet):
	"""Screenlet interface to the excellent NZB leeching software, HellaNZB."""
	
	# default meta-info for Screenlets
	__name__ = 'HellaScreenlet'
	__version__ = '0.7'
	__author__ = '2007-2008 Paul Ashton'
	__website__ = 'http://ashysoft.wordpress.com/'
	__desc__ = __doc__

	# internals
	__hellaTimer = None
	__guiTimer = None
	__textTimer = None
	__shutdownTimer = None
	p_layout = None
	etaShown = False
	server = None
	lastDownloads = []
	notes = Notifier()
	speedReadings = [0 for x in range(10)]

	# menu
	menuPause = None
	menuForce = None
	force_submenu = None
	menuQueue = None
	menuCancel = None
	menuCancel_current = None
	menuCancel_all = None

	# var backups
	lastPercDone = 0
	lastSize = 0
	lastName = ""
	lastQueued = None

	dispInfo = { "progress_mb":":Starting up", "percent_complete":"", "eta":"", "speed":"", "lines":["Please wait.."] }
	hellaInfo = { "currently_downloading":[], "currently_processing":[], "queued":[] }

	# settings
	HELLANZB_HOSTPORT = "localhost:8760"
	HELLANZB_PASSWORD = "changeme"
	hella_update_interval = 1
	text_update_interval = 5
	#conf_path = '/etc/hellanzb.conf'
	flashETA = True
	colorProgressBarText = (0.0, 0.0, 0.0, 1.0)
	colorBottomText = (1.0, 1.0, 1.0, 1.0)
	showNotifications = True
	shutdownIssued = False


	def makeMenus( self ):
		print "Making menus"
		#self.add_default_menuitems(DefaultMenuItem.XML)
		self.add_menuitem("", str(self.__name__)+" v"+str(self.__version__)).set_sensitive(False)
		self.add_menuitem("","-")

		self.menuPause = self.add_menuitem("pause", "Pause downloading")
		self.menuPause.set_sensitive(False)

		self.menuForce = self.add_menuitem("force", "Force")
		self.menuForce.set_sensitive(False)
		self.force_submenu = gtk.Menu()
		self.menuForce.set_submenu( self.force_submenu )

		self.menuCancel = self.add_menuitem("", "Cancel")
		self.menuCancel.set_sensitive(False)
		cancel_submenu = gtk.Menu()
		self.menuCancel.set_submenu( cancel_submenu )

		item = gtk.MenuItem("Current download")
		item.connect("activate", self.menuitem_callback, "cancel_current")
		item.show()
		cancel_submenu.append(item)

		item = gtk.MenuItem("All downloads")
		item.connect("activate", self.menuitem_callback, "cancel_all")
		item.show()
		cancel_submenu.append(item)

		self.add_menuitem("","-")

		self.add_menuitem("autoresume", "Auto Resume...")
		self.menuPause.set_sensitive(False)

		self.add_menuitem("shutdown", "Shutdown when done")
		
		self.updateForceMenu()



	def __init__(self, **keyword_args):
		screenlets.Screenlet.__init__(self, width=200, height=62,uses_theme=True, **keyword_args)
		self.theme_name = "default"

		self.makeMenus()

		self.add_default_menuitems()
		self.add_options_group('HellaScreenlet Options', 'HellaScreenlet Options')
		#self.add_option(StringOption('HellaScreenlet Options', 'conf_path', self.conf_path, '.conf path', 'Enter the path to your hellanzb.conf'), realtime=False)
		self.add_option(BoolOption('HellaScreenlet Options', 'flashETA', self.flashETA, 'ETA Display', 'Will display ETA as well as MB info'))
		self.add_option(BoolOption('HellaScreenlet Options', 'showNotifications', self.showNotifications, 'Show Notifications', 'Will alert you when downloads have completed'))

		self.add_options_group('HellaNZB Config', 'HellaNZB config options')
		self.add_option(StringOption('HellaNZB Config', 'HELLANZB_PASSWORD', self.HELLANZB_PASSWORD, 'XMLRPC Password', 'Can be found in your .conf file (Default: changeme)'), realtime=False)
		self.add_option(StringOption('HellaNZB Config', 'HELLANZB_HOSTPORT', self.HELLANZB_HOSTPORT, 'XMLRPC Host:Port', 'You should probably never need to change this but you can find the details in your .conf file (Usually: localhost:8760)'), realtime=False)

		self.hella_update_interval = self.hella_update_interval
		self.text_update_interval = self.text_update_interval



	def updateMenu( self ):
		#Pause menu..
		if self.hellaInfo["currently_downloading"]:
			#downloading
			if self.hellaInfo["is_paused"]: self.menuPause.get_child().set_label("Resume downloading")
			else: self.menuPause.get_child().set_label("Pause downloading")
			self.menuPause.set_sensitive(True)
			self.menuCancel.set_sensitive(True)
		else:
			#NOT downloading
			self.menuPause.get_child().set_label("Pause downloading")
			self.menuPause.set_sensitive(False)
			self.menuCancel.set_sensitive(False)
			
		#Update the "force" menu if needed
		if self.hellaInfo["queued"] != self.lastQueued:
			self.lastQueued = self.hellaInfo["queued"]
			self.updateForceMenu()



	def updateForceMenu( self ):
		#Force menu
		if self.hellaInfo["queued"]:
			self.menuForce.set_sensitive(True)
			self.menuForce.deselect()
			self.menuForce.remove_submenu()
			self.force_submenu.detach()
			self.force_submenu = gtk.Menu()
			for queueitem in self.hellaInfo["queued"]:
				item = gtk.MenuItem("(%s) %s" % (queueitem["id"],queueitem["nzbName"]) )
				item.connect("activate", self.menuitem_callback, "force_"+str(queueitem["id"]) )
				item.show()
				self.force_submenu.append(item)
			self.menuForce.set_submenu( self.force_submenu )
			
		else:
			self.menuForce.set_sensitive(False)



	def on_menuitem_select (self, id):
		print "menu item selected: "+str(id)
		if "pause" in id:
			if self.hellaInfo["is_paused"]:
				#TODO: Fix this when possible (bug in HellaNZB)
				#s = self.server.continue()
				s = os.popen( "hellanzb -c %s continue 2>&1" % self.hellaInfo["config_file"] ).readlines()
			else:
				s = self.server.pause()
		elif "cancel_current" in id:
			if screenlets.show_question(self, "Are you sure you want to cancel the current download?", "Confirm"):
				s = self.server.cancel()
				print "Cancelled current download"
		elif "cancel_all" in id:
			if screenlets.show_question(self, "Are you sure you want to cancel ALL downloads?", "Confirm"):
				s = self.server.clear(True)
				print "Cancelled ALL downloads"
		elif "force_" in id:
			#Force a specific ID to start downloading
			print "Forcing ID: %s" % id[6:]
			self.server.force(id[6:])
		elif "autoresume" in id:
			print "You selected auto-resume"
			resumeWindow = gtk.glade.XML("dialog.glade", "resumeWindow")
			resumeWindow.get_widget("hourspin").set_text("12")
			resumeWindow.get_widget("minspin").set_text("30")
			resumeWindow.signal_autoconnect( { "on_button1_clicked":self.bleh } )
		elif "shutdown" in id:
			print "Shutdown when done selected"
			#Get admin privileges
			os.system("gksudo -D HellaScreenlet echo HellaScreenlet >/dev/null")

			#Start shutdown gksudo ticker timer			
			if self.__shutdownTimer: gobject.source_remove(self.__shutdownTimer)
			self.__shutdownTimer = gobject.timeout_add(60000, self.shutdownTick) # 60 secs



	def shutdownTick(self):
		print "shutdownTick"
		os.system("gksudo echo HellaScreenlet shutdown tick >/dev/null")
		return True



	# attribute-"setter", handles setting of attributes
	def __setattr__(self, name, value):
		# call Screenlet.__setattr__ in baseclass (ESSENTIAL!!!!)
		screenlets.Screenlet.__setattr__(self, name, value)
		# check for this Screenlet's attributes, we are interested in:
		if name == "hella_update_interval":
			self.__dict__['hella_update_interval'] = value
			if self.__hellaTimer: gobject.source_remove(self.__hellaTimer)
			self.__hellaTimer = gobject.timeout_add(int(value * 1000), self.updateHella)
		if name == "text_update_interval":
			self.__dict__['text_update_interval'] = value
			if self.__textTimer: gobject.source_remove(self.__textTimer)
			self.__textTimer = gobject.timeout_add(int(value * 1000), self.updateText)



	def updateGUI(self):
		self.redraw_canvas()
		return True



	def updateText(self):
		if self.flashETA: self.etaShown = not self.etaShown
		return True



	def log(self, logThis):
		FILE = open("error.log","w")
		FILE.write(str(logThis))
		FILE.close()



	def updateHella(self):
		#Attempt connection to HellaNZB
		try:
			self.server = xmlrpclib.Server("http://hellanzb:%s@%s" % (self.HELLANZB_PASSWORD,self.HELLANZB_HOSTPORT));
			s = self.server.status()
		except:
			#Could not connect
			error = str(sys.exc_info()[0])
			if "socket.error" in error:
				print "*** ERROR: Seems HellaNZB is not running or HELLANZB_HOSTPORT is incorrect"
				self.dispInfo = { "progress_mb":":Error", "percent_complete":"", "eta":"", "speed":"",	"lines":["HellaNZB not running"] }
			elif "xmlrpclib.ProtocolError" in error:
				print "*** ERROR: HellaNZB is running but I can't connect to the XMLRPC server, probably a bad XMLRPC password"
				self.dispInfo = { "progress_mb":":Error: Can't connect to HellaNZB", "percent_complete":"", "eta":"", "speed":"",	"lines":["Check your XMLRPC password"] }
			else:
				print "*** ERROR: Couldn't open XMLRPC server connection: "+error
				self.dispInfo = { "progress_mb":":Error: Unknown error occured", "percent_complete":"", "eta":"", "speed":"",	"lines":["Please report error.log"] }
				self.log( error + str(self.hellaInfo) )
			self.hellaInfo = { "currently_downloading":[], "currently_processing":[] }
			self.redraw_canvas()
			return True
		
		# Create some lines to display..
		self.hellaInfo = s
		lines = []
		if s["currently_downloading"]:
			progress_mb = "%sMB of %sMB" % (s["currently_downloading"][0]["total_mb"]-s["queued_mb"],s["currently_downloading"][0]["total_mb"])
			lines.append("Dl: (%s) %s" % (str(s["currently_downloading"][0]["id"]),s["currently_downloading"][0]["nzbName"]))
		else:
			progress_mb = ""
		
		if s["currently_processing"]:
			lines.append("Pr: (%s) %s" % (str(s["currently_processing"][0]["id"]),s["currently_processing"][0]["nzbName"]))
		
		if s["queued"]:
			total = 0
			queueNum = 0
			for i in range(len(s["queued"])):
				if "total_mb" in s["queued"][i]:
					queueNum += 1
					total = total + s["queued"][i]["total_mb"]
			if queueNum:
				lines.append("Queue: %s items (%sMB)" % (queueNum,total))
		
		if not lines:
			if self.__shutdownTimer:
				if not self.shutdownIssued:
					os.system("gksudo 'shutdown -h +1' &")
					self.shutdownIssued = True
				lines.append("Shutdown issued (1 min)")
			else:
				lines.append("Idle")

		# Work out a nicer average speed/eta
		del self.speedReadings[0]
		self.speedReadings.append(int(s["rate"]))
		avgSpeed = 0
		num = 0
		for i in self.speedReadings:
			avgSpeed += i
			if i > 0: num += 1
		avgSpeed = avgSpeed / len(self.speedReadings)

		if num < len(self.speedReadings):
			eta = s["eta"]
			avgSpeed = s["rate"]
		else:
			eta = (int(s["queued_mb"])*1024)/avgSpeed

		# Make the display list
		self.dispInfo = {	"progress_mb": progress_mb,
					"percent_complete":"%s%%" % s["percent_complete"],
					"eta":"ETA: %s" % prettyEta(eta),
					"speed":"%sKB/s" % avgSpeed,
					"lines":lines
				}

		self.updateMenu()
		self.updateGUI()

		#Flash up a notification if needed..
		if self.showNotifications:
			log = s["log_entries"]
			for line in range(len(log)):
				if log[line].has_key("INFO") and "Finished processing" in log[line]["INFO"]:
					if not log[line]["INFO"] in self.lastDownloads:
						if len(self.lastDownloads) > 9: del self.lastDownloads[0]
						self.lastDownloads.append(log[line]["INFO"])
						filename = log[line]["INFO"][:int(log[line]["INFO"].find(": Finished processing"))]
						time = re.findall("\(total: ([\S\s]+)\)", log[line]["INFO"])[0]
						#if len(time) > 0: time = time[0][8:-1]
						#else: time = "Unknown"
						self.notes.notify("'%s' has finished downloading.\nTime taken: %s" % (filename,time), "Download Complete!", self.get_screenlet_dir()+"/icon.svg")

		self.redraw_canvas()
		return True



	def drawText( self, ctx, x, y, text, size, rgba, align ):
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
		if align == 1: x = x - textSize[0]
		elif align == 2: x = x - textSize[0]/2
		ctx.translate(x, y)
		ctx.show_layout(self.p_layout)
		ctx.fill()
		ctx.restore()



	def on_draw(self, ctx):
		if self.hellaInfo["currently_downloading"]: downloading = True
		else: downloading = False
		if self.hellaInfo["currently_processing"]: processing = True
		else: processing = False

		#Draw the background and perc bar..
		ctx.scale(self.scale, self.scale)
		ctx.set_operator(cairo.OPERATOR_OVER)
		if self.theme:
			ctx.save()
			#TODO: draw background in blocks and resize canvas
			ctx.translate(1, (12*len(self.dispInfo["lines"]))-24)
			self.theme.render(ctx, "hella-bottom")
			ctx.restore()
			self.theme.render(ctx, "hella-barempty")
			if downloading and self.hellaInfo["percent_complete"] > 0:
				ctx.save()
				ctx.rectangle(0, 0, int(float(self.hellaInfo["percent_complete"]/100.0)*200.0), 20)
				ctx.clip()
				self.theme['hella-barfull.svg'].render_cairo(ctx)
				ctx.restore()

		#MB & Perc text
		if downloading:
			if self.etaShown:
				mbText = self.dispInfo["eta"]
				percText = self.dispInfo["speed"]
				if self.hellaInfo["is_paused"]:
					mbText = "Paused"
					percText = ""
			else:
				mbText = self.dispInfo["progress_mb"]
				percText = self.dispInfo["percent_complete"]
		elif processing:
			mbText = "Processing..."
			percText = ""
		else:
			mbText = "Idle"
			if len(self.dispInfo["progress_mb"])>0 and self.dispInfo["progress_mb"][0] == ":": mbText = self.dispInfo["progress_mb"][1:]
			percText = ""

		self.drawText( ctx, 4, 4, mbText, 9, self.colorProgressBarText, 0 )
		self.drawText( ctx, 196, 4, percText, 9, self.colorProgressBarText, 1 )


		#Draw some text lines
		textPos = 0
		for line in self.dispInfo["lines"]:
			self.drawText( ctx, 4, 22+(textPos*13), line, 9, self.colorBottomText, 0 )
			textPos = textPos + 1



	def on_draw_shape(self,ctx):
		if self.theme:
			ctx.scale(self.scale, self.scale)
			ctx.set_operator(cairo.OPERATOR_OVER)
			self.theme.render(ctx, "hella-barfull")

# If the program is run directly or passed as an argument to the python
# interpreter then create a Screenlet instance and show it
if __name__ == "__main__":
	import screenlets.session
	screenlets.session.create_session(HellaScreenlet)

