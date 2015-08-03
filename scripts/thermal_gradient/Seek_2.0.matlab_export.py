###########################################################################
#
# Program by Cynfab, available from
# http://www.eevblog.com/forum/testgear/yet-another-cheap-thermal-imager-incoming/msg571129/#msg571129
# Tweaks made by David Tulloh to generate vars.mat on pushing Snapshot button
#
# This is a program to read thermal image data from the Seek PIR206 Thermal Camera
# It operates more or less in real time (if your platform is fast enough), since
# it is in python, don't expect it to run in real time on anything less than an i7.
# Someday, I may port it to C (and daresay C++) to improve the rate on other platforms.
# OpenCV will be useful here (I hope I live that long ;>))
#
# It can save a snapshot of the current raw image, cal image and colorized image
# Sorry, the file names are hardcoded...
# It supports several palettes, more are easily added in colorscale.py
# If you like Iron, BlackHot or WhiteHot, you are golden. I included RedGreen
# because "we're all in this together"
# just so you would have an excuse to change it to something like RainBow,
# which is in colorscale.py and should be trivial to enable.
#
# You will need to have python 2.7 (3+ may work, not tried)
# and PyUSB 1.0 (needs to be gotten as source from Github and installed as root)
# and PIL (Pillow fork, often in debian distros)
# and numpy (often in debian base distros)
# and scipy
# and Tkinter
# and ImageTk (part of Pillow but a seperate module)
# and maybe some other stuff like colorscale.py (see below)
#
# You will probably have to run this as root unless you get your udev/mdev rules
# set up to allow the Seek device to be used by other than root.
#
# Many thanks to the folks at eevblog, especially (in no particular order) 
#   miguelvp, marshallh, mikeselectricstuff, sgstair, Fry-kun, frenky and many others
#     for the inspiration to figure this out
# This is not a finished product and you can use it if you like. Don't be
# suprised if there are bugs as I am NOT a programmer..... ;>))
# This is my first python program and has been a learning experience.
# There may also be a lot of test code sprinkled about which probably doesn't work.
# Updated the USB send/receive message code to use Fry-Kun's (sort of). And add
# a bit of error checking.
#
# There are also the beginings of some documentation on the Seek init sequence.
#
###########################################################################


import usb.core
import usb.util
import sys
from PIL import Image, ImageTk
import numpy
from numpy import array
import colorscale # used to colorize the image, be sure that colorscale.py is in the
# current directory
# Original colorscale.py from https://github.com/pklaus/python-colorscale
from scipy.misc import toimage
from scipy import ndimage
import scipy.io as sio
import Tkinter



class App(Tkinter.Tk):
    def __init__(self,parent):
        Tkinter.Tk.__init__(self,parent)
        self.parent = parent
        self.initialize()

# defs

    def usbinit(self):
# find our Seek Thermal device  289d:0010
	dev = usb.core.find(idVendor=0x289d, idProduct=0x0010)

# was it found?
	if dev is None:
    	    raise ValueError('Device not found')

# set the active configuration. With no arguments, the first
# configuration will be the active one
	dev.set_configuration()

# get an endpoint instance
	cfg = dev.get_active_configuration()
	intf = cfg[(0,0)]

	ep = usb.util.find_descriptor(
	    intf,
    # match the first OUT endpoint
    	    custom_match = \
    	    lambda e: \
		usb.util.endpoint_direction(e.bEndpointAddress) == \
    		usb.util.ENDPOINT_OUT)

	assert ep is not None

	return dev

# send_msg sends a message that does not need or get an answer
    def send_msg(self,dev,bmRequestType, bRequest, wValue=0, wIndex=0, data_or_wLength=None, timeout=None):
	assert (dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data_or_wLength, timeout) == len(data_or_wLength))

# alias method to make code easier to read
# receive msg actually sends a message as well.
    def receive_msg(self,dev,bmRequestType, bRequest, wValue=0, wIndex=0, data_or_wLength=None, timeout=None):
	zz = dev.ctrl_transfer(bmRequestType, bRequest, wValue, wIndex, data_or_wLength, timeout) # == len(data_or_wLength))
	return zz

# Documentation on the init sequence starts here

#  Some day we will figure out what all this init stuff is and
#  what the returned values mean.

# Here are what the commands mean, still no clue about the passed params or return values:

#   ("WINDOWS_TARGET", 0, 0);
#   ("ANDROID_TARGET", 1, 1);
#   ("MACOS_TARGET", 2, 2);
#   ("IOS_TARGET", 3, 3);

#  There seem to be 2 SeekOperationMode(s) 0 = Sleep, 1 = Run


#    BEGIN_MEMORY_WRITE = 82;
#    COMPLETE_MEMORY_WRITE = 81;
#    GET_BIT_DATA = 59;
#    GET_CURRENT_COMMAND_ARRAY = 68;
#    GET_DATA_PAGE = 65;
#    GET_DEFAULT_COMMAND_ARRAY = 71;
#    GET_ERROR_CODE = 53;
#  * GET_FACTORY_SETTINGS = 88;
#  * GET_FIRMWARE_INFO = 78;
#    GET_IMAGE_PROCESSING_MODE = 63;
#  * GET_OPERATION_MODE = 61;
#    GET_RDAC_ARRAY = 77;
#    GET_SHUTTER_POLARITY = 57;
#    GET_VDAC_ARRAY = 74;
#  * READ_CHIP_ID = 54;
#    RESET_DEVICE = 89;
#    SET_BIT_DATA_OFFSET = 58;
#    SET_CURRENT_COMMAND_ARRAY = 67;
#    SET_CURRENT_COMMAND_ARRAY_SIZE = 66;
#    SET_DATA_PAGE = 64;
#    SET_DEFAULT_COMMAND_ARRAY = 70;
#    SET_DEFAULT_COMMAND_ARRAY_SIZE = 69;
#    SET_FACTORY_SETTINGS = 87;
#  * SET_FACTORY_SETTINGS_FEATURES = 86;
#    SET_FIRMWARE_INFO_FEATURES = 85;
#  * SET_IMAGE_PROCESSING_MODE = 62;
#  * SET_OPERATION_MODE = 60;
#    SET_RDAC_ARRAY = 76;
#    SET_RDAC_ARRAY_OFFSET_AND_ITEMS = 75;
#    SET_SHUTTER_POLARITY = 56;
#    SET_VDAC_ARRAY = 73;
#    SET_VDAC_ARRAY_OFFSET_AND_ITEMS = 72;
#  * START_GET_IMAGE_TRANSFER = 83;
#  * TARGET_PLATFORM = 84;
#    TOGGLE_SHUTTER = 55;
#    UPLOAD_FIRMWARE_ROW_SIZE = 79;
#    WRITE_MEMORY_DATA = 80;


#  Only a few of the above (*) seem to be used in the normal startup sequence
# End of documentation


# De-init the device
    def deinit(self,dev):
	msg = '\x00\x00'
        for i in range(3):
	    self.send_msg(dev,0x41, 0x3C, 0, 0, msg)           # 0x3c = 60  Set Operation Mode 0x0000 (Sleep)

# Camera initilization
    def camerainit(self,dev):

	try:
	    msg = '\x01'
	    self.send_msg(dev,0x41, 0x54, 0, 0, msg)              # 0x54 = 84 Target Platform 0x01 = Android
	except Exception as e:
	    self.deinit(dev)
	    msg = '\x01'
	    self.send_msg(dev,0x41, 0x54, 0, 0, msg)              # 0x54 = 84 Target Platform 0x01 = Android

	self.send_msg(dev,0x41, 0x3C, 0, 0, '\x00\x00')              # 0x3c = 60 Set operation mode    0x0000  (Sleep)
	ret1 = self.receive_msg(dev,0xC1, 0x4E, 0, 0, 4)             # 0x4E = 78 Get Firmware Info
#print ret1
#array('B', [1, 3, 0, 0])

	ret2 = self.receive_msg(dev,0xC1, 0x36, 0, 0, 12)            # 0x36 = 54 Read Chip ID
#print ret2
#array('B', [20, 0, 12, 0, 86, 0, 248, 0, 199, 0, 69, 0])

	self.send_msg(dev,0x41, 0x56, 0, 0, '\x20\x00\x30\x00\x00\x00')                  # 0x56 = 86 Set Factory Settings Features
	ret3 = self.receive_msg(dev,0xC1, 0x58, 0, 0, 0x40)                              # 0x58 = 88 Get Factory Settings
#print ret3
#array('B', [2, 0, 0, 0, 0, 112, 91, 69, 0, 0, 140, 65, 0, 0, 192, 65, 79, 30, 86, 62, 160, 137, 64, 63, 234, 149, 178, 60, 0, 0, 0, 0, 0, 0, 0, 0, 72, 97, 41, 66, 124, 13, 1, 61, 206, 70, 240, 181, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 66, 0, 0, 2, 67])

	self.send_msg(dev,0x41, 0x56, 0, 0, '\x20\x00\x50\x00\x00\x00')                  # 0x56 = 86 Set Factory Settings Features
	ret4 = self.receive_msg(dev,0xC1, 0x58, 0, 0, 0x40)                              # 0x58 = 88 Get Factory Settings
#print ret4
#array('B', [0, 0, 0, 0, 0, 0, 0, 0, 255, 255, 255, 255, 255, 255, 255, 255, 161, 248, 65, 63, 40, 127, 119, 60, 44, 101, 55, 193, 240, 133, 129, 63, 244, 253, 96, 66, 40, 15, 155, 63, 43, 127, 103, 186, 9, 144, 186, 52, 0, 0, 0, 0, 0, 0, 2, 67, 0, 0, 150, 67, 0, 0, 0, 0])

	self.send_msg(dev,0x41, 0x56, 0, 0, '\x0C\x00\x70\x00\x00\x00')                  # 0x56 = 86 Set Factory Settings Features
	ret5 = self.receive_msg(dev,0xC1, 0x58, 0, 0, 0x18)                              # 0x58 = 88 Get Factory Settings
#print ret5
#array('B', [0, 0, 0, 0, 255, 255, 255, 255, 190, 193, 249, 65, 205, 204, 250, 65, 48, 42, 177, 191, 200, 152, 147, 63])

	self.send_msg(dev,0x41, 0x56, 0, 0, '\x06\x00\x08\x00\x00\x00')                  # 0x56 = 86 Set Factory Settings Features   
	ret6 = self.receive_msg(dev,0xC1, 0x58, 0, 0, 0x0C)                              # 0x58 = 88 Get Factory Settings
#print ret6
#array('B', [49, 52, 48, 99, 49, 48, 69, 52, 50, 78, 55, 49])

	self.send_msg(dev,0x41, 0x3E, 0, 0, '\x08\x00')                                  # 0x3E = 62 Set Image Processing Mode 0x0008
	ret7 = self.receive_msg(dev,0xC1, 0x3D, 0, 0, 2)                                 # 0x3D = 61 Get Operation Mode
#print ret7
#array('B', [0, 0])

	self.send_msg(dev,0x41, 0x3E, 0, 0, '\x08\x00')                                  # 0x3E = 62 Set Image Processing Mode  0x0008
	self.send_msg(dev,0x41, 0x3C, 0, 0, '\x01\x00')                                  # 0x3c = 60 Set Operation Mode         0x0001  (Run)
	ret8 = self.receive_msg(dev,0xC1, 0x3D, 0, 0, 2)                                 # 0x3D = 61 Get Operation Mode
#print ret8
#array('B', [1, 0])



#####################################################################
# build a matrix of "patent pixils" that match the Seek Imager
# this may be useful later, this code is not executed in the program 
# but included to show how to find the "patent pixels"
    def dots(self):
        dotsF = numpy.zeros((156,208))
        dotsI = dotsF.astype('uint8')
        k = 10

        for i in range(0,155,1):
            for j in range(k,206,15):
#                print i,j
		    dotsI[i,j] = 255
		    k = k - 4
    	    if k < 0: k = k + 15

	return dotsI
# display it to see if it matches the Seek black dot hex pattern

#	zz = Image.fromstring("I", (208,156), dotsI, "raw", "I;8")
#	toimage(zz).show()
#        print dotsI
#####################################################################


    def printIMG(self,img):
	global Label1, Label2
	j = img.min()
	k = img.max()
        Label1.configure( text="Img min %d" % j)
        Label2.configure( text="Img max %d" % k)

    def printCAL(self,cal):
	global Label3, Label4
	j = cal.min()
	k = cal.max()
        Label3.configure( text="Cal min %d" % j)
        Label4.configure( text="Cal max %d" % k)

    def printSUM(self,add):
	global Label5, Label6
	j = add.min()
	k = add.max()
        Label5.configure( text="Sum min %d" % j)
        Label6.configure( text="Sum max %d" % k)

    def read_frame(self,dev): # Send a read frame request

        self.send_msg(dev,0x41, 0x53, 0, 0, '\xC0\x7E\x00\x00')                 # 0x53 = 83 Set Start Get Image Transfer

        try:
            data  = dev.read(0x81, 0x3F60, 1000)
            data += dev.read(0x81, 0x3F60, 1000)
            data += dev.read(0x81, 0x3F60, 1000)
            data += dev.read(0x81, 0x3F60, 1000)
        except usb.USBError as e:
            sys.exit()

	return data

###################################

    def add_207(self,imgF):  # Add (really subtract) the data from the 207 row to each pixil
	global scl2
# or not depending on the testing some of the following may be commented out.
# there are a different # of black dots in each row so the divisor
# needs to change for each row according to what is in the dot_numbers.txt file.
# this may not be the best way to do this. The code below does not do this now.
# need to try to use numpy or scipy to do this as it is a real hit on cpu useage.
# But doing it only for the cal image doesn't impact the real time images.
	tuning = scl2.get() / 150.0

	z = (.002 * imgF[:,206].mean())
	z1 = z * tuning
#	print tuning
#	maxTune = ( imgF[:,206].max())
#	minTune = ( imgF[:,206].min())

	for i in range(0,156,1):
	    for j in range(0,205,1):
		    imgF[i,j] = imgF[i,j] - (.05 * imgF[i,j]/z) - imgF[i,206]/z1 # try scaled pixil and scaled pixil 207
#		    imgF[i,j] = imgF[i,j]
	return

#	for i in range(0,156,1):
#	    for j in range(0,205,1):
#		    imgF[i,j] = imgF[i,j] - (.05 * imgF[i,j]/z) - imgF[i,206]/z # try scaled pixil and scaled pixil 207
#	return

####################################

    def pal1(self):
	global pal
	pal = 'ironscale'
    def pal2(self):
	global pal
	pal = 'whitehotscale'
    def pal3(self):
	global pal
	pal = 'blackhotscale'
    def pal4(self):
	global pal
	pal = 'greenredscale'
    def snap(self):
	global snapshot
	snapshot = 1


# Main program starts here (you can tell I'm new to Python ;)
    def initialize(self):

	global dev, label, Label1, Label2, Label3, Label4, Label5, Label6
	global scl, scl1, scl2
	global calImage, calImagex, calimgI, pal, snapshot

# Default palette is "iron"
	pal = 'ironscale'
	snapshot = 0

# Set up device
	dev = self.usbinit()
	self.camerainit(dev)

	self.grid()

# Buttons for changing palettes
        button1 = Tkinter.Button(self,text=u"Iron",command=self.pal1)
        button1.grid(row=0,column=5)
        button2 = Tkinter.Button(self,text=u"WhiteHot",command=self.pal2)
        button2.grid(row=1,column=5)
        button3 = Tkinter.Button(self,text=u"BlackHot",command=self.pal3)
        button3.grid(row=2,column=5)
        button4 = Tkinter.Button(self,text=u"GreenRed",command=self.pal4)
        button4.grid(row=3,column=5)
        button5 = Tkinter.Button(self,text=u"Snap!",command=self.snap)
        button5.grid(row=4,column=5)

# Set up the label positions for the img, cal and sum data
	Label1 = Tkinter.Label(self,text="Label1")
	Label2 = Tkinter.Label(self,text="Label2")
	Label3 = Tkinter.Label(self,text="Label3")
	Label4 = Tkinter.Label(self,text="Label4")
	Label5 = Tkinter.Label(self,text="Label5")
	Label6 = Tkinter.Label(self,text="Label6")

	Label1.grid(row=4,column=0,sticky='W') # img min
	Label2.grid(row=5,column=0,sticky='W') # img max
	Label3.grid(row=4,column=1,sticky='W') # cal min
	Label4.grid(row=5,column=1,sticky='W') # cal max
	Label5.grid(row=4,column=2,sticky='E') # sum min
	Label6.grid(row=5,column=2,sticky='E') # sum max

# set up the position of the image
        label = Tkinter.Label(self,text="your image here", compound="top")

	label.grid(column=0,row=1,columnspan=3,rowspan=3,sticky='EW')
	self.grid_columnconfigure(0,weight=1)
	self.resizable(True,True)

# set up the position of the 2 sliders for the top & bottom ranges
	scl = Tkinter.Scale(self, from_=0, to=255, length=200, orient=Tkinter.HORIZONTAL, label='Bottom Range')
	scl.set(0)
	scl.grid(row = 0, column=0,sticky='W')

	scl1 = Tkinter.Scale(self, from_=0, to=255,length=200, orient=Tkinter.HORIZONTAL, label='Top Range')
	scl1.set(64)
	scl1.grid(row = 0, column=2)

	scl2 = Tkinter.Scale(self, from_=100, to=300,length=200, orient=Tkinter.HORIZONTAL, label='Tuning')
	scl2.set(200)
	scl2.grid(row = 0, column=1)

# start iteration (or frame) count to 0
# this is printed out on the GUI so you can get a feel for how fast the program is running.
# maybe should implemt an FPS function like Fry-Kun did.
	self.iteration=0

# get a cal image so the data isn't null if/when we miss the first one
        self.get_cal_image(dev)

# update the image after 10 ms wait
	self.UpdateImage(10)

# End of the initilization routine


# This is actually the main loop as it self-calls at the end

    def UpdateImage(self, delay, event=None):
        # this is merely so the display changes even though the image doesn't
	global dev, status, calImage, calimgI, ImageFinal, label
        self.iteration += 1

        self.image = self.get_image(dev)
	ImageFinal = self.image

        label.configure(image=ImageFinal, text="Frames captured %s" % self.iteration)
        # reschedule to run again in 1 ms
        self.after(delay, self.UpdateImage, 1)

# End of main loop

    def get_cal_image(self,dev):
# Get the first cal image so calImage isn't null

	global status, calImage, calimgI, calImagex
	status = 0

#  Wait for the cal frame

	while status != 1:
#  1 is a Calibration frame

# Read a raw frame
	   ret9 = self.read_frame(dev)

	   status = ret9[20]

	   status1 = ret9[80]
#	   print (status , status1)


#  6 is a pre-calibration frame (whatever that means)
#  4, 9, 8, 7, 5, 10 other... who knows.
#  See http://www.eevblog.com/forum/testgear/yet-another-cheap-thermal-imager-incoming/msg545910/#msg545910
#  for examples.


#  Convert the raw 16 bit calibration data to a PIL Image

	calimgI = Image.frombytes("F", (208,156), ret9, "raw", "F;16")

# save 16bit cal image for later
	calImagex = Image.frombytes("I", (208,156), ret9, "raw", "I;16")

#  Convert the PIL Image to an unsigned numpy float array

	im2arr = numpy.asarray(calimgI)

# clamp values < 2000 to 2000

	im2arr = numpy.where(im2arr < 2000, 2000, im2arr)

	im2arrF = im2arr.astype('float')
	calImage = im2arrF

	return


    def get_image(self,dev):
	global calImage, calimgI, calImagex, status, scl, scl1, pal, snapshot

	status = 0

#  Wait for the next image frame, ID = 3 is a Normal frame
	while status != 3:


# Read a raw frame
	   ret9 = self.read_frame(dev)

	   status = ret9[20]


# check for a new cal frame, if so update the cal image
	   if status == 1:

#  Convert the raw 16 bit calibration data to a PIL Image
		calimgI = Image.frombytes("F", (208,156), ret9, "raw", "F;16")

# save cal 16bit image for later
		calImagex = Image.frombytes("I", (208,156), ret9, "raw", "I;16")

#  Convert the PIL Image to an unsigned numpy float array
		im2arr = numpy.asarray(calimgI)

# Pixel 40 is a counter of some sort that starts at 0 and increments to 65535
# maybe an internal frame counter or clock.
		status1 = im2arr[0,40]

# clamp values < 2000 to 2000
		im2arr = numpy.where(im2arr < 2000, 2000, im2arr)
		im2arrF = im2arr.astype('float')

# Clamp pixel 40 to 2000 so it doesn't cause havoc as it rises to 65535
	        im2arrF[0,40] = 2000

# Add the row 207 correction (maybe) >>Looks like it needs to be applied to just the cal frame<<
		self.add_207(im2arrF)

# Zero out column 207
		im2arrF[:,206] = numpy.zeros(156)

#  Print the min max values for the calimage
		self.printCAL(im2arrF)

#  Save the calibration image
		calImage = im2arrF

#  If this is normal image data
#  Convert the raw 16 bit thermal data to a PIL Image
	imgx = Image.fromstring("F", (208,156), ret9, "raw", "F;16")
	imgy = Image.fromstring("I", (208,156), ret9, "raw", "I;16")

#  Convert the PIL Image to an unsigned numpy float array
	im1arr = numpy.asarray(imgx)

# Pixel 40 is a counter of some sort that starts at 0 and increments to 65535
# maybe an internal frame counter or clock.
#	status1 = im1arr[0,40]

# clamp values < 2000 to 2000
	im1arr = numpy.where(im1arr < 2000, 2000, im1arr)
	im1arrF = im1arr.astype('float')

# Clamp pixel 40 to 2000 so it doesn't cause havoc as it rises to 65535
	im1arrF[0,40]  = 2000

# Zero out column 207
	im1arrF[:,206] = numpy.zeros(156)

#  Print the min max values for the image
	self.printIMG(im1arrF)

#  Subtract the most recent calibration image from the offset image data
#  With both the cal and image as floats, the offset doesn't matter and
#  the following image conversion scales the result to display properly
	additionF = (im1arrF) + 600 - (calImage)

#  Try removing noise from the image, this works suprisingly well, but takes some cpu time
#  It gets rid of bad pixels as well as the "Patent Pixils"
	noiselessF = ndimage.median_filter(additionF, 3)

# don't bother to zero out column 207 as it contains no data
# can't see any difference on the image anyway.
#	noiselessF[:,206] = numpy.zeros(156)

#  Print the min max values for the calibrated/noise filtered image
	self.printSUM(noiselessF)


# This will colorize the image, it works but it is a cpu hog

	bottom = scl.get()
	top = scl1.get()

	display_min = bottom * 4
	display_max = top * 16
	image8 = noiselessF

        image8.clip(display_min, display_max, out=image8)
        image8 -= display_min
	image8 //= (display_max - display_min + 1) / 256.
        image8 = image8.astype(numpy.uint8)

	noiselessI8= image8

	conv = colorscale.GrayToRGB(palettes[pal])
	cred = numpy.frompyfunc(conv.get_red, 1, 1)
	cgreen = numpy.frompyfunc(conv.get_green, 1, 1)
	cblue = numpy.frompyfunc(conv.get_blue, 1, 1)

# Convert to a PIL image sized to 640 x 480
	color = numpy.dstack((cred(noiselessI8).astype(noiselessI8.dtype), cgreen(noiselessI8).astype(noiselessI8.dtype), cblue(noiselessI8).astype(noiselessI8.dtype)))
	imgCC = Image.fromarray(color).resize((640, 480),Image.ANTIALIAS).transpose(3)

# If user has clicked Snap! then save the rawCal, rawData, and colorized image
# File names are hardcoded for now.
	if snapshot == 1: 
	    im1arry = numpy.asarray(imgy)
	    im1arrz = numpy.asarray(calImagex)
	    jj = Image.fromarray(im1arry)
	    jj.save('data/rawData.png')
	    jj = Image.fromarray(im1arrz)
	    jj.save('data/rawCal.png')
	    imgCC.save('data/CImage.png')
            sio.savemat('data/vars.mat', {'raw':numpy.asarray(imgx), 'cal':numpy.asarray(calimgI), 'py_processed':noiselessF})
	    snapshot = 0

# Then convert the colorized image to a PhotoImage which auto scales when displayed by Tkinter
	image = ImageTk.PhotoImage(imgCC)

        return image

# The following palettes are supported, add more in colorscale.py

palettes = dict()
palettes['tillscale'] = colorscale.TillPalette()
palettes['gray1scale'] = colorscale.Gray1Palette()
palettes['redgreenscale'] = colorscale.RedGreenPalette()
palettes['greenredscale'] = colorscale.GreenRedPalette()
palettes['rain1scale'] = colorscale.Rain1Palette()
palettes['ironscale'] = colorscale.IronPalette()
palettes['blackhotscale'] = colorscale.BlackHotPalette()
palettes['whitehotscale'] = colorscale.WhiteHotPalette()


if __name__ == "__main__":
    app=App(None)
    app.title('Seek Thermal Imager')
    app.mainloop()

