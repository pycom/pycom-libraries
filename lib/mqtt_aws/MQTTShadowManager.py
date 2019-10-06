import _thread
import time

class shadowManager:

    def __init__(self, MQTTClient):
        if MQTTClient is None:
            raise ValueError("MQTT Client is none")

        self._mqttClient = MQTTClient
        self._subscribe_mutex = _thread.allocate_lock()

    def getClientID(self):
        return self._mqttClient.getClientID()

    def _getDeltaTopic(self, shadowName):
        return "$aws/things/" + str(shadowName) + "/shadow/update/delta"

    def _getNonDeltaTopics(self, shadowName, actionName):
        generalTopic = "$aws/things/" + str(shadowName) + "/shadow/" + str(actionName)
        acceptTopic = "$aws/things/" + str(shadowName) + "/shadow/" + str(actionName) + "/accepted"
        rejectTopic = "$aws/things/" + str(shadowName) + "/shadow/" + str(actionName) + "/rejected"

        return (generalTopic, acceptTopic, rejectTopic)

    def shadowPublish(self, shadowName, shadowAction, payload):
        (generalTopic, acceptTopic, rejectTopic) = self._getNonDeltaTopics(shadowName, shadowAction)
        self._mqttClient.publish(generalTopic, payload, 0, False)

    def shadowSubscribe(self, shadowName, shadowAction, callback):
        self._subscribe_mutex.acquire()
        if shadowAction == "delta":
            deltaTopic = self._getDeltaTopic(shadowName)
            self._mqttClient.subscribe(deltaTopic, 0, callback)
        else:
            (generalTopic, acceptTopic, rejectTopic) = self._getNonDeltaTopics(shadowName, shadowAction)
            self._mqttClient.subscribe(acceptTopic, 0, callback)
            self._mqttClient.subscribe(rejectTopic, 0, callback)
        time.sleep(2)
        self._subscribe_mutex.release()

    def shadowUnsubscribe(self, srcShadowName, srcShadowAction):
        self._subscribe_mutex.acquire()
        currentShadowAction = _shadowAction(srcShadowName, srcShadowAction)
        if shadowAction == "delta":
            deltaTopic = self._getDeltaTopic(shadowName)
            self._mqttClient.unsubscribe(deltaTopic)
        else:
            (generalTopic, acceptTopic, rejectTopic) = self._getNonDeltaTopics(shadowName, shadowAction)
            self._mqttClient.unsubscribe(acceptTopic)
            self._mqttClient.unsubscribe(rejectTopic)
        self._subscribe_mutex.release()

    def insertShadowCallback(self, callback, payload, status, token):
        self._mqttClient.insertShadowCallback(callback, payload, status, token)
