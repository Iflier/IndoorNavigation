import sprotapi as sprotapi
import sprotpkt as sprotpkt
# import serialmod as serialmod
import threading
import src.communication.queueManager as qm
import Queue

DATA_SIZE = 16
DEST_PORT_CRUNCHER = 9003
DEST_PORT_ALERT = 9004
SERIALMOD_BAUDRATE = 115200

ACC_X_DATA_FILE = "acc_x.txt"
ACC_Y_DATA_FILE = "acc_y.txt"
ACC_Z_DATA_FILE = "acc_z.txt"
COMPASS_DATA_FILE = "compass.txt"

sprotapi.SPROTInit("/dev/ttyAMA0", baudrate=SERIALMOD_BAUDRATE)

PRINT_EVERY_N_ITER = 10
canPrint = False
iterationCount = 0
sonar1Data = 0      # Left Sonar
sonar2Data = 0      # Right Sonar
sonar3Data = 0      # Middle Sonar
compassData = 0
footsensData = 0
LIMIT_DATA_RATE = 10

class SensorManagerThread(threading.Thread):
    def __init__(self, threadName, imuQueue, middleSonarQueue, leftSonarQueue, rightSonarQueue):
        threading.Thread.__init__(self)
        self.threadName = threadName
        self.imuQueue = imuQueue
        self.middleSonarQueue = middleSonarQueue
        self.leftSonarQueue = leftSonarQueue
        self.rightSonarQueue = rightSonarQueue

    def run(self):
        print 'Starting {} thread'.format(self.threadName)
        read_packet(LIMIT_DATA_RATE, self.imuQueue)
        print 'Exited {} thread'.format(self.threadName)


# Extract sonar data from generic packet
def convertPacketToSonarData(strpkt):
    sonarData = { strpkt[0] : strpkt[2:5] }
    return sonarData

# Strips trailing zeroes if required
def removeNullChars(str):
    maxIndex = 7
    for i in range(maxIndex):
        if(str[i].isdigit() or str[i] == '.'):
            maxIndex = i

    return str[0:maxIndex+1]
    
def read_packet(limit, imuQueue):
    counter = 1
    while True :

        # Read a packet
        pkt = sprotapi.SPROTReceive()

        try :
                # Check for error
                if (not isinstance(pkt, sprotpkt.SPROTPacket)) :
                    print "recv error"
                else :
                    # pkt.printPacket()
                    strpkt = pkt.data.decode("ascii")

                    if (strpkt[0] == b'a') :
                        data = strpkt.split(":")
                        xyz = data[1].split(",")

                        if counter == 1:
                            print "c:" + xyz[0] + " x:" + xyz[1] + " y:" + xyz[2] + "z:" + xyz[3]
                            imuQueue.put(qm.IMUData(xyz[1], xyz[2], xyz[3]))
                            with open(ACC_X_DATA_FILE, "a") as myfile:
                                myfile.write(xyz[1] + '\n')
                            with open(ACC_Y_DATA_FILE, "a") as myfile:
                                myfile.write(xyz[2] + '\n')
                            with open(ACC_Z_DATA_FILE, "a") as myfile:
                                myfile.write(xyz[3] + '\n')
                            with open(COMPASS_DATA_FILE, "a") as myfile:
                                myfile.write(xyz[0] + '\n')
                        if counter == limit:
                            counter = 0
                        counter += 1

                        x = int(xyz[0])
                        y = int(xyz[1])
                        z = int(xyz[2])
                        # qm.IMUData(xAxis=x, yAxis=y, zAxis=z)


                    elif (strpkt[0] == b'2') :
                        sonar2Data = convertPacketToSonarData(strpkt)
                    elif (strpkt[0] == b'3') :
                        sonar3Data = convertPacketToSonarData(strpkt)
                    elif (strpkt[0] == b'C') :
                        compassData = strpkt[2:5]

        except:
            sprotapi.SPROTClose()
            sprotapi.SPROTInit("/dev/ttyAMA0", baudrate=SERIALMOD_BAUDRATE)

if __name__ == "__main__":
    read_packet(LIMIT_DATA_RATE, Queue.Queue())
