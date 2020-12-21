import time
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM) # GPIO Nummern statt Board Nummern
 
RELAIS_1_GPIO = 26
wait_delay = 0.2
GPIO.setup(RELAIS_1_GPIO, GPIO.OUT) # GPIO Modus zuweisen


def lock(unlock=False):
    maxloopindex=2
    if unlock:
        maxloopindex=3
        print("UNLOCKING SUREFLAP ...")
    else:
        print("LOCKING SUREFLAP ...")
    for x in range(maxloopindex):
        GPIO.output(RELAIS_1_GPIO, GPIO.HIGH)
        time.sleep(wait_delay)
        GPIO.output(RELAIS_1_GPIO, GPIO.LOW)
        time.sleep(wait_delay+0.1)

def unlock():
    lock(unlock=True)

def test():
    print("::::: TESTING SUREFLAP LOCKING ... ::::")
    lock()
    time.sleep(2.0)
    unlock()
    print(":::: TESTING SUREFLAP COMPLETED. ::::")
