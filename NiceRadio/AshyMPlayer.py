import os, re, fcntl, gobject, time

class AshyMPlayer:
	stream = ""
	title = ""
	mpin = None
	mpout = None
	currentSong = ""
	timer = None
	status = "Idle"
	format = ""
	lastRemainder = ""
	active = False
	error = ""


	def __init__(self):
		pass



	def __del__(self):
		self.closeStream()
		self.close()



	def openStream(self, url, title):
		if self.active:
			print "Closing existing stream.."
			self.closeStream()

		self.stream = url
		self.title = title

		if ".ram" in self.stream or ".asx" in self.stream:
			cmd = "mplayer -slave -playlist %s" % self.stream
		else:
			cmd = "mplayer -slave %s" % self.stream

		print "Opening stream: %s (%s)" % (title, self.stream)
		self.mpin, self.mpout = os.popen4(cmd)
		fcntl.fcntl(self.mpout, fcntl.F_SETFL, os.O_NONBLOCK)
		self.active = True

		self.timer = gobject.timeout_add(1000, self.checkInput)



	def closeStream(self):
		self.mpin.close()
		self.mpout.close()
		self.active = False
		self.stream = ""
		self.title = ""



	def checkInput(self):
		if self.mpout:
			try:
				line = self.lastRemainder + self.mpout.read()
			except:
				return True

			if not line:
				return True

			#replace \r with \n
			line = line.replace("\r", "\n")
			#split lines by \n
			lines = line.split("\n")

			for line in lines:
				if "ICY Info:" in line:
					self.currentSong = re.findall("StreamTitle=\'(.*)\';StreamUrl", line)[0]
				elif "Connecting to server" in line:
					self.status = "Connecting.."
				elif "Starting playback..." in line:
					self.status = "Playing"
				elif "Cache fill:" in line:
					self.status = "Caching..."
				elif "file format detected." in line:
					self.format = re.findall("(.*) file format detected.", line)[0]
				elif "LoadLibrary failed to load" in line:
					self.status = "Error"
					self.error = line
				elif "Exiting..." in line:
					self.status = "Error"
					if not self.error:
						self.error = "Connection Closed"

			self.lastRemainder = lines[len(lines)-1]

		return True



	def sendCommand(self, command):
		if not self.mpin: return True

		if self.status == "Playing":
			self.mpin.write("%s\n" % command)
			self.mpin.flush()

			if "quit" in command:
				self.playing = False


	def close(self):
		print "Closing pipe.."
		try:
			self.mpout.close()
			self.mpin.close()
		except:
			pass






