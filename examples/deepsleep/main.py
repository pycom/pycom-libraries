from deepsleep import DeepSleep
import deepsleep

ds = DeepSleep()

# get the wake reason and the value of the pins during wake up
wake_s = ds.get_wake_status()
print(wake_s)

if wake_s['wake'] == deepsleep.PIN_WAKE:
    print("Pin wake up")
elif wake_s['wake'] == deepsleep.TIMER_WAKE:
    print("Timer wake up")
else:  # deepsleep.POWER_ON_WAKE:
    print("Power ON reset")

ds.enable_pullups('P17')  # can also do ds.enable_pullups(['P17', 'P18'])
ds.enable_wake_on_fall('P17') # can also do ds.enable_wake_on_fall(['P17', 'P18'])

ds.go_to_sleep(60)  # go to sleep for 60 seconds
