#!/usr/bin/env python

import errno
import fnmatch
import io
import os
import os.path
import picamera
import pygame
import stat
from pygame.locals import *


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

def quitCallback(): # Quit confirmation button
  camera.stop_preview()
  raise SystemExit

def viewCallback(n): # Viewfinder buttons
  global scan_flag, scaled, screenMode, screenModePrior

  if n is 0:   # Gear icon (settings)
    if screenMode == 0:
      takePicture()
    else:
      screenMode = 0
  elif n is 1:
    screenMode = 1
  elif n is 2: # Play icon (image playback)
    screenModePrior = screenMode
    screenMode      = 3
    scan_flag = 1
    camera.stop_preview()
    r = imgRange(pathData[storeMode][0])
    if r: 
      showImage(r[1])
  elif n is 3:
    if video_flag:
      screenMode = 2
      takeVideo()
    else:
      screenMode = 1
      takeVideo()

def imageCallback(n): # Pass 1 (next image), -1 (prev image) or 0 (delete)
  global scan_flag, image_loadIdx, screenMode, screenModePrior
 
  if n is 3:
    scan_flag = 1
  elif n is 4:
    scan_flag = 2
  elif n is 2:
    camera.start_preview()
    screenMode = screenModePrior
    print screenMode
  elif n is 0:
    deleteCallback(image_loadIdx)
  else:
    showNextImage(n)

def deleteCallback(n): # Delete confirmation
  global scan_flag, screenMode, storeMode

  if scaled:
    if scan_flag is 1:
      os.remove(pathData[storeMode][0] + '/IMG_' + '%04d' % n + '.JPG')
      screen.fill(0)
      pygame.display.update()
      showNextImage(-1)
    if scan_flag is 2:
      os.remove(pathData[storeMode][1] + '/VID_' + '%04d' % n + '.h264')
      screen.fill(0)
      pygame.display.update()
      showNextImage(-1)     

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
scan_flag	= 0

sizeData = [ # Camera parameters for different size settings
 [(1280, 960), (640, 480), (0.0   , 0.0   , 1.0   , 1.0   )]
]


pathData = [
  ['/home/pi/Photos', '/home/pi/Videos']
]

def expCallback(n):
  global expIdx
def inteCallback(n):
  global inteIdx
icons = [] # This list gets populated at startup

buttons = [
  # Screen mode 0 is viewfinder / snapshot
  [Button(( 10,214, 52, 52), bg='photo_small', cb=viewCallback, value=0),
   Button((738,112, 52, 52), bg='video_small', cb=viewCallback, value=1),
   Button((738,214, 52, 52), bg='scan_small', cb=viewCallback, value=2),
   Button((738,316, 52, 52), bg='quite', cb=quitCallback),
   Button(( 10,112, 52, 52), bg='explore',cb=expCallback,value=3),
   Button(( 10,316, 52, 52), bg='interfere',cb=inteCallback,value=4)],


  # Screen mode 1
  [Button((738,112, 52, 52), bg='photo_small', cb= viewCallback, value=0),
   Button(( 10,214, 52, 52), bg='video_close', cb=viewCallback, value=3),
   Button((738,214, 52, 52), bg='scan_small', cb=viewCallback, value=2),
   Button((738,316, 52, 52), bg='quite', cb=quitCallback),
   Button(( 10,112, 52, 52), bg='explore',cb=expCallback,value=3),
   Button(( 10,316, 52, 52), bg='interfere',cb=inteCallback,value=4)],


  # Screen mode 2
  [Button(( 10,214, 52, 52), bg='video_open', cb=viewCallback, value=3)], 

  # Screen mode 3 is photo playback
  [Button((738, 10, 52, 52), bg='up' , cb=imageCallback, value=-1),
   Button((738,418, 52, 52), bg='down' , cb=imageCallback, value= 1),
   Button(( 10,163, 52, 52), bg='photo_small', cb=imageCallback, value=3),
   Button(( 10,265, 52, 52), bg='video_small', cb=imageCallback, value=4),
   Button((738,163, 52, 52), bg='trash', cb=imageCallback, value= 0),
   Button((738,265, 52, 52), bg='return' , cb=imageCallback, value= 2)],

]

# Video --------------------------------------------------------------------
def videoRange(path):
  min = 9999
  max = 0
  try:  
    for file in os.listdir(path):
      if fnmatch.fnmatch(file, 'VID_[0-9][0-9][0-9][0-9].h264'):
        i = int(file[4:8])
        if(i < min): min = i
        if(i > max): max = i
  finally:
    return None if min > max else (min, max)

def takeVideo():
  global video_flag, video_saveIdx, storeMode
  
  if video_flag:
    while True:
      filename = pathData[storeMode][1] + '/VID_' + '%04d' % video_saveIdx + '.h264'
      if not os.path.isfile(filename): break
      video_saveIdx += 1
      if video_saveIdx > 9999: video_saveIdx = 0

    camera.resolution = sizeData[sizeMode][0]
    camera.start_recording(filename, format='h264')
    os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    video_flag = False
  else:
    camera.stop_recording()
    video_flag = True

def showNextVideo(direction):
  global video_loadIdx

  n = video_loadIdx
  while True:
    n += direction
    if(n > 9999): n = 0
    elif(n < 0):  n = 9999
    if os.path.exists(pathData[storeMode][1] + '/VID_' + '%04d' % n + '.JPG'):
        showVideo(n)
        break

def showVideo(n):
  global scaled, sizeMode, storeMode

# Image -------------------------------------------------------------------

def imgRange(path):
  min = 9999
  max = 0
  try:  
    for file in os.listdir(path):
      if fnmatch.fnmatch(file, 'IMG_[0-9][0-9][0-9][0-9].JPG'):
        i = int(file[4:8])
        if(i < min): min = i
        if(i > max): max = i
  finally:
    return None if min > max else (min, max)

def takePicture():
  global image_saveIdx, storeMode
  
  while True:
    filename = pathData[storeMode][0] + '/IMG_' + '%04d' % image_saveIdx + '.JPG'
    if not os.path.isfile(filename): break
    image_saveIdx += 1
    if image_saveIdx > 9999: image_saveIdx = 0

  camera.capture(filename, use_video_port=False, format='jpeg', thumbnail=None)
  os.chmod(filename, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

def showNextImage(direction):
  global image_loadIdx
  
  n = image_loadIdx
  while True:
    n += direction
    if(n > 9999): n = 0
    elif(n < 0):  n = 9999
    if n is image_loadIdx: break
    if os.path.exists(pathData[storeMode][0] + '/IMG_' + '%04d' % n + '.JPG'):
    	showImage(n)
    	break

def showImage(n):
  global image_loadIdx, scaled, sizeMode, storeMode

  image_loadIdx  = n
  img      = pygame.image.load(pathData[storeMode][0] + '/IMG_' + '%04d' % n + '.JPG')
  scaled   = pygame.transform.scale(img, sizeData[sizeMode][1])

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
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN|pygame.HWSURFACE, 32)

# Init camera and set up default values
camera            = picamera.PiCamera()
camera.resolution = sizeData[sizeMode][0]
camera.crop       = sizeData[sizeMode][2]
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

r = imgRange(pathData[storeMode][0])
if r:
  image_saveIdx = r[1]

# Main loop ----------------------------------------------------------------

f = open('/root/pos.txt','w+')
camera.start_preview()

while True:
  
  for event in pygame.event.get():
    if(event.type is MOUSEBUTTONDOWN):
      pos = pygame.mouse.get_pos() 
      f.write('%d:' % pos[0])
      f.write('%d\n' % pos[1])
      for b in buttons[screenMode]:
        if b.selected(pos): break

  screen.fill(0)

  if screenMode == 3 and scaled:
    screen.blit(scaled,
      ((800 - scaled.get_width() ) / 2,
       (480 - scaled.get_height()) / 2))
  
  for i,b in enumerate(buttons[screenMode]):
    b.draw(screen)
  pygame.display.update()
