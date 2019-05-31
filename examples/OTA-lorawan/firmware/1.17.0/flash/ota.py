#!/usr/bin/env python
#
# Copyright (c) 2019, Pycom Limited.
#
# This software is licensed under the GNU GPL version 3 or any
# later version, with permitted additional terms. For more information
# see the Pycom Licence v1.0 document supplied with this file, or
# available at https://www.pycom.io/opensource/licensing
#

import diff_match_patch as dmp_module
from watchdog import Watchdog
from machine import RTC
import ubinascii
import uhashlib
import _thread
import utime
import uos
import machine
import json

class LoraOTA:

    MSG_HEADER = b'$OTA'
    MSG_TAIL = b'*'

    FULL_UPDATE = b'F'
    DIFF_UPDATE = b'D'
    NO_UPDATE = b'N'

    UPDATE_INFO_MSG = 1
    UPDATE_INFO_REPLY = 2

    MULTICAST_KEY_REQ = 3
    MULTICAST_KEY_REPLY = 4

    LISTENING_MSG = 5
    LISTENING_REPLY = 6

    UPDATE_TYPE_FNAME = 7
    UPDATE_TYPE_PATCH = 8
    UPDATE_TYPE_CHECKSUM = 9

    DELETE_FILE_MSG = 10
    MANIFEST_MSG = 11

    def __init__(self, lora):
        self.lora = lora
        self.is_updating = False
        self.version_file = '/flash/OTA_INFO.py'
        self.update_version = '0.0.0'
        self.update_time = -1
        self.update_type = None
        self.resp_received = False
        self.update_in_progress = False
        self.operation_timeout = 10
        self.max_send = 5
        self.listen_before_sec = uos.urandom(1)[0] % 180
        self.updates_check_period = 6 * 3600

        self.mcAddr = None
        self.mcNwkSKey = None
        self.mcAppSKey = None

        self.patch = ''
        self.file_to_patch = None
        self.patch_list = dict()
        self.checksum_failure = False
        self.device_mainfest = None

        self._exit = False
        _thread.start_new_thread(self._thread_proc, ())

        self.inactivity_timeout = 120
        self.wdt = Watchdog()

        self.lora.init(self.process_message)

    def stop(self):
        self.lora.stop()
        self._exit = True

    def _thread_proc(self):
        updates_check_time = utime.time()
        self.device_mainfest = self.create_device_manifest()

        while not self._exit:
            if utime.time() > updates_check_time and self.update_time < 0:
                self.synch_request(self.check_firmware_updates)
                updates_check_time = utime.time() + self.updates_check_period

            if self.update_time > 0 and not self.update_in_progress:
                if self.update_time - utime.time() < self.listen_before_sec:
                    self.update_in_progress = True
                    self.updating_proc()

            if self.update_failed():
                print('Update failed: No data received')
                machine.reset()

            utime.sleep(2)

    def updating_proc(self):
        self.synch_request(self.get_mulitcast_keys)

        if self.mcAddr is not None:
            mulitcast_auth = (self.mcAddr, self.mcNwkSKey, self.mcAppSKey)
            self.lora.change_to_multicast_mode(mulitcast_auth)

            wdt_timeout = self.listen_before_sec + self.inactivity_timeout
            self.wdt.enable(wdt_timeout)

            self.synch_request(self.send_listening_msg)
        else:
            self.reset_update_params()

    def create_device_manifest(self):

        manifest = dict()
        manifest["delete"] = 0
        manifest["update"] = 0
        manifest["new"] = 0

        return manifest

    def reset_update_params(self):
        self.mcAddr = None
        self.mcNwkSKey = None
        self.mcAppSKey = None

        self.update_in_progress = False
        self.update_time = -1
        self.update_version = '0.0.0'

    def get_mulitcast_keys(self):
        msg = bytearray()
        msg.extend(self.MSG_HEADER)
        msg.extend(b',' + str(self.MULTICAST_KEY_REQ).encode())
        msg.extend(b',' + self.MSG_TAIL)

        self.lora.send(msg)

    def synch_request(self, func):
        attempt_num = 0
        self.resp_received = False

        while attempt_num < self.max_send and not self.resp_received:
            func()

            count_10ms = 0
            while(count_10ms <= self.operation_timeout * 100 and not self.resp_received):
                count_10ms += 1
                utime.sleep(0.01)

            attempt_num += 1

    def check_firmware_updates(self):
        msg = bytearray()
        msg.extend(self.MSG_HEADER)
        msg.extend(b',' + str(self.UPDATE_INFO_MSG).encode())

        version = self.get_current_version().encode()
        msg.extend(b',' + version)
        msg.extend(b',' + self.MSG_TAIL)

        self.lora.send(msg)
        print("Lora OTA: Request for info sent")

    def get_current_version(self):
        version = '0.0.0'
        if self.file_exists(self.version_file):
            with open(self.version_file, 'r') as fh:
                version = fh.read().rstrip("\r\n\s")
        else:
            self._write_version_info(version)

        print("Version: {}", version)

        return version

    def send_listening_msg(self):
        msg = bytearray()
        msg.extend(self.MSG_HEADER)
        msg.extend(b',' + str(self.LISTENING_MSG).encode())
        msg.extend(b',' + self.MSG_TAIL)

        self.lora.send(msg)

    def _write_version_info(self, version):
        try:
            with open(self.version_file, 'w+') as fh:
                fh.write(version)
        except Exception as e:
            print("Exception creating OTA version file")

    def file_exists(self, file_path):
        exists = False
        try:
            if uos.stat(file_path)[6] > 0:
                exists = True
        except Exception as e:
            exists = False
        return exists

    def get_msg_type(self, msg):
        msg_type = -1
        try:
            msg_type = int(msg.split(",")[1])
        except Exception as ex:
            print("Exception getting message type")

        return msg_type

    def sync_clock(self, epoc):
        try:
            rtc = RTC()
            rtc.init(utime.gmtime(epoc))
        except Exception as ex:
            print("Exception setting system data/time: {}".format(ex))
            return False

        return True

    def parse_update_info_reply(self, msg):
        self.resp_received = True

        try:
            token_msg = msg.split(",")
            self.update_type = token_msg[3].encode()
            if self.update_type in [self.FULL_UPDATE, self.DIFF_UPDATE]:
                self.update_version = token_msg[2]
                self.update_time = int(token_msg[4])

            if utime.time() < 1550000000:
                self.sync_clock(int(token_msg[5]))

        except Exception as ex:
            print("Exception getting update information: {}".format(ex))
            return False

        return True

    def parse_multicast_keys(self, msg):

        try:
            token_msg = msg.split(",")
            print(token_msg)

            if len(token_msg[2]) > 0:
                self.mcAddr = token_msg[2]
                self.mcNwkSKey = token_msg[3]
                self.mcAppSKey = token_msg[4]

            print("mcAddr: {}, mcNwkSKey: {}, mcAppSKey: {}".format(self.mcAddr, self.mcNwkSKey, self.mcAppSKey))

            self.resp_received = True
        except Exception as ex:
            print("Exception getting multicast keys: {}".format(ex))
            return False

        return True

    def parse_listening_reply(self, msg):
        self.resp_received = True

    def _data_start_idx(self, msg):
        # Find first index
        i = msg.find(",")

        #Find second index
        return msg.find(",", i + 1)

    def _data_stop_idx(self, msg):
        return msg.rfind(",")

    def get_msg_data(self, msg):
        data = None
        try:
            start_idx = self._data_start_idx(msg) + 1
            stop_idx = self._data_stop_idx(msg)
            data = msg[start_idx:stop_idx]
        except Exception as ex:
            print("Exception getting msg data: {}".format(ex))
        return data

    def process_patch_msg(self, msg):
        partial_patch = self.get_msg_data(msg)

        if partial_patch:
            self.patch += partial_patch

    def verify_patch(self, patch, received_checksum):
        h = uhashlib.sha1()
        h.update(patch)
        checksum = ubinascii.hexlify(h.digest()).decode()
        print("Computed checksum: {}".format(checksum))
        print("Received checksum: {}".format(received_checksum))

        if checksum != received_checksum:
            self.checksum_failure = True
            return False

        return True

    def process_checksum_msg(self, msg):
        checksum = self.get_msg_data(msg)
        verified = self.verify_patch(self.patch, checksum)
        if verified:
            self.patch_list[self.file_to_patch] = self.patch

        self.file_to_patch = None
        self.patch = ''

    def backup_file(self, filename):
        bak_path = "{}.bak".format(filename)

        # Delete previous backup if it exists
        try:
            uos.remove(bak_path)
        except OSError:
            pass  # There isnt a previous backup

        # Backup current file
        uos.rename(filename, bak_path)

    def process_delete_msg(self, msg):
        filename = self.get_msg_data(msg)

        if self.file_exists('/flash/' + filename):
            self.backup_file('/flash/' + filename)
            self.device_mainfest["delete"] += 1

    def get_tmp_filename(self, filename):
        idx = filename.rfind(".")
        return filename[:idx + 1] + "tmp"

    def _read_file(self, filename):

        try:
            with open('/flash/' + filename, 'r') as fh:
                return fh.read()
        except Exception as ex:
            print("Error reading file: {}".format(ex))

        return None

    def backup_file(self, filename):
        bak_path = "{}.bak".format(filename)

        # Delete previous backup if it exists
        try:
            uos.remove(bak_path)
        except OSError:
            pass  # There isnt a previous backup

        # Backup current file
        uos.rename(filename, bak_path)

    def _write_to_file(self, filename, text):
        tmp_file = self.get_tmp_filename('/flash/' + filename)

        try:
            with open(tmp_file, 'w+') as fh:
                fh.write(text)
        except Exception as ex:
            print("Error writing to file: {}".format(ex))
            return False

        if self.file_exists('/flash/' + filename):
            self.backup_file('/flash/' + filename)
        uos.rename(tmp_file, '/flash/' + filename)

        return True

    def apply_patches(self):
        for key, value in self.patch_list.items():
            self.dmp = dmp_module.diff_match_patch()
            self.patch_list = self.dmp.patch_fromText(value)

            to_patch = ''
            print('Updating file: {}'.format(key))
            if self.update_type == self.DIFF_UPDATE and \
               self.file_exists('/flash/' + key):
                to_patch = self._read_file(key)

            patched_text, success = self.dmp.patch_apply(self.patch_list, to_patch)
            if False in success:
                return False

            if not self._write_to_file(key, patched_text):
                return False

        return True

    @staticmethod
    def find_backups():
        backups = []
        for file in uos.listdir("/flash"):
            if file.endswith(".bak"):
                backups.append(file)
        return backups

    @staticmethod
    def revert():
        backup_list = LoraOTA.find_backups()
        for backup in backup_list:
            idx = backup.find('.bak')
            new_filename = backup[:idx]
            uos.rename(backup, new_filename)
        print('Error: Reverting to old firmware')
        machine.reset()

    def manifest_failure(self, msg):

        try:
            start_idx = msg.find("{")
            stop_idx = msg.find("}")

            recv_manifest = json.loads(msg[start_idx:stop_idx])

            print("Received manifest: {}".format(recv_manifest))
            print("Actual manifest: {}".format(self.device_mainfest))

            if (recv_manifest["update"] != self.device_mainfest["update"]) or \
               (recv_manifest["new"] != self.device_mainfest["new"]) or \
               (recv_manifest["delete"] != self.device_mainfest["delete"]):
               return True
        except Exception as ex:
            print("Error in manifest: {}".format(ex))
            return True

        return False

    def process_manifest_msg(self, msg):

        if self.manifest_failure(msg):
            print('Manifest failure: Discarding update ...')
            self.reset_update_params()
        if self.checksum_failure:
            print('Failed checksum: Discarding update ...')
            self.reset_update_params()
        elif not self.apply_patches():
            LoraOTA.revert()
        else:
            print('Update Success: Restarting .... ')
            self._write_version_info(self.update_version)
            machine.reset()

    def process_filename_msg(self, msg):
        self.file_to_patch = self.get_msg_data(msg)

        if self.update_type == self.DIFF_UPDATE and \
           self.file_exists('/flash/' + self.file_to_patch):
            self.device_mainfest["update"] += 1
            print("Update file: {}".format(self.file_to_patch))
        else:
            self.device_mainfest["new"] += 1
            print("Create new file: {}".format(self.file_to_patch))

        self.wdt.enable(self.inactivity_timeout)

    def update_failed(self):
        return self.wdt.update_failed()

    def process_message(self, msg):
        self.wdt.ack()

        msg_type = self.get_msg_type(msg)
        if msg_type == self.UPDATE_INFO_REPLY:
            self.parse_update_info_reply(msg)
        elif msg_type == self.MULTICAST_KEY_REPLY:
            self.parse_multicast_keys(msg)
        elif msg_type == self.LISTENING_REPLY:
            self.parse_listening_reply(msg)
        elif msg_type == self.UPDATE_TYPE_FNAME:
            self.process_filename_msg(msg)
        elif msg_type == self.UPDATE_TYPE_PATCH:
            self.process_patch_msg(msg)
        elif msg_type == self.UPDATE_TYPE_CHECKSUM:
            self.process_checksum_msg(msg)
        elif msg_type == self.DELETE_FILE_MSG:
            self.process_delete_msg(msg)
        elif msg_type == self.MANIFEST_MSG:
            self.process_manifest_msg(msg)
