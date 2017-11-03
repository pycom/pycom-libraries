from machine import PWM, Pin

class _TB6612FNG_channel(object):
    _pwm_id = 0
    _pwm = PWM(0, frequency=5000)

    @classmethod
    def id(cls):
        if cls._pwm_id > 7:
            raise Exception("Cannot create more pwm channels")

        temp = cls._pwm_id
        cls._pwm_id += 1
        return temp

    def __init__(self, pin_1, pin_2, pwm_pin):
        self.pin_1 = Pin(pin_1, mode=Pin.OUT, pull=None)
        self.pin_1.value(0)

        self.pin_2 = Pin(pin_2, mode=Pin.OUT, pull=None)
        self.pin_1.value(0)

        self.pwm = TB6612FNG_channel._pwm.channel(self.id(), pin=pwm_pin, duty_cycle=1)
        self.pwm.duty_cycle(0)

    def clockwise(self):
        self.pin_1.value(1)
        self.pin_2.value(0)

    def anticlockwise(self):
        self.pin_1.value(0)
        self.pin_2.value(1)

    def short_break(self):
        self.pin_1.value(1)
        self.pin_2.value(1)

    def freewheel(self):
        self.pin_1.value(0)
        self.pin_2.value(0)

    def duty_cycle(self, *args, **kwargs):
        return self.pwm.duty_cycle(*args, **kwargs)


class TB6612FNG(object):

    def __init__(self, a_1, a_2, a_pwm, b_1, b_2, b_pwm, standby_pin):
        self._standby = Pin(standby_pin, mode=Pin.OUT, pull=None)
        self._standby.value(1)
        self.channelA = _TB6612FNG_channel(a_1, a_2, a_pwm)
        self.channelB = _TB6612FNG_channel(b_1, b_2, b_pwm)

    def standby(self, *args):
        return self._standby.value(*args)
