# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime, timedelta

# Start must be in the format  dd month yyyy 23:59
startString = "14 August 2012 19:00"
startDateTime = datetime.strptime(startString, "%d %B %Y %H:%M")
startDate = startDateTime.date()

def daysToWeek(days):
	return int(days/7 +1)

def weekNum(timestamp, start=None):
	if not start:
		start = startDateTime
	
	if timestamp < start+timedelta(days=3): # first week deadline on the Friday
		return 0
	else:
		return daysToWeek((timestamp - start).days)

def gameWeek():
	return weekNum(timestamp=datetime.now())

def weekToDate(week):
	return startDateTime + timedelta(weeks=week-1)

if __name__ == "__main__":
	import sys
	print ("The current game week is", gameWeek())
	if len(sys.argv) > 1:
		print ("{0} is in game week".format(sys.argv[1]),
			   weekNum(datetime.strptime(sys.argv[1], "%d %B %Y %H:%M")))
