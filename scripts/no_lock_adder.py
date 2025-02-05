#!/usr/bin/env python3

import hazelcast

client = hazelcast.HazelcastClient()

distributed_map = client.get_map("distributed-map")

distributed_map.put_if_absent("key", 0).result()

for i in range(1000):
    val: int = distributed_map.get("key").result()
    val += 1
    distributed_map.put("key", val)

print("Map size:", distributed_map.size().result())

client.shutdown()
