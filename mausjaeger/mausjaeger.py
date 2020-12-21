import datetime
from logging import handlers

import RPi.GPIO as GPIO
import time
import logging
import picamera  # Importing the library for camera module
from datetime import date

camera = picamera.PiCamera()  # Setting up the camera
#camera.resolution = (1024, 768)
camera.resolution = (512,384)
#camera.resolution = (320, 180)
camera.framerate = 2

log_file = 'logs/mausjaeger.log'
logging.basicConfig(filename=log_file)
logger = logging.getLogger()
logHandler = handlers.TimedRotatingFileHandler(log_file, when='D', interval=1, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logHandler.setLevel(logging.INFO)
logger.addHandler(logHandler)


#Board Mode: Angabe der Pin-Nummer
GPIO.setmode(GPIO.BOARD)

#GPIO Pin definieren fuer den Dateneingang vom Sensor
PIR_GPIO = 8
GPIO.setup(PIR_GPIO, GPIO.IN)

def MOTION(PIR_GPIO):
     capture_time = datetime.datetime.now()
     filename = f'images/image_{capture_time.strftime("%Y-%m-%d_%H:%M:%S")}'
     image_list = []
     for i in range(0,40):
          image_list.append(filename + '-' + str(i) + '.jpg')
     if datetime.datetime.now().hour in [0, 1, 2, 3, 4, 5, 6, 7, 8, 17, 18, 19, 20, 21, 22, 23]:
          logger.info('Start Recording')
          camera.capture_sequence(image_list, use_video_port=True)
          logger.info('Stop Recording')
     else:
          logger.info('Not recording, not in operating hours.')



time.sleep(1)
logger.info('Motion detection activated')
time.sleep(1)
logger.info("**************************************")
capture_time = datetime.datetime.now()
filename = f'images/image_{capture_time.strftime("%Y-%m-%d_%H:%M:%S")}.jpg'
camera.capture(filename)
logger.info(f'Check test image: {filename}')
try:
     GPIO.add_event_detect(PIR_GPIO, GPIO.RISING, callback=MOTION)

     while 1:
          time.sleep(60)
except KeyboardInterrupt:
    GPIO.cleanup()

