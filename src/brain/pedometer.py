"""
Computes type of step an bearing after each step
Types of steps:
1. Normal forward step
2. Step sideways left/right (for avoiding obstacles)
3. Turning on the spot
"""
import numpy as np
import Queue
import os
import time
# import sys
# sys.path.insert(0, '/home/seowyanyi/school/cg3002/IndoorNavigation/src')
# import communication.queueManager as qm

import src.communication.queueManager as qm

test_queue = Queue.Queue()

WINDOW_SIZE = 10
HEADING_WINDOW_SIZE = 30
AT_REST_LIMIT = 2
AT_REST_HEADING_MARGIN = 8

SWING_LIMIT = 1
TURNING_THRESHOLD = 40
FOOT_OFFSET_ANGLE = 25

AVG_DATA_RATE = 0.04
DATA_RATE_ERROR_MARGIN = 0.005
DATA_RATE_WINDOW_SIZE = 50

import threading

class Step:
    FORWARD, AT_REST = range(2)

class PedometerThread(threading.Thread):
    def __init__(self, threadName, imuQueue, pedometerQueue):
        threading.Thread.__init__(self)
        self.threadName = threadName
        self.imuQueue = imuQueue
        self.pedometerQueue = pedometerQueue

    def run(self):
        print 'Starting {} thread'.format(self.threadName)
        start_pedometer_processing(self.imuQueue, self.pedometerQueue, WINDOW_SIZE, AT_REST_LIMIT, SWING_LIMIT, False)
        print 'Exited {} thread'.format(self.threadName)

def init_test_queue():
    with open('acc_x_with_sensors.txt') as f:
        for line in f:
            test_queue.put(qm.IMUData(int(line), 0, 0, 0, 0))

def init_compass_test_queue():
    with open('compass.txt') as f:
        for line in f:
            test_queue.put(qm.IMUData(0, 0, 0, int(line), 0))

def is_two_seconds_passed(prev_two_seconds):
    curr = int(time.time())
    if curr % 2 == 0 and curr > prev_two_seconds:
        return {'status':True, 'curr': curr}
    return {'status':False, 'curr': curr}

def isWithinRange(expected, actual, errorMargin):
    return abs(expected - actual) <= errorMargin


def start_pedometer_processing(dataQueue, pedometerQueue, windowSize, atRestLimit, swingLimit, debug):
    steps = 0
    data = []
    headingData = []

    swing_count = 0
    at_rest_count = 0

    previouslyAtRest = True

    # data rate stuff
    dataRateList = []
    prev_two_seconds = int(time.time())

    while True:
        if debug and dataQueue.qsize() <= 1:
            break

        # Get data from imu and populate the relevant lists
        imuData = dataQueue.get(True)
        x = imuData.xAxis
        heading = imuData.heading - FOOT_OFFSET_ANGLE
        if heading < 0:
            heading += 360
        medianHeading = heading

        if len(data) > windowSize:
            data.pop(0)
        data.append(x)

        if len(headingData) > HEADING_WINDOW_SIZE:
            headingData.pop(0)
            medianHeading = np.median(headingData)
        headingData.append(heading)

        if len(dataRateList) > DATA_RATE_WINDOW_SIZE:
            dataRateList.pop(0)
        dataRateList.append(imuData.dataRate)

        if len(data) < windowSize:
            continue
        
        # keeps track of a list of data rates. Compare with the expected average every two seconds
        # Also check whether user is at rest every two seconds
        checkTwoSecs = is_two_seconds_passed(prev_two_seconds)

        if checkTwoSecs['status']:
            prev_two_seconds = checkTwoSecs['curr']
            actual_rate = np.mean(dataRateList)
            if not isWithinRange(actual_rate, AVG_DATA_RATE, DATA_RATE_ERROR_MARGIN):
                print 'Data rate is off. Actual: {} s'.format(actual_rate)
            if np.amax(headingData) - np.amin(headingData) < AT_REST_HEADING_MARGIN:
                print 'User currently at rest. {} deg'.format(medianHeading)
                pedometerQueue.put({'type': Step.AT_REST, 'actual_bearing': medianHeading})
                continue

        # Check whether a step is taken
        if is_downward_swing(data):
            swing_count += 1
        else:
            swing_count = 0

        if is_at_rest(data):
            at_rest_count += 1
        else:
            at_rest_count = 0

        if debug:
            line = get_equation_of_line(data)
            gradient = line[0]
            write_to_gradient_file(gradient)

        # count as at rest between steps
        if at_rest_count > atRestLimit:
            previouslyAtRest = True
            at_rest_count = 0

        # User took a step forward
        if previouslyAtRest and swing_count > swingLimit:
            print 'Step taken {} deg'.format(medianHeading)
            steps += 1
            pedometerQueue.put({'type': Step.FORWARD, 'actual_bearing': medianHeading})
            swing_count = 0
            previouslyAtRest = False
            at_rest_count = 0
            if debug:
                write_to_step_file('1')
        elif debug:
            write_to_step_file('0')

    print 'steps: {}'.format(steps)

def write_to_gradient_file(data):
    with open("gradient.txt", "a") as myfile:
        myfile.write(str(data) + '\n')

def write_to_step_file(data):
    with open("step.txt", "a") as myfile:
        myfile.write(data + '\n')


def get_equation_of_line(data):
    x = np.arange(0,len(data))
    y = np.array(data)
    return np.polyfit(x,y,1)

def is_downward_swing(data):
    line = get_equation_of_line(data)
    gradient = line[0]
    return gradient < -0.30

def is_at_rest(data):
    line = get_equation_of_line(data)
    gradient = abs(line[0])
    return gradient <= 0.1

def clean_up():
    try:
        os.remove("step.txt")
    except OSError:
        pass
    try:
        os.remove("gradient.txt")
    except OSError:
        pass

if __name__ == "__main__":
    clean_up()
    # init_test_queue()
    init_compass_test_queue()
    start_pedometer_processing(test_queue,Queue.Queue(), WINDOW_SIZE, AT_REST_LIMIT, SWING_LIMIT, True)
