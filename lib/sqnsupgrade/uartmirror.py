from machine import UART
import time
import os

os.dupterm(None)

repl_u = UART(0, baudrate=921600, timeout_chars=10)

if 'FiPy' in os.uname().sysname:
    lte_u = UART(1, baudrate=921600, pins=('P20', 'P18', 'P19', 'P17'), timeout_chars=10)
else:
    lte_u = UART(1, baudrate=921600, pins=('P5', 'P98', 'P7', 'P99'), timeout_chars=10)

while True:
    if repl_u.any():
        lte_u.write(repl_u.read())
    if lte_u.any():
        repl_u.write(lte_u.read())
    time.sleep_ms(2)
