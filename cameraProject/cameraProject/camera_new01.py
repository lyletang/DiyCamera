#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import datetime as dt
import errno
import fnmatch
import io
import multiprocessing
import os
import os.path
import picamera
import pygame
import stat
import thread
import time
import cv2

#import the necessary packages
#from __future__ import print_function
from imutils.video import VideoStream
import numpy as np
import argparse
import imutils

from pygame.locals import *


# Global stuff -------------------------------------------------------------

screenMode      =  0      # Current screen mode; default = viewfinder
screenModePrior = -1      # Prior screen mode (for detecting changes)
sizeMode        =  0      # Image size; default = Large
iconPath        = 'icons' # Subdirectory containing UI bitmaps (PNG format)
storeMode	= 0
video_saveIdx	= -1
video_loadIdx   = -1
image_saveIdx   = -1      # Image index for saving (-1 = none set yet)
image_loadIdx   = -1      # Image index for loading
scaled          = None    # pygame Surface w/last-loaded image
screenWidth	= 800
screenHeight	= 480
video_flag	= True
scan_flag	= 0       #scan_flag = 1 scan Image or =2 scan video
pin_flag        = 0
init_flag       = 0
video_showpos	= [0, 0, 0, 0]
scaled_show = [None, None, None, None]

sizeData = [
 [(1280, 960), (640, 480), (0.0, 0.0, 1.0, 1.0)]
]


pathData = [
  ['/home/pi/cameraProject/Photos', '/home/pi/cameraProject/Videos', '/home/pi/cameraProject/Data/']
]

# UI classes ---------------------------------------------------------------

class Icon:
  def __init__(self, name):
    self.name = name
    try:
      self.bitmap = pygame.image.load(iconPath + '/' + name + '.png')  
    except:
      pass

class Button:
  def __init__(self, rect, **kwargs):
    self.rect     = rect # Bounds
    self.color    = None # Background fill color, if any
    self.iconBg   = None # Background Icon (atop color fill)
    self.iconFg   = None # Foreground Icon (atop background)
    self.bg       = None # Background Icon name
    self.fg       = None # Foreground Icon name
    self.callback = None # Callback function
    self.value    = None # Value passed to callback
    for key, value in kwargs.iteritems():
      if   key == 'color': self.color    = value
      elif key == 'bg'   : self.bg       = value
      elif key == 'fg'   : self.fg       = value
      elif key == 'cb'   : self.callback = value
      elif key == 'value': self.value    = value

  def selected(self, pos):
    x1 = self.rect[0]
    y1 = self.rect[1]
    x2 = x1 + self.rect[2] - 1
    y2 = y1 + self.rect[3] - 1
    if ((pos[0] >= x1) and (pos[0] <= x2) and
        (pos[1] >= y1) and (pos[1] <= y2)):
      if self.callback:
        if self.value is None:
          self.callback()
        else:
          self.callback(self.value)
      return True
    return False

  def draw(self, screen):
    if self.color:
      screen.fill(self.color, self.rect)
    if self.iconBg:
      screen.blit(self.iconBg.bitmap,
        (self.rect[0]+(self.rect[2]-self.iconBg.bitmap.get_width())/2,
        self.rect[1]+(self.rect[3]-self.iconBg.bitmap.get_height())/2))
    if self.iconFg:
      screen.blit(self.iconFg.bitmap,
        (self.rect[0]+(self.rect[2]-self.iconFg.bitmap.get_width())/2,
        self.rect[1]+(self.rect[3]-self.iconFg.bitmap.get_height())/2))

  def setBg(self, name):
    if name is None:
      self.iconBg = None
    else:
      for i in icons:
        if name == i.name:
          self.iconBg = i
          break

# UI callbacks -------------------------------------------------------------

def quitCallback():         #退出
  camera.stop_preview()
  raise SystemExit

def viewCallback(n):        #显示消息处理
  global scan_flag, scaled, screenMode, screenModePrior, pin_flag, init_flag, image_loadIdx

  if n is 0:    #照相功能
    if screenMode == 0:
      takePicture()
    else:
      screenMode = 0

  elif n is 1:  #录像功能
    if screenMode == 0:
      screenMode = 1
    else:
      if video_flag:
        screenMode = 2
        takeVideo()
      else:
        screenMode = 1
        takeVideo()

  elif n is 2:  #相片回放
    screenModePrior = screenMode
    screenMode = 3
    scan_flag = 1
    camera.stop_preview()
    image_loadIdx = image_saveIdx
    showImage()

  elif n is 3:  #录像回放
    screenModePrior = screenMode
    screenMode = 4
    scan_flag = 1
    camera.stop_preview()
    tpos = video_saveIdx
    position = 0
    video_showpos[0] = 0
    video_showpos[1] = 0
    video_showpos[2] = 0
    video_showpos[3] = 0
    tpos += 1
    if (tpos > 0):
      while (position < 4):
        tpos += -1
        if (tpos < 1): break
        if (tpos > video_saveIdx): tpos = 1
        if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % tpos + '.jpg'):
          video_showpos[position] = tpos
          position += 1
    showVideo()

  elif n is 4:
    #screenMode = 0
    if init_flag is 0:
      print 4
      init_flag = 1
    if pin_flag is 0:
      print 4.1
      pin_flag = 1
      #t2 = thread.start_new_thread(timer2,(1,1))
    else:
      print 4.2
      pin_flag = 0
    
  elif n is 5:
    #screenMode = 0
    if init_flag is 0:
      print 1
      init_flag =  1
    if pin_flag is 0:
      print 2
      pin_flag = 1
      #t1 = thread.start_new_thread(timer,(1,1))
    else:
      print 3
      pin_flag = 0

def imageCallback(n):       #照相消息处理
  global scan_flag, image_loadIdx, screenMode, screenModePrior, video_saveIdx, video_showpos

  if n is 2:
    camera.start_preview()
    screenMode = screenModePrior
  elif n is 3:
    pass
  elif n is 4:
    tpos = video_saveIdx
    position = 0
    video_showpos[0] = 0
    video_showpos[1] = 0
    video_showpos[2] = 0
    video_showpos[3] = 0
    tpos += 1
    if (tpos > 0):
      while (position < 4):
        tpos += -1
        if (tpos < 1): break
        if (tpos > video_saveIdx): tpos = 1
        if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % tpos + '.jpg'):
          video_showpos[position] = tpos
          position += 1
    screenMode = 4
    showVideo()
  elif n is 0:
    deleteImageCallback(image_loadIdx)
  
  elif n is 5:
    renlianjiance()
  
  else:
    showNextImage(n)

def videoCallback(n):       #录像消息处理
  global scan_flag, image_loadIdx, screenMode, screenModePrior, video_saveIdx, image_saveIdx

  if n is 2:
    camera.start_preview()
    screenMode = screenModePrior
  elif n is 3:
    image_loadIdx = image_saveIdx
    screenMode = 3
    showImage()
  elif n is 4:
    pass
  elif n is 5:
    if video_showpos[0] != 0:
      deleteVideoCallback(0)
  elif n is 6:
    if video_showpos[1] != 0:
      deleteVideoCallback(1)
  elif n is 7:
    if video_showpos[2] != 0:
      deleteVideoCallback(2)
  elif n is 8:
    if video_showpos[3] != 0:
      deleteVideoCallback(3)
  elif n is 9:
    if video_showpos[0] != 0:
      playVideo(0)
  elif n is 10:
    if video_showpos[1] != 0:
      playVideo(1)
  elif n is 11:
    if video_showpos[2] != 0:
      playVideo(2)
  elif n is 12:
    if video_showpos[3] != 0:
      playVideo(3)
 
#the work of encryption
  elif n is 13:
  	encryption()
#the work of decryption	
  elif n is 14:	
  	pass
  
  else:
    showNextVideo(n)

def deleteVideoCallback(n):      #删除功能
  global storeMode, video_loadIdx
  os.remove(pathData[storeMode][1] + '/VID_' + '%04d' % video_showpos[n] + '.h264')
  os.remove(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_showpos[n] + '.jpg')
  os.remove(pathData[storeMode][2] + '/VID_' + '%04d' % video_showpos[n] + '.h264')
  os.remove(pathData[storeMode][2] + '/VIDPRE_' + '%04d' % video_showpos[n] + '.jpg')
  screen.fill(0)
  screen.fill(0)
  pygame.display.update()
 
  temp = video_showpos[n]

  for i in range(n+1, 4, 1):
    video_showpos[i-1] = video_showpos[i]
    video_showpos[i] = 0
  if n == 3: video_showpos[n] = 0

  position = 3
  for i in range(0, 4, 1):
    if video_showpos[i] == 0:
      position = i
      break

  video_loadIdx = video_showpos[position-1]
  if (video_loadIdx > 0):
    while (position < 4):
      video_loadIdx += -1
      if (video_loadIdx < 1): break
      if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_loadIdx + '.jpg'):
        video_showpos[position] = video_loadIdx
        position += 1
  
  if (position == 0):  
    position = 3
    if (temp > 0):
      while (position >= 0):
        temp += 1
        if (temp > video_saveIdx): break
        if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % temp + '.jpg'):
          video_showpos[position] = temp
          position += -1
  
  showVideo()

def deleteImageCallback(n):      #删除功能
  global storeMode

  if scaled:
    os.remove(pathData[storeMode][0] + '/IMG_' + '%04d' % n + '.jpg')
    os.remove(pathData[storeMode][2] + '/IMG_' + '%04d' % n + '.jpg')
    screen.fill(0)
    pygame.display.update()
    showNextImage(-1)

# explore  interfere  ---------------------------------$
def expCallback():
  global exploreIdx
def inteCallback():
  pass

icons = [] # This list gets populated at startup

buttons = [
  # Screen mode 0 is viewfinder / snapshot
  [Button(( 10,214, 52, 52), bg='photo_small', cb=viewCallback, value=0),
   Button((738,112, 52, 52), bg='video_small', cb=viewCallback, value=1),
   Button((738,214, 52, 52), bg='scan_small', cb=viewCallback, value=2),
   Button((738,316, 52, 52), bg='quite', cb=quitCallback),
   Button(( 10,112, 52, 52), bg='explore',cb=viewCallback,value=4),
   Button(( 10,316, 52, 52), bg='interfere',cb=viewCallback,value=5)],

  # Screen mode 1
  [Button((738,112, 52, 52), bg='photo_small', cb= viewCallback, value=0),
   Button(( 10,214, 52, 52), bg='video_close', cb=viewCallback, value=1),
   Button((738,214, 52, 52), bg='scan_small', cb=viewCallback, value=3),
   Button((738,316, 52, 52), bg='quite', cb=quitCallback),
   Button(( 10,112, 52, 52), bg='explore',cb=viewCallback,value=4),
   Button(( 10,316, 52, 52), bg='interfere',cb=viewCallback,value=5)],

  # Screen mode 2
  [Button(( 10,214, 52, 52), bg='video_open', cb=viewCallback, value=1)],

  # Screen mode 3 is photo playback
  [Button((738, 10, 52, 52), bg='up' , cb=imageCallback, value = 1),
   Button((738,418, 52, 52), bg='down' , cb=imageCallback, value= -1),
   Button(( 10,163, 52, 52), bg='photo_small', cb=imageCallback, value=3),
   Button(( 10,265, 52, 52), bg='video_small', cb=imageCallback, value=4),
   Button((738,163, 52, 52), bg='trash', cb=imageCallback, value= 0),
   Button((738,265, 52, 52), bg='return' , cb=imageCallback, value= 2),
#the picture renlian jiance
   Button((10, 63, 52, 52), bg='up', cb=imageCallback, value=5)],

  # Screen mode 4 is video playback
  [Button((738, 10, 52, 52), bg='up', cb=videoCallback, value=1),
   Button((738, 418, 52, 52), bg='down', cb=videoCallback, value=-1),
   Button((10, 163, 52, 52), bg='photo_small', cb=videoCallback, value=3),
   Button((10, 265, 52, 52), bg='video_small', cb=videoCallback, value=4),

  ##the video encryption and the disencryption
   #the button of encryption
   Button((10, 63, 52, 52), bg='up', cb = videoCallback, value=13),
   #the button of decryption
   Button((10, 363, 52, 52), bg='down', cb=videoCallback, value=14),
   
   Button((214, 94, 52, 52), bg='video_play', cb=videoCallback, value=9),
   Button((348, 188, 52, 52), bg='trash', cb=videoCallback, value=5),
   Button((534, 94, 52, 52), bg='video_play', cb=videoCallback, value=10),
   Button((668, 188, 52, 52), bg='trash', cb=videoCallback, value=6),
   Button((214, 334, 52, 52), bg='video_play', cb=videoCallback, value=11),
   Button((348, 428, 52, 52), bg='trash', cb=videoCallback, value=7),
   Button((534, 334, 52, 52), bg='video_play', cb=videoCallback, value=12),
   Button((668, 428, 52, 52), bg='trash', cb=videoCallback, value=8),

   Button((738, 265, 52, 52), bg='return', cb=videoCallback, value=2)]
]

def getDate():
  return time.strftime("%Y%m%d", time.localtime(time.time()))

def getMaxPos():
  global image_saveIdx, video_saveIdx, video_showpos, image_loadIdx
  file = open('camera_savepos', 'r')
  savepos = file.readline().split(':')
  image_saveIdx = int(savepos[0])
  video_saveIdx = int(savepos[1])
  file.close()

  image_loadIdx = image_saveIdx
  tpos = video_saveIdx
  position = 0
  video_showpos[0] = 0
  video_showpos[1] = 0
  video_showpos[2] = 0
  video_showpos[3] = 0
  tpos += 1
  if (tpos > 0):
    while (position < 4):
      tpos += -1
      if (tpos < 1): break
      if (tpos > video_saveIdx): tpos = 1
      if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % tpos + '.jpg'):
          video_showpos[position] = tpos
          position += 1


# Video --------------------------------------------------------------------
def takeVideo():
  global video_flag, video_saveIdx, storeMode, video_loadIdx
  
  if video_flag:
    video_saveIdx += 1
    if (video_saveIdx > 9999): video_saveIdx = 1

    filenamepre = pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_saveIdx + '.jpg'
    camera.capture(filenamepre, use_video_port=False, format='jpeg', thumbnail=None)

    camera.annotate_background = False
    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    camera.resolution = sizeData[sizeMode][0]
    filename = pathData[storeMode][1] + '/VID_' + '%04d' % video_saveIdx + '.h264'
    camera.start_recording(filename, format='mjpeg')

    os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    video_flag = False
  else:
    camera.stop_recording()

    filename = pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_saveIdx + '.jpg'
    target = pathData[storeMode][2] + '/VIDPRE_' + '%04d' % video_saveIdx + '.jpg'
    cmdStr = 'cp '+ filename + ' ' + target
    os.system(cmdStr)

    filename = pathData[storeMode][1] + '/VID_' + '%04d' % video_saveIdx + '.h264'
    target = pathData[storeMode][2] + '/VID_' + '%04d' % video_saveIdx + '.h264'
    cmdStr = 'cp '+ filename + ' ' + target
    os.system(cmdStr)

    file = open('camera_savepos', 'w+')
    file.write(str(image_saveIdx))
    file.write(':')
    file.write(str(video_saveIdx))
    file.close()

    video_flag = True

def showNextVideo(direction):
  global video_loadIdx, video_showpos, video_saveIdx
  if (direction == 1): 
    position = 3
    video_loadIdx = video_showpos[0]
    if (video_loadIdx > 0):
      while (position >= 0):
        video_loadIdx += 1
        if (video_loadIdx > video_saveIdx): break
        if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_loadIdx + '.jpg'):
          video_showpos[position] = video_loadIdx
          position += -1


  if (direction == -1): 
    position = 0
    video_loadIdx = video_showpos[3]
    if (video_loadIdx > 0):
      while (position < 4):
        video_loadIdx += -1
        if (video_loadIdx < 1): break
        if os.path.exists(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_loadIdx + '.jpg'):
          video_showpos[position] = video_loadIdx
          position += 1

    if position > 0:
      for i in range(position, 4, 1):
        video_showpos[i] = 0
  
  showVideo()

def showVideo():
  global scaled_show, storeMode, video_showpos
  
  scaled_show[0] = None
  if (video_showpos[0] != 0):
    img = pygame.image.load(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_showpos[0] + '.jpg')
    scaled_show[0] = pygame.transform.scale(img, (320, 240))

  scaled_show[1] = None
  if (video_showpos[1] != 0):
    img = pygame.image.load(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_showpos[1] + '.jpg')
    scaled_show[1] = pygame.transform.scale(img, (320, 240))

  scaled_show[2] = None
  if (video_showpos[2] != 0):
    img = pygame.image.load(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_showpos[2] + '.jpg')
    scaled_show[2] = pygame.transform.scale(img, (320, 240))

  scaled_show[3] = None
  if (video_showpos[3] != 0):
    img = pygame.image.load(pathData[storeMode][1] + '/VIDPRE_' + '%04d' % video_showpos[3] + '.jpg')
    scaled_show[3] = pygame.transform.scale(img, (320, 240))

def playVideo(n):
  filename = pathData[storeMode][1] + '/VID_' + '%04d' % video_showpos[n] + '.h264'
  print filename
  #cmdStr = "omxplayer --win '72,0,728,480' --fps 12 "
  cmdStr = "omxplayer --win '72,0,728,480' "
  cmdStr = cmdStr+filename
  os.system(cmdStr)

def encryption():
  pass
  #filename = pathData[storeMode][1] + '/VID_' + '0011' + '.avi'
	
  #cap = cv2.VideoCapture(filename)
  
  #fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
  #size = (int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
  #	int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
  #)

  #outname = pathData[storeMode][1] + '/VID_' + 'encryption' + '.avi'

  #out = cv2.VideoWriter(outname, cv2.cv.CV_FOURCC('I','4','2','0'),fps,size)


  #while(cap.isOpened()):
  #	ret, frame = cap.read()
	
  #	out.write(frame)
	
  #cmdStr = "omxplayer --win '80,0,720,480' "
  #cmdStr = cmdStr+filename
  #os.system(cmdStr)
 # except:
  #	pass
	
  #filename = pathData[storeMode][1] + '/VID_' + '0011' + '.avi'

  #outname = pathData[storeMode][1] + '/VID_' + 'example' + '.avi'
 
  #cap = cv2.VideoCapture(filename)

  #fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
  #size = (int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
  #	int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
  #)
  
  #fourcc = cv2.cv.CV_FOURCC('M','J','P','G')

  #out = cv2.VideoWriter(outname, fourcc, fps, size) 

  #while(cap.isOpened()):
  #	ret, frame = cap.read()
	#frame = imutils.resize(frame, width=300)

	#(h, w) = frame.shape[:2]
  #	(h, w) = (int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
  #		int(cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))
  #	)

  #	zeros = np.zeros((h, w), dtype='uint8')

	#(R, G, B) = cv2.split(frame)
	#R = cv2.merge([zeros, zeros, R])

	#output = np.zeros((h, w, 3), dtype='uint8')
	#output[:h, :w] = frame
	
#	out.write(frame)
	

#def decryption():
#  filename = pathData[storeMode][1] + '/VID_' + '0003' + '.h264' 




# Image -------------------------------------------------------------------
def takePicture():
  global storeMode, image_saveIdx, video_saveIdx, image_loadIdx

  image_saveIdx += 1
  if image_saveIdx > 9999: image_saveIdx = 1

  #camera.annotate_bg = False
  camera.annotate_text = ''
  filename = pathData[storeMode][0] + '/IMG_' + '%04d' % image_saveIdx + '.jpg'
  camera.capture(filename, use_video_port=False, format='jpeg', thumbnail=None)

  os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

  target = pathData[storeMode][2] + '/IMG_' + '%04d' % image_saveIdx + '.jpg'
  cmdStr = 'cp '+ filename + ' ' + target
  os.system(cmdStr)

  file = open('camera_savepos', 'w+')
  file.write(str(image_saveIdx))
  file.write(':')
  file.write(str(video_saveIdx))
  file.close()

def showNextImage(direction):
  global image_loadIdx, image_saveIdx

  while True:
    image_loadIdx += direction
    if (image_loadIdx < 1): image_loadIdx = image_saveIdx
    if (image_loadIdx > image_saveIdx):  image_loadIdx = 1
    if os.path.exists(pathData[storeMode][0] + '/IMG_' + '%04d' % image_loadIdx + '.jpg'):
      showImage()
      break

def showImage():
  global image_loadIdx, scaled, storeMode
  if os.path.exists(pathData[storeMode][0] + '/IMG_' + '%04d' % image_loadIdx + '.jpg'):
    img = pygame.image.load(pathData[storeMode][0] + '/IMG_' + '%04d' % image_loadIdx + '.jpg')
    scaled = pygame.transform.scale(img, (640, 480))

def renlianjiance():
	global image_loadIdx, scaled, storeMode

	faceCascade = cv2.CascadeClassifier('databases/haarcascade_frontalface_default.xml')
	
	if os.path.exists(pathData[storeMode][0] + '/IMG_' + '%04d' % image_loadIdx + '.jpg'):
		imagePath = pathData[storeMode][0] + '/IMG_' + '%04d' % image_loadIdx + '.jpg'
	image = cv2.imread(imagePath)
	gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

	faces = faceCascade.detectMultiScale(
		gray,
		scaleFactor = 1.06,
		minNeighbors = 6,
		minSize = (40,40),
		flags = cv2.cv.CV_HAAR_SCALE_IMAGE
	)
	
	#print 'found {0} faces!'.format(len(faces))
	for(x, y, w, h) in faces:
		cv2.rectangle(image, (x,y), (x+w, y+h), (0,255,0), -1)
	#cv2.imshow('Faces found', image)
	cv2.imwrite(imagePath, image)
	showImage()
	
# Initialization -----------------------------------------------------------

# Init framebuffer/touchscreen environment variables
os.putenv('SDL_VIDEODRIVER', 'directfb')
os.putenv('SDL_FBDEV'      , '/dev/fb0')
os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
os.putenv('SDL_MOUSEDEV'   , '/dev/input/event2')


# Get user & group IDs for file & folder creation
# (Want these to be 'pi' or other user, not root)
s = os.getenv("SUDO_UID")
uid = int(s) if s else os.getuid()
s = os.getenv("SUDO_GID")
gid = int(s) if s else os.getgid()

# Init pygame and screen
pygame.init()
pygame.mouse.set_visible(True)
#screen = pygame.display.set_mode((800,480))
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN|pygame.HWSURFACE|pygame.DOUBLEBUF, 32)

# Init camera and set up default values

camera            = picamera.PiCamera()
camera.resolution = sizeData[sizeMode][0]
camera.crop       = sizeData[sizeMode][2]
camera.framerate  = 25
#camera.start_preview()
# Leave raw format at default YUV, don't touch, don't set to RGB!

  
# Load all icons at startup.
for file in os.listdir(iconPath):
  if fnmatch.fnmatch(file, '*.png'):
    icons.append(Icon(file.split('.')[0]))

# Assign Icons to Buttons, now that they're loaded
for s in buttons:        # For each screenful of buttons...
  for b in s:            #  For each button on screen...
    for i in icons:      #   For each icon...
      if b.bg == i.name: #    Compare names; match?
        b.iconBg = i     #     Assign Icon to Button
        b.bg     = None  #     Name no longer used; allow garbage collection
      if b.fg == i.name:
        b.iconFg = i
        b.fg     = None

pathData[storeMode][2] = pathData[storeMode][2] + getDate()

if not os.path.isdir(pathData[storeMode][0]):
  try:
    os.makedirs(pathData[storeMode][0])
    # Set new directory ownership to pi user, mode to 755
    os.chown(pathData[storeMode][0], uid, gid)
    os.chmod(pathData[storeMode][0],
      stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
      stat.S_IRGRP | stat.S_IXGRP |
      stat.S_IROTH | stat.S_IXOTH)
  except OSError as e:
    # errno = 2 if can't create folder
    print errno.errorcode[e.errno]
    
if not os.path.isdir(pathData[storeMode][1]):
  try:
    os.makedirs(pathData[storeMode][1])
    # Set new directory ownership to pi user, mode to 755
    os.chown(pathData[storeMode][1], uid, gid)
    os.chmod(pathData[storeMode][1],
      stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
      stat.S_IRGRP | stat.S_IXGRP |
      stat.S_IROTH | stat.S_IXOTH)
  except OSError as e:
    # errno = 2 if can't create folder
    print errno.errorcode[e.errno]

if not os.path.isdir(pathData[storeMode][2]):
  try:
    os.makedirs(pathData[storeMode][2])
    # Set new directory ownership to pi user, mode to 755
    os.chown(pathData[storeMode][2], uid, gid)
    os.chmod(pathData[storeMode][2],
      stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
      stat.S_IRGRP | stat.S_IXGRP |
      stat.S_IROTH | stat.S_IXOTH)
  except OSError as e:
    # errno = 2 if can't create folder
    print errno.errorcode[e.errno]

# Main loop ----------------------------------------------------------------

camera.start_preview()
getMaxPos()
cflag = True

while True:
  camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  for event in pygame.event.get():
    if(event.type is MOUSEBUTTONDOWN):
      pos = pygame.mouse.get_pos() 
      pygame.mouse.set_pos((800, 480))
      for b in buttons[screenMode]:
        if b.selected(pos): break

  if cflag:
    pygame.mouse.set_pos((800, 480))
    screen.fill(0)

    if (screenMode == 3):
      if (scaled):
        screen.blit(scaled, (80, 0))
    elif (screenMode == 4):
      if (scaled_show[0] != None):
        screen.blit(scaled_show[0], (80, 0))
      if (scaled_show[1] != None):
        screen.blit(scaled_show[1], (400, 0))
      if (scaled_show[2] != None):
        screen.blit(scaled_show[2], (80, 240))
      if (scaled_show[3] != None):
        screen.blit(scaled_show[3], (400, 240))

  for i,b in enumerate(buttons[screenMode]):
    b.draw(screen)
  pygame.display.update()

  if screenMode == 2:
    cflag = False
    time.sleep(0.1)
  else:
    cflag = True
