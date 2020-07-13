'''
Copyright (c) 2020, Pycom Limited.
This software is licensed under the GNU GPL version 3 or any
later version, with permitted additional terms. For more information
see the Pycom Licence v1.0 document supplied with this file, or
available at https://www.pycom.io/opensource/licensing
'''
import ubinascii
import json

from network import LoRa
import machine
import time

try:
    from pymesh_debug import print_debug
except:
    from _pymesh_debug import print_debug

__version__ = '2'
"""
__version__ = '2'
* added BR_ena, BR_prio

__version__ = ''
* first release

"""

class PymeshConfig:

    CONFIG_FILENAME = "/flash/pymesh_config.json"

    ############################################################
    # DEFAULT SETTINGS

    # LoRa region is one of LoRa.US915, LoRa.EU868, LoRa.AS923, LoRa.AU915
    LORA_REGION = LoRa.EU868

    # frequency expressed in Hz, for EU868 863000000 Hz, for US915 904600000 Hz
    LORA_FREQ = const(869000000)

    # bandwidth options are: LoRa.BW_125KHZ, LoRa.BW_250KHZ or LoRa.BW_500KHZ
    LORA_BW = LoRa.BW_500KHZ

    # spreading factor options are 7 to 12
    LORA_SF = const(7)

    # Pymesh 128b key, used for auth. and encryption
    KEY = "112233"

    # if true, Pymesh is auto-started
    AUTOSTART = True
    DEBUG_LEVEL = 5

    # if true, it will start as BLE Server, to be connected with mobile app
    BLE_API = False
    BLE_NAME_PREFIX = "PyGo "

    ############################################################
    # Border router preference priority
    BR_PRIORITY_NORM = const(0)
    BR_PRIORITY_LOW = const(-1)
    BR_PRIORITY_HIGH = const(1)

    # if true then this node is Border Router
    BR_ENABLE = False
    # the default BR priority
    BR_PRIORITY = BR_PRIORITY_NORM

    def write_config(pymesh_config, force_restart = False):
        cf = open(PymeshConfig.CONFIG_FILENAME, 'w')
        cf.write(json.dumps(pymesh_config))
        cf.close()

        if force_restart:
            print_debug(3, "write_config force restart")
            time.sleep(1)
            machine.deepsleep(1000)

    def check_mac(pymesh_config):
        lora = LoRa(mode=LoRa.LORA, region= LoRa.EU868)
        MAC = int(str(ubinascii.hexlify(lora.mac()))[2:-1], 16)

        if pymesh_config.get('MAC') is None:
            # if MAC config unspecified, set it to LoRa MAC
            print_debug(3, "Set MAC in config file as " + str(MAC))
            pymesh_config['MAC'] = MAC
            PymeshConfig.write_config(pymesh_config, False)
        else:
            mac_from_config = pymesh_config.get('MAC')
            if mac_from_config != MAC:
                print_debug(3, "MAC different"+ str(mac_from_config) + str(MAC))
                pymesh_config['MAC'] = MAC
                # if MAC in config different than LoRa MAC, set LoRa MAC as in config file
                fo = open("/flash/sys/lpwan.mac", "wb")
                mac_write=bytes([(MAC >> 56) & 0xFF, (MAC >> 48) & 0xFF, (MAC >> 40) & 0xFF, (MAC >> 32) & 0xFF, (MAC >> 24) & 0xFF, (MAC >> 16) & 0xFF, (MAC >> 8) & 0xFF, MAC & 0xFF])
                fo.write(mac_write)
                fo.close()
                # print_debug(3, "reset")
                PymeshConfig.write_config(pymesh_config, False)

        print_debug(3, "MAC ok" + str(MAC))

    def read_config():
        file = PymeshConfig.CONFIG_FILENAME
        pymesh_config = {}
        error_file = True

        try:
            import json
            f = open(file, 'r')
            jfile = f.read()
            f.close()
            try:
                pymesh_config = json.loads(jfile.strip())
                # pymesh_config['cfg_msg'] = "Pymesh configuration read from {}".format(file)
                error_file = False
            except Exception as ex:
                print_debug(1, "Error reading {} file!\n Exception: {}".format(file, ex))
        except Exception as ex:
            print_debug(1, "Final error reading {} file!\n Exception: {}".format(file, ex))

        if error_file:
            # config file can't be read, so it needs to be created and saved
            pymesh_config = {}
            print_debug(3, "Can't find" +str(file) + ", or can't be parsed as json; Set default settings and reset")
            # don't write MAC, just to use the hardware one
            pymesh_config['LoRa'] = {"region": PymeshConfig.LORA_REGION,
                                    "freq": PymeshConfig.LORA_FREQ,
                                    "bandwidth": PymeshConfig.LORA_BW,
                                    "sf": PymeshConfig.LORA_SF}
            pymesh_config['Pymesh'] = {"key": PymeshConfig.KEY}
            pymesh_config['autostart'] = PymeshConfig.AUTOSTART
            pymesh_config['debug'] = PymeshConfig.DEBUG_LEVEL
            pymesh_config['ble_api'] = PymeshConfig.BLE_API
            pymesh_config['ble_name_prefix'] = PymeshConfig.BLE_NAME_PREFIX
            pymesh_config['br_ena'] = PymeshConfig.BR_ENABLE
            pymesh_config['br_prio'] = PymeshConfig.BR_PRIORITY

            PymeshConfig.check_mac(pymesh_config)
            print_debug(3, "Default settings:" + str(pymesh_config))
            PymeshConfig.write_config(pymesh_config, True)

        PymeshConfig.check_mac(pymesh_config)
        print_debug(3, "Settings:" + str(pymesh_config))
        return pymesh_config
