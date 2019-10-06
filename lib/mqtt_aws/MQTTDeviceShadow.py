import MQTTConst as mqttConst
from machine import Timer
import json
import os
import _thread

class _basicJSONParser:

    def setString(self, srcString):
        self._rawString = srcString
        self._dictionObject = None

    def regenerateString(self):
        return json.dumps(self._dictionaryObject)

    def getAttributeValue(self, srcAttributeKey):
        return self._dictionaryObject.get(srcAttributeKey)

    def setAttributeValue(self, srcAttributeKey, srcAttributeValue):
        self._dictionaryObject[srcAttributeKey] = srcAttributeValue

    def validateJSON(self):
        try:
            self._dictionaryObject = json.loads(self._rawString)
        except ValueError:
            return False
        return True

class deviceShadow:
    def __init__(self, srcShadowName, srcIsPersistentSubscribe, srcShadowManager):

        if srcShadowName is None or srcIsPersistentSubscribe is None or srcShadowManager is None:
            raise TypeError("None type inputs detected.")
        self._shadowName = srcShadowName
        # Tool handler
        self._shadowManagerHandler = srcShadowManager
        self._basicJSONParserHandler = _basicJSONParser()
        # Properties
        self._isPersistentSubscribe = srcIsPersistentSubscribe
        self._lastVersionInSync = -1  # -1 means not initialized
        self._isGetSubscribed = False
        self._isUpdateSubscribed = False
        self._isDeleteSubscribed = False
        self._shadowSubscribeCallbackTable = dict()
        self._shadowSubscribeCallbackTable["get"] = None
        self._shadowSubscribeCallbackTable["delete"] = None
        self._shadowSubscribeCallbackTable["update"] = None
        self._shadowSubscribeCallbackTable["delta"] = None
        self._shadowSubscribeStatusTable = dict()
        self._shadowSubscribeStatusTable["get"] = 0
        self._shadowSubscribeStatusTable["delete"] = 0
        self._shadowSubscribeStatusTable["update"] = 0
        self._tokenPool = dict()
        self._dataStructureLock = _thread.allocate_lock()

    def _doNonPersistentUnsubscribe(self, currentAction):
        self._shadowManagerHandler.shadowUnsubscribe(self._shadowName, currentAction)

    def _generalCallback(self, client, userdata, message):
        # In Py3.x, message.payload comes in as a bytes(string)
        # json.loads needs a string input
        self._dataStructureLock.acquire()
        currentTopic = message.topic
        currentAction = self._parseTopicAction(currentTopic)  # get/delete/update/delta
        currentType = self._parseTopicType(currentTopic)  # accepted/rejected/delta
        payloadUTF8String = message.payload.decode('utf-8')
        # get/delete/update: Need to deal with token, timer and unsubscribe
        if currentAction in ["get", "delete", "update"]:
            # Check for token
            self._basicJSONParserHandler.setString(payloadUTF8String)
            if self._basicJSONParserHandler.validateJSON():  # Filter out invalid JSON
                currentToken = self._basicJSONParserHandler.getAttributeValue(u"clientToken")
                if currentToken is not None and currentToken in self._tokenPool.keys():  # Filter out JSON without the desired token
                    # Sync local version when it is an accepted response
                    if currentType == "accepted":
                        incomingVersion = self._basicJSONParserHandler.getAttributeValue(u"version")
                        # If it is get/update accepted response, we need to sync the local version
                        if incomingVersion is not None and incomingVersion > self._lastVersionInSync and currentAction != "delete":
                            self._lastVersionInSync = incomingVersion
                        # If it is a delete accepted, we need to reset the version
                        else:
                            self._lastVersionInSync = -1  # The version will always be synced for the next incoming delta/GU-accepted response
                    # Cancel the timer and clear the token
                    self._tokenPool[currentToken].cancel()
                    del self._tokenPool[currentToken]
                    # Need to unsubscribe?
                    self._shadowSubscribeStatusTable[currentAction] -= 1
                    if not self._isPersistentSubscribe and self._shadowSubscribeStatusTable.get(currentAction) <= 0:
                        self._shadowSubscribeStatusTable[currentAction] = 0
                        self._doNonPersistentUnsubscribe(currentAction)
                    # Custom callback
                    if self._shadowSubscribeCallbackTable.get(currentAction) is not None:
                        self._shadowManagerHandler.insertShadowCallback(self._shadowSubscribeCallbackTable[currentAction], payloadUTF8String, currentType, currentToken)
        # delta: Watch for version
        else:
            currentType += "/" + self._parseTopicShadowName(currentTopic)
            # Sync local version
            self._basicJSONParserHandler.setString(payloadUTF8String)
            if self._basicJSONParserHandler.validateJSON():  # Filter out JSON without version
                incomingVersion = self._basicJSONParserHandler.getAttributeValue(u"version")
                if incomingVersion is not None and incomingVersion > self._lastVersionInSync:
                    self._lastVersionInSync = incomingVersion
                    # Custom callback
                    if self._shadowSubscribeCallbackTable.get(currentAction) is not None:
                        self._shadowManagerHandler.insertShadowCallback(self._shadowSubscribeCallbackTable[currentAction], payloadUTF8String, currentType, None)
        self._dataStructureLock.release()

    def _parseTopicAction(self, srcTopic):
        ret = None
        fragments = srcTopic.decode('utf-8').split('/')
        if fragments[5] == "delta":
            ret = "delta"
        else:
            ret = fragments[4]
        return ret

    def _parseTopicType(self, srcTopic):
        fragments = srcTopic.decode('utf-8').split('/')
        return fragments[5]

    def _parseTopicShadowName(self, srcTopic):
        fragments = srcTopic.decode('utf-8').split('/')
        return fragments[2]

    def _timerHandler(self, args):
        srcActionName = args[0]
        srcToken = args[1]

        self._dataStructureLock.acquire()
        # Remove the token
        del self._tokenPool[srcToken]
        # Need to unsubscribe?
        self._shadowSubscribeStatusTable[srcActionName] -= 1
        if not self._isPersistentSubscribe and self._shadowSubscribeStatusTable.get(srcActionName) <= 0:
            self._shadowSubscribeStatusTable[srcActionName] = 0
            self._shadowManagerHandler.shadowUnsubscribe(self._shadowName, srcActionName)
        # Notify time-out issue
        if self._shadowSubscribeCallbackTable.get(srcActionName) is not None:
            self._shadowSubscribeCallbackTable[srcActionName]("REQUEST TIME OUT", "timeout", srcToken)
        self._dataStructureLock.release()

    def shadowGet(self, srcCallback, srcTimeout):
        self._dataStructureLock.acquire()
        # Update callback data structure
        self._shadowSubscribeCallbackTable["get"] = srcCallback
        # Update number of pending feedback
        self._shadowSubscribeStatusTable["get"] += 1
        # clientToken
        currentToken = mqttConst.UUID(bytes=os.urandom(16), version=4).urn[9:]
        self._tokenPool[currentToken] = None
        self._basicJSONParserHandler.setString("{}")
        self._basicJSONParserHandler.validateJSON()
        self._basicJSONParserHandler.setAttributeValue("clientToken", currentToken)
        currentPayload = self._basicJSONParserHandler.regenerateString()
        self._dataStructureLock.release()
        # Two subscriptions
        if not self._isPersistentSubscribe or not self._isGetSubscribed:
            self._shadowManagerHandler.shadowSubscribe(self._shadowName, "get", self._generalCallback)
            self._isGetSubscribed = True
        # One publish
        self._shadowManagerHandler.shadowPublish(self._shadowName, "get", currentPayload)
        # Start the timer
        self._tokenPool[currentToken] = Timer.Alarm(self._timerHandler, srcTimeout,arg=("get", currentToken),periodic=False)
        return currentToken

    def shadowDelete(self, srcCallback, srcTimeout):
        self._dataStructureLock.acquire()
        # Update callback data structure
        self._shadowSubscribeCallbackTable["delete"] = srcCallback
        # Update number of pending feedback
        self._shadowSubscribeStatusTable["delete"] += 1
        # clientToken
        currentToken = mqttConst.UUID(bytes=os.urandom(16), version=4).urn[9:]
        self._tokenPool[currentToken] = None
        self._basicJSONParserHandler.setString("{}")
        self._basicJSONParserHandler.validateJSON()
        self._basicJSONParserHandler.setAttributeValue("clientToken", currentToken)
        currentPayload = self._basicJSONParserHandler.regenerateString()
        self._dataStructureLock.release()
        # Two subscriptions
        if not self._isPersistentSubscribe or not self._isDeleteSubscribed:
            self._shadowManagerHandler.shadowSubscribe(self._shadowName, "delete", self._generalCallback)
            self._isDeleteSubscribed = True
        # One publish
        self._shadowManagerHandler.shadowPublish(self._shadowName, "delete", currentPayload)
        # Start the timer
        self._tokenPool[currentToken] = Timer.Alarm(self._timerHandler,srcTimeout, arg=("delete", currentToken), periodic=False)
        return currentToken

    def shadowUpdate(self, srcJSONPayload, srcCallback, srcTimeout):
        # Validate JSON
        JSONPayloadWithToken = None
        currentToken = None
        self._basicJSONParserHandler.setString(srcJSONPayload)
        if self._basicJSONParserHandler.validateJSON():
            self._dataStructureLock.acquire()
            # clientToken
            currentToken = mqttConst.UUID(bytes=os.urandom(16), version=4).urn[9:]
            self._tokenPool[currentToken] = None
            self._basicJSONParserHandler.setAttributeValue("clientToken", currentToken)
            JSONPayloadWithToken = self._basicJSONParserHandler.regenerateString()
            # Update callback data structure
            self._shadowSubscribeCallbackTable["update"] = srcCallback
            # Update number of pending feedback
            self._shadowSubscribeStatusTable["update"] += 1
            self._dataStructureLock.release()
            # Two subscriptions
            if not self._isPersistentSubscribe or not self._isUpdateSubscribed:
                self._shadowManagerHandler.shadowSubscribe(self._shadowName, "update", self._generalCallback)
                self._isUpdateSubscribed = True
            # One publish
            self._shadowManagerHandler.shadowPublish(self._shadowName, "update", JSONPayloadWithToken)
            # Start the timer
            self._tokenPool[currentToken] = Timer.Alarm(self._timerHandler, srcTimeout, arg=("update", currentToken), periodic=False)
        else:
            raise ValueError("Invalid JSON file.")
        return currentToken

    def shadowRegisterDeltaCallback(self, srcCallback):
        self._dataStructureLock.acquire()
        # Update callback data structure
        self._shadowSubscribeCallbackTable["delta"] = srcCallback
        self._dataStructureLock.release()
        # One subscription
        self._shadowManagerHandler.shadowSubscribe(self._shadowName, "delta", self._generalCallback)

    def shadowUnregisterDeltaCallback(self):
        self._dataStructureLock.acquire()
        # Update callback data structure
        del self._shadowSubscribeCallbackTable["delta"]
        self._dataStructureLock.release()
        # One unsubscription
        self._shadowManagerHandler.shadowUnsubscribe(self._shadowName, "delta")
