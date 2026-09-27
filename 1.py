import pyfirmata
import time

board = pyfirmata.Arduino("COM5")
pin = 7

board.digital[pin].mode = pyfirmata.OUTPUT

while True:
    board.digital[pin].write(0)   # ON
    time.sleep(2)
    board.digital[pin].write(1)   # OFF
    time.sleep(2)