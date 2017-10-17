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

# user specified callback functions
def customShadowCallback_Update(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Update request " + token + " time out!")
    if responseStatus == "accepted":
        payloadDict = json.loads(payload)
        print("Update request with token: " + token + " accepted!")
        print("property: " + str(payloadDict["state"]["desired"]["property"]))
    if responseStatus == "rejected":
        print("Update request " + token + " rejected!")

def customShadowCallback_Delete(payload, responseStatus, token):
    if responseStatus == "timeout":
        print("Delete request " + token + " time out!")
    if responseStatus == "accepted":
        print("Delete request with token: " + token + " accepted!")
    if responseStatus == "rejected":
        print("Delete request " + token + " rejected!")

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

# Delete shadow JSON doc
deviceShadowHandler.shadowDelete(customShadowCallback_Delete, 5)

# Update shadow in a loop
loopCount = 0
while True:
    JSONPayload = '{"state":{"desired":{"property":' + str(loopCount) + '}}}'
    deviceShadowHandler.shadowUpdate(JSONPayload, customShadowCallback_Update, 5)
    loopCount += 1
    time.sleep(5)
