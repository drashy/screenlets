#!/usr/bin/env python
import gobject, time, gtk

def myFunc():
	print "myFunc was called"
	return True

timer = gobject.timeout_add( 1000, myFunc )

gtk.main()
