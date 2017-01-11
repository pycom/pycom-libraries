import _thread
import time

def th_func(delay, id):
    while True:
        time.sleep(delay)
        print('Running thread %d' % id)

for i in range(2):
    _thread.start_new_thread(th_func, (i + 1, i))