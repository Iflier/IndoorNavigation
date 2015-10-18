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
import timeit
import time
#import sys
#sys.path.insert(0, '/home/seowyanyi/school/cg3002/IndoorNavigation/src')
#import communication.queueManager as qm

import src.communication.queueManager as qm

test_queue = Queue.Queue()

WINDOW_SIZE = 20
AT_REST_LIMIT = 5
AT_REST_LIMIT_LONG = 10
SWING_LIMIT = 1
SECS_BETW_BEARING_READINGS = 0.5
TURNING_THRESHOLD = 40
FOOT_OFFSET_ANGLE = 25
#todo: minus ~5 degrees from bearing due to angle of foot

import threading

class Step:
    FORWARD, TURN, AT_REST = range(3)

class PedometerThread(threading.Thread):
    def __init__(self, threadName, imuQueue, pedometerQueue, keypressQueue, audioQueue):
        threading.Thread.__init__(self)
        self.threadName = threadName
        self.imuQueue = imuQueue
        self.pedometerQueue = pedometerQueue
        self.keypressQueue = keypressQueue
        self.audioQueue = audioQueue

    def run(self):
        print 'Starting {} thread'.format(self.threadName)
        start_pedometer_processing(self.imuQueue, self.pedometerQueue, WINDOW_SIZE, AT_REST_LIMIT, SWING_LIMIT, False,
                                   self.keypressQueue, self.audioQueue)
        print 'Exited {} thread'.format(self.threadName)

def init_test_queue():
    with open('b.txt') as f:
        for line in f:
            test_queue.put(qm.IMUData(int(line), 0, 0, 0))

def start_pedometer_processing(dataQueue, pedometerQueue, windowSize, atRestLimit, swingLimit, debug, keypressQueue, audioQueue):
    steps = 0
    data = []
    previous_bearing = None
    time_bearing_taken = None

    swing_count = 0
    at_rest_count = 0
    at_rest_count_long = 0
    previouslyAtRest = True

    pause_pedo = False

    while True:
        if debug and dataQueue.qsize() <= 1:
            break

        try:
            pause_pedo = keypressQueue.get(False)
            if pause_pedo:
                print '     ***   PEDOMETER PAUSED      ***'
                audioQueue.put('Pedometer paused')
            else:
                print '     ***   PEDOMETER RESTARTED      ***'
                audioQueue.put('Pedometer restarted')

        except Queue.Empty:
            pass

        if pause_pedo:
            time.sleep(0.5)
            continue


        # Get data from imu and populate the relevant lists
        imuData = dataQueue.get(True)
        x = imuData.xAxis
        heading = imuData.heading - FOOT_OFFSET_ANGLE

        if previous_bearing is None:
            previous_bearing = heading
            time_bearing_taken = timeit.default_timer()

        if len(data) > windowSize:
            data.pop(0)
        data.append(x)
        if len(data) < windowSize:
            continue


        # check whether we are making a turn
        if timeit.default_timer() - time_bearing_taken >= SECS_BETW_BEARING_READINGS:
            time_bearing_taken = timeit.default_timer()
            if abs(heading - previous_bearing) > TURNING_THRESHOLD:
                previous_bearing = heading
                print 'User made a turn to {} deg'.format(heading)
                pedometerQueue.put({'type': Step.TURN, 'actual_bearing': heading})
                continue

        # detect the movement type
        if is_downward_swing(data):
            swing_count += 1
        else:
            swing_count = 0

        if is_at_rest(data):
            at_rest_count += 1
            at_rest_count_long += 1
        else:
            at_rest_count = 0
            at_rest_count_long = 0

        if debug:
            line = get_equation_of_line(data)
            gradient = line[0]
            write_to_gradient_file(gradient)

        # count as at rest between steps
        if at_rest_count > atRestLimit:
            previouslyAtRest = True
            at_rest_count = 0

        # User is at rest
        if at_rest_count_long > AT_REST_LIMIT_LONG:
            print 'User currently at rest. {} deg'.format(heading)
            pedometerQueue.put({'type': Step.AT_REST, 'actual_bearing': heading})
            at_rest_count_long = 0
            continue

        # User took a step forward
        if previouslyAtRest and swing_count > swingLimit:
            print 'Step taken {} deg'.format(heading)
            steps += 1
            pedometerQueue.put({'type': Step.FORWARD, 'actual_bearing': heading})
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
    return gradient <= 0.15

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
    init_test_queue()
    start_pedometer_processing(test_queue,Queue.Queue(), WINDOW_SIZE, AT_REST_LIMIT, SWING_LIMIT, True, Queue.Queue(), Queue.Queue())
