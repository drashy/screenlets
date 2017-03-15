#!/usr/bin/env python

import os

def getDriveStats( path ):
	try:
		tempStats = os.statvfs( path )
	except OSError:
		return [path, 0, 0]
	# (bsize, frsize, blocks, bfree, bavail, files, ffree, favail, flag, namemax)

	print tempStats
	driveFree = tempStats.f_bsize * tempStats.f_bavail
	driveSize = tempStats.f_bsize * tempStats.f_blocks

	return [path, driveSize, driveFree]

print getDriveStats("/")
print getDriveStats("/dev/sda1")
