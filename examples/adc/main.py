from machine import ADC
import time

adc = ADC(0)
adc_c = adc.channel(pin='P13')

while True:
    value = adc_c.value()
    print("ADC value:" + str(value))
    time.sleep(1)
