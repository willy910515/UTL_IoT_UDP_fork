import socket 
from PyQt5 import  QtCore
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from retry import retry
class MQTTMOD(QtCore.QThread):

    control = QtCore.pyqtSignal(str)
    def __init__(self, parent=None):
        super().__init__(parent) 
        self.client = None
        print("MQTT模組初始化")
    def run(self):
        """"""
        try:

            self.client = mqtt.Client()
            self.client.username_pw_set(username="utl_food",password="utl2041")
            self.client.connect("114.32.9.225", 1883, 60)
            self.client.on_connect = self.on_connect
            self.client.on_message = self.on_message
            
            
            self.client.loop_start()
        except socket.timeout as e:
            print(e)        
    @retry(tries=3, delay=1)
    def on_connect(self,client, userdata, flags, rc):
        # print("Connected with result code "+str(rc))
        if rc == 0:
            self.client.subscribe("Food/Camera")
            print("connect mqtt broker success")

            # 將訂閱主題寫在on_connet中
            # 如果我們失去連線或重新連線時
            # 地端程式將會重新訂閱
            
# 當接收到從伺服器發送的訊息時要進行的動作
    def on_message(self,client, userdata, msg):
        # 轉換編碼utf-8才看得懂中文
        print(msg.topic+" "+ msg.payload.decode('utf-8'))
        if msg.payload.decode('utf-8') == 'shot':
            self.control.emit('shot')
        elif msg.payload.decode('utf-8') == 'stop':
            self.control.emit('stop')
    def send_message(self,MacAddress,message):
        
        publish.single(
          topic=f"Food/{MacAddress}/Camera",
          payload= message,
          hostname="114.32.9.225",
          
          port=1883,
          auth={'username':'utl_food','password':'utl2041'})
    def killThread(self):
        self.wait()
        self.client.disconnect()
if __name__=="__main__":
    mq = MQTTMOD()
    mq.run()
    mq.send_message()

