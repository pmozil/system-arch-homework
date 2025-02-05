#!/usr/bin/env python3

import hazelcast

client = hazelcast.HazelcastClient()

distributed_map = client.get_map("distributed-map").blocking()

key = "key1"
distributed_map.put_if_absent(key, 0)

for i in range(1000):
    distributed_map.lock(key)
    try:
        value = distributed_map.get(key)
        value += 1
        distributed_map.put(key, value)
    finally:
        distributed_map.unlock(key)
print("Map size:", distributed_map.size())

client.shutdown()
