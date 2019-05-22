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
import threading
import hashlib
import binascii
import filecmp
import json
import time
import os

class updateHandler:
    
    def __init__(self, dev_version, latest_version, clientApp, jwt, multicast_id, ota_obj):
        self.tag = dev_version + ',' + latest_version
        self.oper_dict = None
        self.patch_dict = None
        self.dev_version = dev_version
        self.latest_version = latest_version
        self._clientApp = clientApp
        self.ota =ota_obj
        self.max_send = 5
        
        self._loraserver_jwt = jwt
        self._multicast_group_id = multicast_id
        
        self._binary_ext = []
        
        self._m_th = threading.Thread(target=self._multicast_proc)
        self._m_th.start()
        
    def print_file_operations(self, oper_dict):
        if 'delete_txt' in oper_dict:
            print('Delete text: {}'.format(oper_dict['delete_txt']))
        if 'delete_bin' in oper_dict:
            print('Delete bin: {}'.format(oper_dict['delete_bin']))
        if 'new_txt' in oper_dict:
            print('New text: {}'.format(oper_dict['new_txt']))
        if 'new_bin' in oper_dict:
            print('New binary: {}'.format(oper_dict['new_bin']))
        if 'update_txt' in oper_dict:
            print('Update {}'.format(oper_dict['update_txt']))
            
    def _create_manifest(self, oper_dict):
        manifest = {"delete":0, "update":0, "new":0}
        for key, value in oper_dict.items():
            if 'delete_txt' in key:
                manifest['delete'] = len(value)
            elif 'new_txt' in key:
                manifest['new'] = len(value)
            elif 'update_txt' in key:
                manifest['update'] = len(value)
                
        return json.dumps(manifest)
                
    def get_all_paths(self, path, ignore=[]):
        ignore = set(ignore)
        paths = []
        for entry in os.walk(path):
            d, _, files = entry
            files = set(files).difference(ignore)
            paths += [os.path.join(d, f) for f in files]
        out = [d.replace('{}{}'.format(path, os.path.sep), '') for d in paths]
        return set(out)
    
    def text_binary_lists(self, all_delete, all_new):
        path_dict = dict()

        delete_dict = self.text_binary_separation(all_delete, 'delete')
        path_dict.update(delete_dict)

        new_dict = self.text_binary_separation(all_new, 'new')
        path_dict.update(new_dict)
    
        return path_dict
    
    def text_binary_separation(self, paths, key):
        path_dict = dict()

        for path in paths:
            filename, extension = os.path.splitext(path)
            if extension in self._binary_ext:
                if key + '_bin' not in path_dict:
                    path_dict[key + '_bin'] = []
                path_dict[key + '_bin'].append(path)
            else:
                if key + '_txt' not in path_dict:
                    path_dict[key + '_txt'] = []
                path_dict[key + '_txt'].append(path)

        return path_dict
        
    def get_diff_list(self, left, right, ignore=['.DS_Store', 'pymakr.conf']):
        left_paths = self.get_all_paths(left, ignore=ignore)
        right_paths = self.get_all_paths(right, ignore=ignore)
        new_files = right_paths.difference(left_paths)
        to_delete = left_paths.difference(right_paths)
        common = left_paths.intersection(right_paths)

        paths_dict = self.text_binary_lists(to_delete, new_files)

        for f in common:
            if not filecmp.cmp(os.path.join(left, f),
               os.path.join(right, f), shallow=False):
               filename, extension = os.path.splitext(f)
               if extension in self._binary_ext:
                   # No diff update for binary files
                   if 'new_bin' not in paths_dict:
                       paths_dict['update_txt'] = []
                   paths_dict['new_bin'].append(f)
               else:
                   if 'update_txt' not in paths_dict:
                       paths_dict['update_txt'] = []
                   paths_dict['update_txt'].append(f)

        return paths_dict
    
    def _read_firware_file(self, filename):
        text = ''
        try:
            text = open(filename).read()
        except Exception as e:
            pass
        return text
    
    def _create_hash(self, data):
        h = hashlib.sha1()
        h.update(data.encode())

        return binascii.hexlify(h.digest()).decode()
    
    def chunkstring(self, string, length):
        return list(string[0+i:length+i] for i in range(0, len(string), length))
    
    def _send_delete_msg(self, filename):
        msg = bytearray()
        msg.extend(self.ota.MSG_HEADER)
        msg.extend(b',' + str(self.ota.DELETE_FILE_MSG).encode())
        msg.extend(b',' + filename.encode())
        msg.extend(b',' + self.ota.MSG_TAIL)
        
        self._clientApp.send(self._loraserver_jwt, self._multicast_group_id, msg)
    
    def _send_delete_operations(self, oper_dict):
        for key, value in oper_dict.items():
            if key in ['delete_txt', 'delete_bin']:
                for filename in value:
                    self._send_delete_msg(filename[6:])
        
    def _send_patches(self, patch_dict):
        for fname in patch_dict:
            #send file name to patch
            self._send_multicast_msg(self.ota.UPDATE_TYPE_FNAME, fname)
            time.sleep(3)
            patch_list = self.chunkstring(patch_dict[fname][0], 200)
            patch_idx = 0
            for p in patch_list:
                patch_idx += len(p)
                # send segmented patch
                self._send_multicast_msg(self.ota.UPDATE_TYPE_PATCH, p)
                time.sleep(3)
            checksum = patch_dict[fname][1]
            # Send checksum
            self._send_multicast_msg(self.ota.UPDATE_TYPE_CHECKSUM, checksum)
            time.sleep(3)
            
    def _send_multicast_msg(self, msg_type, data):
        
        msg = bytearray()
        msg.extend(self.ota.MSG_HEADER)
        msg.extend(b',' + str(msg_type).encode())
        msg.extend(b',' + data.encode())
        msg.extend(b',' + self.ota.MSG_TAIL)
        
        self._clientApp.send(self._loraserver_jwt, self._multicast_group_id, msg)
        
    def _send_manifest_msg(self):
        msg = bytearray()
        msg.extend(self.ota.MSG_HEADER)
        msg.extend(b',' + str(self.ota.UPDATE_TYPE_RESTART).encode())
        msg.extend(b',' + self.ota.MSG_TAIL)

        self._clientApp.send(self._loraserver_jwt, self._multicast_group_id, msg)
    
    def _create_file_patch(self, left, right, fileList):
        patch_dict = dict()

        for f in fileList:
            left_text = self._read_firware_file(left + '/' + f)
            right_text = self._read_firware_file(right + '/' + f)

            dmp = dmp_module.diff_match_patch()

            # Execute one reverse diff as a warmup.
            patch_lst = dmp.patch_make(left_text, right_text)
            patch_str = dmp.patch_toText(patch_lst)

            print("File name: {}".format(f))
            print("Patch : {}".format(patch_str))

            idx = f.find('/flash') + 7
            hash = self._create_hash(patch_str)
            patch_dict[f[idx:]] = (patch_str, hash)

        return patch_dict
        
    def file_operations(self, device_version, update_version):
        oper_dict = dict()

        left = self.ota.firmware_dir + '/' + device_version
        right = self.ota.firmware_dir + '/' + update_version
        if os.path.isdir(left):
            oper_dict = self.get_diff_list(left, right)
        else:
            oper_dict = self.get_diff_list('', right)

        self.print_file_operations(oper_dict)

        return oper_dict
    
    def _create_patches(self, device_version, update_version, oper_dict):
        patch_dict = dict()

        left = self.ota.firmware_dir + '/' + device_version
        right = self.ota.firmware_dir + '/' + update_version

        if 'update_txt' in oper_dict:
            update_dict = self._create_file_patch(left, right, oper_dict['update_txt'])
            patch_dict.update(update_dict)

        if 'new_txt' in oper_dict:
            new_dict = self._create_file_patch(left, right, oper_dict['new_txt'])
            patch_dict.update(new_dict)

        return patch_dict
    
    def _send_manifest_msg(self):
        manifest = self._create_manifest(self.oper_dict)
        print('Manifest: {}'.format(manifest))
        
        for i in (0, self.max_send):
            self._send_multicast_msg(self.ota.MANIFEST_MSG, manifest)
            time.sleep(4)
        
    def _multicast_proc(self):
        
        self.oper_dict = self.file_operations(self.dev_version, self.latest_version)
        self.patch_dict = self._create_patches(self.dev_version, self.latest_version, self.oper_dict)
        
        self._send_patches(self.patch_dict)
        self._send_delete_operations(self.oper_dict)
        self._send_manifest_msg()
        
        while not self.ota.is_empty_multicast_queue(self._loraserver_jwt, self._multicast_group_id):
            time.sleep(1)
        
        self.ota.clear_multicast_group(self.tag)
        
    
    
        
    
    
    
