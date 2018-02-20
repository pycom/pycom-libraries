#!/usr/bin/env python3

# Firmware over the air update server
# Copyright Pycom Ltd.
#
# Version History
#  1.0 - Initial release (Sebastian Goscik)
#
# Setup
# -------
# This script runs a HTTP server on port 8000 that provisions over the air
# (OTA) update manifests in JSON format as well as serving the update content.
# This script should be run in a directory that contains every version of the
# end devices code, in the following structure:
#
#  - server directory
#    |- this_script.py
#    |- 1.0.0
#    |  |- flash
#    |  |   |- lib
#    |  |   |  |- lib_a.py
#    |  |   |- main.py
#    |  |   |- boot.py
#    |  |- sd
#    |     |- some_asset.txt
#    |     |- asset_that_will_be_removed.wav
#    |- 1.0.1
#    |  |- flash
#    |  |   |- lib
#    |  |   |  |- lib_a.py
#    |  |   |  |- new_lib.py
#    |  |   |- main.py
#    |  |   |- boot.py
#    |  |- sd
#    |     |- some_asset.txt
#    |- firmware_1.0.0.bin
#    |- firmware_1.0.1.bin
#
# The top level directory that contains this script can contain one of two
# things:
#     Update directory: These should be named with a version number compatible
#                       with the python LooseVersion versioning scheme
#                      (http://epydoc.sourceforge.net/stdlib/distutils.version.LooseVersion-class.html).
#                      They should contain the entire file system of the end
#                      device for the corresponding version number.
#    Firmware: These files should be named in the format "firmare_VERSION.bin",
#              where VERSION is a a version number compatible with the python
#              LooseVersion versioning scheme
#              (http://epydoc.sourceforge.net/stdlib/distutils.version.LooseVersion-class.html).
#              This file should be in the format of the appimg.bin created by
#              the pycom firmware build scripts.
#
# How to use
# -----------
# Once the directory has been setup as described above you simply need to start
# this script using python3. Once started this script will run a HTTP server on
# port 8000 (this can be changed by chaning the PORT variable below). This
# server will serve all the files in directory as expected along with one
# additional special file, "manifest.json". This file does not exist on the
# file system but is instead generated when requested and contains the required
# change to bring the end device from its current version to the latest
# available version. You can see an example of this by pointing your web
# browser at:
#    http://127.0.0.1:8000/manifest.json?current_ver=1.0.0
# The `current_ver` field at the end of the URL should be set to the current
# firmware version of the end device. The generated manifest will contain lists
# of which files are new, have changed or need to be deleted along with SHA1
# hashes of the files. Below is an example of what such a manifest might look
# like:
#
# {
#    "delete": [
#       "flash/old_file.py",
#       "flash/other_old_file.py"
#    ],
#    "firmware": {
#        "URL": "http://192.168.1.144:8000/firmware_1.0.1b.bin",
#        "hash": "ccc6914a457eb4af8855ec02f6909316526bdd08"
#    },
#    "new": [
#        {
#            "URL": "http://192.168.1.144:8000/1.0.1b/flash/lib/new_lib.py",
#            "dst_path": "flash/lib/new_lib.py",
#            "hash": "1095df8213aac2983efd68dba9420c8efc9c7c4a"
#        }
#    ],
#    "update": [
#        {
#            "URL": "http://192.168.1.144:8000/1.0.1b/flash/changed_file.py",
#            "dst_path": "flash/changed_file.py",
#            "hash": "1095df8213aac2983efd68dba9420c8efc9c7c4a"
#        }
#    ],
#    "version": "1.0.1b"
# }
#
# The manifest contains the following feilds:
#  "delete": A list of paths to files which are no longer needed
#  "firmware": The URL and SHA1 hash of the firmware image
#  "new": the URL, path on end device and SHA1 hash of all new files
#  "update": the URL, path on end device and SHA1 hash of all files which
#            existed before but have changed.
#  "version": The version number that this manifest will update the client to
#  "previous_version": The version the client is currently on before appling
#                      this update
#
# Note: The version number of the files might not be the same as the firmware.
#       The highest available version number, higher than the current client
#       version is used for both firmware and files. This may differ between
#       the two.
#
# In order for the URL's to be properly formatted you are required to send a
# "host" header along with your HTTP get request e.g:
# GET /manifest.json?current_ver=1.0.0 HTTP/1.0\r\nHost: 192.168.1.144:8000\r\n\r\n

import os
import socket
import json
import hashlib
import filecmp
import re

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from distutils.version import LooseVersion

PORT = 8000


class OTAHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        print("Got query for: {}".format(self.path))

        # Parse the URL
        path = urlparse(self.path).path
        query_components = parse_qs(urlparse(self.path).query)
        host = self.headers.get('Host')

        # Generate update manifest
        if path == "/manifest.json":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            # If query specified a version generate a diff from that version
            # otherwise return a manifest of all files
            if "current_ver" in query_components:
                current_ver = query_components["current_ver"][0]
            else:
                # This assumes there is no version lower than 0
                current_ver = '0'

            # Send manifest
            print("Generating a manifest from version: {}".format(current_ver))
            manifest = generate_manifest(current_ver, host)
            j = json.dumps(manifest,
                           sort_keys=True,
                           indent=4,
                           separators=(',', ': '))
            self.wfile.write(j.encode())

        # Send file
        else:
            try:
                with open(os.path.join('.', self.path[1:]), 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type',
                                     'application/octet-stream')
                    self.end_headers()
                    self.wfile.write(f.read())
            # File could not be opened, send error
            except IOError as e:
                self.send_error(404, "File Not Found {}".format(self.path))


# Searches the current working directory for the directory named with the
# highest version number as per LooseVersion.
def get_latest_version():
    latest = None
    for d in os.listdir('.'):
        if os.path.isfile(d):
            continue
        if latest is None or LooseVersion(latest) < LooseVersion(d):
            latest = d
    return latest


# Returns a list of all files found relative to `path`.
# Parameters:
#   path - The directory that will be traversed, results will be relative to
#          this path.
#   Ignore - A list of file names which to ignore
def get_all_paths(path, ignore=[]):
    ignore = set(ignore)
    paths = []
    for entry in os.walk(path):
        d, _, files = entry
        files = set(files).difference(ignore)
        paths += [os.path.join(d, f) for f in files]
    out = [d.replace('{}{}'.format(path, os.path.sep), '') for d in paths]
    return set(out)


# Returns a tuple containing three lists: deleted files, new_file, changed
# files.
# Parameters
#    left - The original directory
#    right - The directory with updates
#    ignore - A list o file name which to ignore
def get_diff_list(left, right, ignore=['.DS_Store', 'pymakr.conf']):
    left_paths = get_all_paths(left, ignore=ignore)
    right_paths = get_all_paths(right, ignore=ignore)
    new_files = right_paths.difference(left_paths)
    to_delete = left_paths.difference(right_paths)
    common = left_paths.intersection(right_paths)

    to_update = []
    for f in common:
        if not filecmp.cmp(os.path.join(left, f),
                           os.path.join(right, f),
                           shallow=False):
            to_update.append(f)

    return (to_delete, new_files, (to_update))


# Searches the current working directory for a file starting with "firmware_"
# followed by a version number higher than `current_ver` as per LooseVersion.
# Returns None if such a file does not exist.
# Parameters
#    path - the path to the directory to be searched
#    current_ver - the result must be higher than this version
#
def get_new_firmware(path, current_ver):
    latest = None
    for f in os.listdir(path):
        # Ignore directories
        if not os.path.isfile(f):
            continue

        try:
            m = re.search(r'firmware_([0-9a-zA-Z.]+)(?=.bin|hex)', f)
            version = m.group(1)
            if LooseVersion(current_ver) < LooseVersion(version):
                latest = f
        except AttributeError:
            # file does not match firmware naming scheme
            pass
    return latest


# Returns a dict containing a manifest entry which contains the files
# destination path, download URL and SHA1 hash.
# Parameters
#    path - The relative path to the file
#    version - The version number of the file
#    host - The server address, used in URL formatting
def generate_manifest_entry(host, path, version):
    path = "/".join(path.split(os.path.sep))
    entry = {}
    entry["dst_path"] = "/{}".format(path)
    entry["URL"] = "http://{}/{}/{}".format(host, version, path)
    data = open(os.path.join('.', version, path), 'rb').read()
    hasher = hashlib.sha1(data)
    entry["hash"] = hasher.hexdigest()
    return entry


# Returns the update manivest as a dictionary with the following entries:
#    delete - List of files that are no longer needed
#    new - A list of manifest entries for new files to be downloaded
#    update - A list of manifest entries for files that require Updating
#    version - The version that this manifest will bring the client up to
#    firmware(optional) - A manifest entry for the new firmware, if one is
#                         available.
def generate_manifest(current_ver, host):
    latest = get_latest_version()

    # If the current version is already the latest, there is nothing to do
    if latest == current_ver:
        return None

    # Get lists of difference between versions
    to_delete, new_files, to_update = get_diff_list(current_ver, latest)

    manifest = {
      "delete": list(to_delete),
      "new": [generate_manifest_entry(host, f, latest) for f in new_files],
      "update": [generate_manifest_entry(host, f, latest) for f in to_update],
      "version": latest
    }

    # If there is a newer firmware version add it to the manifest
    new_firmware = get_new_firmware('.', current_ver)
    if new_firmware is not None:
        entry = {}
        entry["URL"] = "http://{}/{}".format(host, new_firmware)
        data = open(os.path.join('.', new_firmware), 'rb').read()
        hasher = hashlib.sha1(data)
        entry["hash"] = hasher.hexdigest()
        manifest["firmware"] = entry

    return manifest


if __name__ == "__main__":
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, OTAHandler)
    httpd.serve_forever()
