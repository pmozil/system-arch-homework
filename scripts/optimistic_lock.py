#!/usr/bin/env python3

import hazelcast

client = hazelcast.HazelcastClient()

distributed_map = client.get_map("distributed-map").blocking()

key = "key2"
distributed_map.put_if_absent(key, 0)

i = 0
while i < 1000:
    value = distributed_map.get(key)
    if distributed_map.replace_if_same(key, value, value + 1):
        i += 1
print("Map size:", distributed_map.size())

client.shutdown()
