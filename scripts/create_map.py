#!/usr/bin/env python3

import hazelcast
import random

client = hazelcast.HazelcastClient()

distributed_map = client.get_map("distributed-map")

for i in range(1000):
    distributed_map.set(f"{i}", f"{random.randint(0, 10000)}").result()

print("Map size:", distributed_map.size().result())

client.shutdown()
