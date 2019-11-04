# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing

import uos
import time
import ujson

__version__ = '1'
"""
first draft
"""

class Statistics:
    """ Class for keeping profiling statistics inside Pymesh """

    TYPE_MESSAGE = const(0)
    FILENAME = '/flash/statistics.json'

    def __init__(self, meshaging):
        self.meshaging = meshaging

        # dictionary with all ongoing statistics, having key a unique 32bit number
        self.dict = {}
        self._restore_data()
        self.sleep_function = None

    def _restore_data(self):
        """ restore all data from file """
        try:
            f = open(self.FILENAME, 'r')
        except:
            print('no ', self.FILENAME)
            return
        # with open(self.FILENAME, 'r+') as f:
        for line in f:
            try:
                stat = StatJob(ujson.loads(line.strip()))
                if stat.valid:
                    self.dict[stat.id] = stat
                    print('Stat added: ', stat.to_string())
            except:
                print("parsing failed ", line)
                continue                
        f.close()
        print("Statistics file ok?!")
        pass

    def save_all(self):
        """ save all data as json into a file """
        # if len(self.dict) > 0:
        with open(self.FILENAME, 'w') as f:
            for _, job in self.dict.items():
                f.write(ujson.dumps(job.to_dict()) + '\n')
        pass

    def _get_new_id(self):
        id = 1
        while (1):
            x = self.dict.get(id, None)
            if x is None:
                break
            id = id + 1
        return id

    def num(self):
        return len(self.dict)

    def add_stat_mess(self, data):
        ret = False
        id = self._get_new_id()
        print("id:", id)
        stat = StatJob([id, TYPE_MESSAGE, data])
        if stat.valid:
            self.dict[id] = stat
            ret = stat.status()
        print("Stat: added ", ret)
        return ret

    def process(self):
        for id, job in self.dict.items():
            # print(job.to_string())
            if job.state == job.STATE_STARTED:

                # send new message
                job.last_ack = False
                job.last_send = time.time()
                job.last_mess_num = job.last_mess_num + 1
                payload = "Test %d, pack from node %d, #%d/%d"%(job.id, job.mac, job.last_mess_num, job.repetitions)
                print("Stat: " + payload)                
                self.meshaging.send_message(job.mac, 0, payload, id*1000+job.last_mess_num, job.last_send)

                job.state = job.STATE_WAIT_ANS

            elif job.state == job.STATE_WAIT_ANS:
                # check if last message was ack
                if job.last_ack == False:
                    job.last_ack = self.meshaging.mesage_was_ack(job.mac, id*1000+job.last_mess_num)
                    # job.last_ack could be False (0 int value) or True (1 int value)
                    job.ack_num = job.ack_num + job.last_ack
                    print("Stat: last mess ack? ", job.last_ack)
                
                # check if it's ACK or time for a new message
                if job.last_ack or time.time() - job.last_send > job.period:
                    print("Timeout or ACK", job.to_string())
                    # check if job is done
                
                    if job.repetitions == job.last_mess_num:
                        job.state = job.STATE_DONE
                        print("Stat: done")
                        self.save_all() # just to be safe
                        continue # no need to send another message

                    job.state = job.STATE_STARTED
                    self.sleep(job.s1, job.s2)
                    
    def status(self, id):
        data = list()
        if id == 0: # print all jobs
            data = list()
            for _, job in self.dict.items():
                data.append(job.status())
        elif id == 1234: # print all Active jobs
            for _, job in self.dict.items():
                if job.state != job.STATE_DONE:
                    data.append(job.status())
        elif id == 123456: # DELETE all done jobs
            for idx, job in self.dict.items():
                if job.state == job.STATE_DONE:
                    del self.dict[idx]
        elif id == 123456789: # DELETE ALL jobs
            for idx, job in self.dict.items():
                del self.dict[idx]
        else: # print a specific job
            stat = self.dict.get(id, None)
            data.append(stat.status())
        # print(stat.to_string())
        return data

    def sleep(self, s1, s2):
        # nothing to do if s2 is 0
        if s2 == 0 or s2 < s1 or not self.sleep_function:
            print("no sleep")
            return
        # random seconds between s1 and s2 (including them)
        t = s1 + (uos.urandom(1)[0] % (s2 - s1 + 1))
        self.sleep_function(t)

class StatJob:
    """ Class for keeping a message statistics """
    STATE_STARTED = const(0)
    STATE_WAIT_ANS = const(1)
    STATE_DONE = const(2)

    def __init__(self, data):
        self.type = 0 # by default message TEXT type
        self.state = STATE_STARTED
        self.valid = False
        self.last_send = 0
        self.last_ack = False
        self.last_mess_num = 0
        self.ack_num = 0 # num of ack messages
        self.s1 = 0
        self.s2 = 0

        if type(data) is dict:
            self._init_dict(data)
        elif type(data) is list:
            self._init_list(data)
        self.last_send = time.time() - self.period

    def _init_list(self, data_list):
        id, jobtype, data =  data_list
        self.id = id
        self.type = jobtype
        
        try:
            self.mac = data['mac']
            self.repetitions = data['n']
            self.period = data['t']
            self.s1 = data.get('s1', 0)
            self.s2 = data.get('s2', 0)
        except:
            print("StatJob init failed")
            print(data)
            return
        self.valid = True
        self.last_send = -self.period

    def to_string(self):
        text = "%d: %s Send %d mess, to %d, every %d sec\n\
            Sent %d,ack %d"%(self.id, 
            ('Done' if self.state == STATE_DONE else 'Ongoing'),
            self.repetitions, self.mac,
            self.period, self.last_mess_num, self.ack_num)
        return text
    
    def status(self):
        data = {'id':self.id, 'm': self.mac, 'left': (self.repetitions - self.last_mess_num),
        'sc': str(self.ack_num)+':'+str(self.last_mess_num)}
        #'done': self.state,
        return data

    def to_dict(self):
        d = {'id':self.id, 
        'mac':self.mac, 
        'period': self.period,
        'repetitions': self.repetitions,
        'ack_num': self.ack_num, 
        'state': self.state,
        'last_send': self.last_send, 
        'last_ack': self.last_ack,
        'last_mess_num': self.last_mess_num,
        'type': self.type,
        's1': self.s1,
        's2': self.s2,
        }
        return d
    
    def _init_dict(self, d):
        self.valid = True
        try:
            self.id = d['id']
            self.mac = d['mac']
            self.period = d['period']
            self.repetitions = d['repetitions']
            self.ack_num = d['ack_num']
            self.state = d['state']
            self.last_send = d['last_send']
            self.last_ack = d['last_ack']
            self.last_mess_num = d['last_mess_num']
            self.type = d['type']
            self.s1 = d['s1']
            self.s2 = d['s2']
        except:
            print("error parsing ", d)
            self.valid = False
        return
