import cv2
import sys

imagePath = sys.argv[1]

faceCascade = cv2.CascadeClassifier('databases/haarcascade_frontalface_default.xml')

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

cv2.waitKey(0)
