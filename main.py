#! /usr/bin/env python

import time
import alsaaudio
import audioop
import threading

from Queue import Queue

# A queue to transfer noise data between the main thread (listen) and the
# adjust thread (adjust_vol).
noise_q = Queue()

# If the stop object is listened through the noise_q, it means that the thread
# must be stopped.
stop = object()


def listen(mic, sleeptime=0.05):
    """ Listen to the mic and put noise level into the noise_q queue. After
    each data pushed, sleep during `sleeptime` secs.
    """

    while True:
        # Read data from the mic.
        l, data = mic.read()
        if l:
            try:
                # Transform the data to a noise level.
                noise = audioop.max(data, 2)

                # Put the noise level to the queue.
                noise_q.put(noise)
            except audioop.error as e:
                # Ignore that specific error.
                if e.message != "not a whole number of frames":
                    raise e

        # zzzzzZZZZZZzzzzzzzz...
        time.sleep(sleeptime)


def adjust_vol(headphone, avg_interval=4):
    """ Listen to the noise_q queue for noise data. When there're
    `avg_interval` elements read, compute the average noise level value. Adjust
    the headphone value based on this average.
    """

    # A list to register each noise value until the avg is computed.
    noises = []

    while True:
        # Block until there's data on the noise_q queue.
        noise = noise_q.get()

        if noise is stop:
            # Exit if the data listened is the stop object.
            break
        elif noise:
            # If there's data, append it to the noises list.
            noises.append(noise)

        if len(noises) == avg_interval:
            # It's time to compute the average.
            avg = sum(noises) / len(noises)

            # Adjust the volume based on the avg value.
            vol = avg / 10
            vol = 10 if vol < 10 else vol
            vol = 70 if vol > 100 else vol

            # Here we go, set the volume !
            headphone.setvolume(vol)

            # Clear the list
            noises[:] = []


if __name__ == '__main__':
    try:
        # Get the mic interface.
        mic = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NONBLOCK)

        # Get the headphone mixer.
        headphone = alsaaudio.Mixer()

        # Start the adjust_vol thread.
        t1 = threading.Thread(target=adjust_vol, args=(headphone,))
        t1.start()

        # Listen to the mic on the main thread.
        noise = listen(mic)

        # Wait until the adjust_vol thread is finished before exiting.
        t1.join()
    except KeyboardInterrupt:
        # Push the stop object into the noise_q to stop the thread.
        noise_q.put(stop)
