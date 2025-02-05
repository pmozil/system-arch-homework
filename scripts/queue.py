#!/usr/bin/env python3


import hazelcast
import threading
import time

client = hazelcast.HazelcastClient()

queue = client.get_queue("queue")


def produce():
    for i in range(100):
        queue.offer(i)


def make_consumer(cons_num=0):
    def consume():
        for _ in range(100):
            val = 0
            if queue.size() == 0:
                time.sleep(0.1)
            if queue.size() == 0:
                break
            val = queue.take().result()
            print(f"{cons_num=}, {val=}")

    return consume


producer_thread = threading.Thread(target=produce)

cons_1 = threading.Thread(target=make_consumer(1))
cons_2 = threading.Thread(target=make_consumer(2))

cons_1.start()
cons_2.start()
producer_thread.start()

cons_1.join()
cons_2.join()
producer_thread.join()

client.shutdown()
