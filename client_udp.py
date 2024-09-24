import serial
import queue
import time
import datetime
import socket
from mqttMod import MQTTMOD
ser = serial.Serial('/dev/ttyAMA0', 115200)    #Open port with baud rate
uart_read_queue = queue.Queue(maxsize=50)
uart_write_queue = queue.Queue()
HOST = '114.34.73.26' #serverIP
PORT = 8001 #server port

server_addr = (HOST, PORT)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def decode_data(data):
    clear_data = data[:]
    now = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=8)))
    packet = clear_data + str(datetime.datetime.utcnow() + datetime.timedelta(hours = 8)) + 'r1' 
    return packet

class Uart_Read:
    def __init__(self, read_queue, write_queue, ser):
        self.read_queue = read_queue
        self.write_queue = write_queue
        self.ser = ser
        self.if_upload = False
        self.state = 0 #用來鎖定相機觸發
        self.mqtt = MQTTMOD()
        self.mqtt.start()
    def run(self):
        while True:
            try:
                data = self.ser.readline().decode()
                if (uart_write_queue.qsize() > 0):
                    uart_write_data = uart_write_queue.get()
                    ser.write(uart_write_data.decode('hex'))

                packet = decode_data(data)
                print(len(packet))
                if len(packet) == 233:                      # 辨識封包是否為手環封包
                    json_pakage = self.decode_json(packet)
                    if self.if_upload == True :
                        """"""

                    area_position = json_pakage["Area"]
                    posture = json_pakage["Posture_state"]
                    safe_mac = json_pakage["safe_Mac"]
                    print("="*10)
                    print(f"Posture:{posture}"+"="*5+f"Area:{area_position}"+"="*5+f"Mac:{safe_mac}")
                    if area_position == 1 and posture == 1 and self.state == 0:# 
                        self.mqtt.send_message(safe_mac,"shot")
                        self.state = 1 # 將狀態切換至用餐
                        print("用餐")
                        
                    elif posture == 2 and self.state == 1:
                        """"""
                        self.mqtt.send_message(safe_mac,"stop")
                        self.state = 0 #將狀態切換至結束
                        print("結束")

                    time.sleep(.03)
            except Exception as e:
                print(e)
    # 緊急封包判斷
    def judgeState(self,raw_data):
        if raw_data[0:3] == '$0C': #一般封包$0C
            safe_sos = 0
            return safe_sos
        elif raw_data[0:3] == '$4C': #緊急封包$4C
            safe_sos = 1
            return safe_sos
        
    # 將十六進制的值轉為有正負號的十進制值
    def twosComplement_hex(self,hexval):
        bits = 16 # Number of bits in a hexadecimal number format
        val = int(hexval, bits)
        if val & (1 << (bits-1)):
            val -= 1 << bits
        return val


    def tmpIdentify(self,raw_data, state):
        if state == 1:
            tmp = str(int(raw_data[71:73],16))+str(int(raw_data[73:75],16))
            return tmp
        elif state == 2:
            tmp = str(int(raw_data[71:75],16))
            return tmp
        elif state == 3:
            tmp = str(int(raw_data[71:75],16))
            return tmp
        else:
            return "tmpIdentify error"
    def decode_json(self,indata):
        """"""
        raw_data = indata
        
        band_Mac = raw_data[5:17]
        safe_Mac = raw_data[189:201]
        state = int(raw_data[97:99],16) # 1為舊手環, 2為新手環, 3為蓋德
        tmp = self.tmpIdentify(raw_data, state)
        sleep = int(raw_data[87:89],16)*60 + int(raw_data[89:91],16)
        raw_data_document = {
            # 協定換算方式:ex 血壓35~36 => 35*2-1=69 => 所以血壓的位置位於raw_data的第69個，有4個bytes，69~72為血壓的判讀區域，剩下的以此類推。
            'Time' : time,
            'state' : self.judgeState(raw_data), #確認封包狀態
            'raspberry_Mac' : raw_data[-2:],
            'safe_Mac' : raw_data[189:201],
            'safe_battery': int(raw_data[201:203],16),
            'Posture_state' : int(raw_data[173:175],16),
            'band_Mac' : raw_data[5:17],
            #-----------------事與物(暫時沒用到)--------------
            # 'Sensor' : int(raw_data[33:34],16),
            # 'MybeBehavior' : int(raw_data[34:35],16),
            # 'Room' : int(raw_data[35:36],16),
            # 'Furniture' : int(raw_data[36:37],16),
            # 'Behavior' : int(raw_data[37:38],16),
            # 'BehaviorQulity' : int(raw_data[38:39],16),
            # 'Alertvalue' : int(raw_data[39:51],16),
            #-----------------手環生理訊號--------------------
            'HR' : int(raw_data[51:53],16),
            'Bloodpressure_SBP' : int((raw_data[53:55]),16),
            'Bloodpressure_DBP' : int((raw_data[55:57]),16),
            'Step' : int((raw_data[57:59] + raw_data[59:61]),16),
            'Mileage' : int((raw_data[61:63] + raw_data[63:65]),16)/1000,
            'Blood_oxygen' : int((raw_data[65:67]),16),
            'Calories' : int((raw_data[67:69] + raw_data[69:71]),16),
            'band_battery' : int(raw_data[85:87],16),
            'Temperature' : tmp[0:2] + '.' + tmp[2:4], # 體溫
            'Sleep' : sleep, # 單位:min
            'Nap' : int(raw_data[91:93],16),
            'SOS' : int(raw_data[93:95],16),
            'Button' : int(raw_data[95:97],16),
            'New&Old' : state,
            #----------------手環生化訊號(暫時沒用到)----------
            # 'Takemedicine1' : int(raw_data[113:115],16),
            # 'Takemedicine2' : int(raw_data[115:117],16),
            # 'Bloodsugar' : int(raw_data[117:119],16),
            # 'Lacticacid' : int(raw_data[119:121],16),
            #-----------------護身符--------------------------
            'ACC_X' : self.twosComplement_hex(raw_data[121:125])/512,
            'ACC_Y' : self.twosComplement_hex(raw_data[125:129])/512,
            'ACC_Z' : self.twosComplement_hex(raw_data[129:133])/512,
            'ACC_total' : self.twosComplement_hex(raw_data[133:137])/512,
            'roll16' : self.twosComplement_hex(raw_data[137:141])/100,
            'pitch16' : self.twosComplement_hex(raw_data[141:145])/100,
            'yaw16' : self.twosComplement_hex(raw_data[145:149])/100,
            'MAG_X' : self.twosComplement_hex(raw_data[149:153]),
            'MAG_Y' : self.twosComplement_hex(raw_data[153:157]),
            'MAG_Z' : self.twosComplement_hex(raw_data[157:161]),
            'MAG_total' : self.twosComplement_hex(raw_data[161:165]),
            'Press_16' : (self.twosComplement_hex(raw_data[165:169])+80000)/100,
            'Ambient temperature' : self.twosComplement_hex(raw_data[169:173])*0.0625, #環境溫度
            'Azimuth16' : self.twosComplement_hex(raw_data[175:179]),
            'Direction' : int(raw_data[179:181],16), #方位
            'RSSI' : self.twosComplement_hex(raw_data[181:185]), #護身符與Beacon的距離
            'Point' : int(raw_data[185:187],16), #Beacon定位點
            'Area' : int(raw_data[187:189],16) #靠近幾號Beacon
        }
        return raw_data_document
dd = Uart_Read(uart_read_queue, uart_write_queue, ser)
print("start")
dd.run()