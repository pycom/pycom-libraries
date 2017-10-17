
# wifi configuration
WIFI_SSID = 'my wifi ssid'
WIFI_PASS = 'my wifi password'

# AWS general configuration
AWS_PORT = 8883
AWS_HOST = 'aws host'
AWS_ROOT_CA = '/flash/cert/aws root CA'
AWS_PUBLIC_KEY = '/flash/cert/aws public key'
AWS_PRIVATE_KEY = '/flash/cert/aws private key'

################## Subscribe / Publish client #################
CLIENT_ID = 'PycomPublishClient'
TOPIC = 'PublishTopic'
OFFLINE_QUEUE_SIZE = -1
DRAINING_FREQ = 2
CONN_DISCONN_TIMEOUT = 10
MQTT_OPER_TIMEOUT = 5
LAST_WILL_TOPIC = 'PublishTopic'
LAST_WILL_MSG = 'To All: Last will message'

####################### Shadow updater ########################
#THING_NAME = "my thing name"
#CLIENT_ID = "ShadowUpdater"
#CONN_DISCONN_TIMEOUT = 10
#MQTT_OPER_TIMEOUT = 5

####################### Delta Listener ########################
#THING_NAME = "my thing name"
#CLIENT_ID = "DeltaListener"
#CONN_DISCONN_TIMEOUT = 10
#MQTT_OPER_TIMEOUT = 5
