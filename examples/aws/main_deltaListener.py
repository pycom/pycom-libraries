from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from network import WLAN
import time
import config
import json

# Connect to wifi
wlan = WLAN(mode=WLAN.STA)
wlan.connect(config.WIFI_SSID, auth=(None, config.WIFI_PASS), timeout=5000)
while not wlan.isconnected():
    time.sleep(0.5)
print('WLAN connection succeeded!')

# Custom Shadow callback
def customShadowCallback_Delta(payload, responseStatus, token):
	payloadDict = json.loads(payload)
	print("property: " + str(payloadDict["state"]["property"]))
	print("version: " + str(payloadDict["version"]))

    # configure the MQTT client
pycomAwsMQTTShadowClient = AWSIoTMQTTShadowClient(config.CLIENT_ID)
pycomAwsMQTTShadowClient.configureEndpoint(config.AWS_HOST, config.AWS_PORT)
pycomAwsMQTTShadowClient.configureCredentials(config.AWS_ROOT_CA, config.AWS_PRIVATE_KEY, config.AWS_PUBLIC_KEY)

pycomAwsMQTTShadowClient.configureConnectDisconnectTimeout(config.CONN_DISCONN_TIMEOUT)
pycomAwsMQTTShadowClient.configureMQTTOperationTimeout(config.MQTT_OPER_TIMEOUT)

# Connect to MQTT Host
if pycomAwsMQTTShadowClient.connect():
    print('AWS connection succeeded')

deviceShadowHandler = pycomAwsMQTTShadowClient.createShadowHandlerWithName(config.THING_NAME, True)

# Listen on deltas
deviceShadowHandler.shadowRegisterDeltaCallback(customShadowCallback_Delta)

# Loop forever
while True:
	time.sleep(1)
