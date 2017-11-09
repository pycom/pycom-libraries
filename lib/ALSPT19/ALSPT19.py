from machine import ADC
import time

class ALSPT19(object):
    def __init__(self, pin_name):
        adc = ADC()
        self.pin = adc.channel(pin=pin_name, attn=ADC.ATTN_11DB, bits=12)
        self.threshold = None

    def calibrate(self, samples=300):
        max_val = 0
        for _ in range(samples):
            val = self.pin()
            if val > max_val:
                max_val = val
            time.sleep_ms(10)

        self.threshold = max_val * 1.2

    def is_on(self):
        if self.pin() > self.threshold:
            return True
        return False
