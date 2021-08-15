import os
import sys
import time
import datetime
import logging
import time
import json
import signal
from logging.handlers import RotatingFileHandler
import relay

import pyinotify as pyinotify
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
import boto3
import logging.handlers as handlers
import sys
import detect_image
import detect
from PIL import Image
from decimal import *
from apscheduler.schedulers.background import BackgroundScheduler
from apns2.client import APNsClient
from apns2.payload import Payload

import timeit
import confuse

config = confuse.Configuration('mousehunter-edge', __name__)

s3_client = boto3.client('s3')

log_file = 'logs/imagewatcher.log'
logging.basicConfig(filename=log_file)
logger = logging.getLogger()
logHandler = handlers.TimedRotatingFileHandler(log_file, when='D', interval=1, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger.setLevel(logging.INFO)
logHandler.setFormatter(formatter)
logHandler.setLevel(logging.INFO)
if (logger.hasHandlers()):
    logger.handlers.clear()
logger.addHandler(logHandler)

BUCKET = config['bucket'].get(None)
ALERT_THRESHOLD = config['alertThreshold'].get(2)
APNTOKEN = config['APNToken'].get(None)
CERTFILE = config['certfile'].get(None)

if BUCKET == None:
    logger.info("No AWS S3 bucket configured. Exit program.")
    sys.exit()

score_with_pray = 0
score_no_pray = 0

JOBKEY_DISABLE_CURFEW = "disableCurfewJob"
CURFEW_TIME = config['curfewTime'].get(15)

scheduler = BackgroundScheduler() 
scheduler.start()

def send_notification(message):
    if CERTFILE == None:
        logger.info('No certfile configured.')
        return
    if APNTOKEN == None:
        logger.info('No APN token configured.')
        return
    client = APNsClient(CERTFILE, use_sandbox=True, use_alternative_port=False)
    topic = 'gerrit.mousehunter'
    payload = Payload(alert=message, sound="default")
    client.send_notification(APNTOKEN, payload, topic)

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_CLOSE_WRITE(self, event):
    
        now = datetime.datetime.now()
        
        filename = str(event.pathname.split("/")[-1])
        if filename.split('.')[-1].lower() != 'jpg':
            logger.error('unknown file type: ' + filename)
            logger.error('file will be skipped')
            return
        image = Image.open(event.pathname)
        scale = detect.set_input(interpreter, image.size, lambda size: image.resize(size, Image.ANTIALIAS))
        start = time.perf_counter()
        logger.info("Invoke interpreter ...")
        interpreter.invoke()
        logger.info("Invoke interpreter done.")
        inference_time = time.perf_counter() - start
        inference_time_string = '%.2f ms' % (inference_time * 1000)
        logger.info("Get outputs ...")
        objs = detect.get_output(interpreter, 0.1, scale)
        logger.info("Get outputs done.")
        
        global score_with_pray
        global score_no_pray

        filename_arr = filename.split('-')
        file_number = int(filename_arr[-1].split('.')[0])

        if file_number == 0:
            score_with_pray = 0
            score_no_pray = 0

        for obj in objs:
            if int(obj.id) in [1]:
                score_with_pray = score_with_pray + Decimal(obj.score)
            if int(obj.id) in [0]:
                score_with_pray = max(Decimal(0), score_with_pray - Decimal(obj.score))
                score_no_pray = score_no_pray + Decimal(obj.score)
            if int(obj.id) in [0,1]:
                logger.info(f'Detection: {obj.score} {labels.get(obj.id, obj.id)} inference time: {inference_time_string}')

        if not objs:
            label = 'NO-DETECTION'
        else:
            label = labels.get(objs[0].id, objs[0].id).upper()
        
            
       
        if score_with_pray > ALERT_THRESHOLD:

            logger.info("****************************")
            logger.info("*                          *")
            logger.info("*         PREY ALERT       *")
            logger.info("*                          *")
            logger.info("****************************")
            start = datetime.datetime.now()
            stop = datetime.datetime.now() + datetime.timedelta(minutes=CURFEW_TIME)
            formatted_score_with_pray = "{:.2f}".format(score_with_pray)
            formatted_score_no_pray = "{:.2f}".format(score_no_pray)


            
            #Remove scheduled job if exists
            if scheduler.get_job(JOBKEY_DISABLE_CURFEW) is not None:
                scheduler.remove_job(JOBKEY_DISABLE_CURFEW)
                logger.info("already locked, will not lock again")
                msg = f"Rosine mit Maus. Confidence: {formatted_score_with_pray}/{formatted_score_no_pray}. Already locked." 
            else:
                lock = datetime.datetime.strptime(start.strftime('%H:%M'), '%H:%M')
                unlock = datetime.datetime.strptime(stop.strftime('%H:%M'), '%H:%M')
                start1 = timeit.default_timer()
                relay.lock()
                stop1 = timeit.default_timer()
                duration = str(stop1 - start1)   
                logger.info(f"Lockout delay: {duration}")
                locktime = str(datetime.datetime.now())
                logger.info(f"Lockout active: {locktime}")        
                msg = f"Rosine mit Maus. Confidence: {formatted_score_with_pray}/{formatted_score_no_pray}. Locked at {locktime}. Lockout delay: {duration}."

            #Schedule job to unlock SureFlag after defined curfew time
            scheduler.add_job(relay.unlock, 'date', run_date=stop, id=JOBKEY_DISABLE_CURFEW)
       
            #send notification to iphone
            send_notification(msg)


        if file_number == 39 and score_no_pray > ALERT_THRESHOLD:
            formatted_score_no_pray = "{:.2f}".format(score_no_pray)
            formatted_score_pray = "{:.2f}".format(score_with_pray)
            msg = f"Rosine ohne Maus, Confidence: {formatted_score_pray}/{formatted_score_no_pray}."
            #send_notification(msg)
            #logger.info("Sending notification completed.")
   

        filename = ''.join(filename_arr[:-1]) + '_' + label + '_' + filename_arr[-1] 
        s3_object_path = 'incoming/' + str(now.year) + '/' + str(now.month) + '/' + str(now.day) + '/' + str(now.hour) + '/' + filename
        detections = {'image': s3_object_path, 'objects': objs}

        detection_file = now.strftime('%Y-%m-%d') + '.txt'
        detection_path = f'detections/{detection_file}'
        s3_detection_log_path = 'incoming/' + str(now.year) + '/' + str(now.month) + '/' + str(now.day) + '/' + detection_file

        with open(detection_path, 'a+') as json_file:
            json.dump(detections, json_file)
            json_file.write(',\n')

        #Save resized img to /tmp
        tempFile = '/tmp/' + s3_object_path
       
        if not os.path.exists(os.path.dirname(tempFile)):
            os.makedirs(os.path.dirname(tempFile))
        image.save(tempFile, quality=50)

        s3_client.upload_file(tempFile, BUCKET, s3_object_path)
        logger.info(f'Upload to s3 completed: {BUCKET}/{s3_object_path} size: {os.path.getsize(tempFile)}')
        
        #remove img from /tmp
        os.remove(tempFile)

        s3_client.upload_file(detection_path, BUCKET, s3_detection_log_path)
        logger.info(f'Upload to s3 completed: {BUCKET}/{s3_detection_log_path} size: {os.path.getsize(detection_path)}') 
        logger.info(f'Score: {score_with_pray}/{score_no_pray}')

        os.remove(event.pathname)
        
        for detection_log in os.listdir('detections'):
            if detection_log != detection_file:
                logger.info(f'Delete old detection log: {detection_log}')
                os.remove('detections/' + detection_log) 

def exit_gracefully(signum, frame):
    logging.info('GRACEFUL EXIT ...')
    relay.cleanup()
    logging.info('GRACEFUL EXIT done.')
    exit()


if __name__ == "__main__":
    logger.info('Image watcher started')
    logger.info('')
    logger.info('Configuration:')
    logger.info(f'AWS Bucket: {BUCKET}')
    logger.info(f'Alert Threshold: {ALERT_THRESHOLD}')
    logger.info(f'Apple APN Token: {APNTOKEN} ')
    logger.info(f'Certfile: {CERTFILE}')
    logger.info('send push ...')
    send_notification('Imagewatcher started.')
    logger.info('push sent')

    time.sleep(1)
    relay.test()
    logger.info('***********************')



    signal.signal(signal.SIGTERM, exit_gracefully)

    labels = detect_image.load_labels('model/cat_labels.txt') 
    interpreter = detect_image.make_interpreter('model/output_tflite_graph_edgetpu.tflite')
    interpreter.allocate_tensors()

    path = '/home/pi/PycharmProjects/mausjaeger/images'

    import pyinotify
    
    wm = pyinotify.WatchManager()  # Watch Manager
    mask = pyinotify.IN_CLOSE_WRITE  # watched events

    handler = EventHandler()
    notifier = pyinotify.Notifier(wm, handler)
    wdd = wm.add_watch(path, mask, rec=True)

    try:
        notifier.loop()
    except:
        print('Unexpected error:')
        print(sys.exc_info())

