# Systems arch homework 4: Microservices with kafka

## Setup

I'll skip hazelcast installation, since  it's the same as in the previous lab.

You'll also need to install deps:

```bash
python3 -m venv venv

source venv/bin/activate

pip install requests fastapi hazelcast-python-client uvicorn kafka-python
```


## Config server

The config server stays the same as the previous task. It does the same,
but now the config has more services.

```python
@app.get("/services/{service_name}")
async def get_service_instances(service_name: str):
    """Get all instances of a specific service"""
    if service_name not in services:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return services[service_name]
```

## Facade

Facade is also the same as the last time, except for sending messages to kafka.
Here are the endpoints:

```python
class MessageRequest(BaseModel):
    msg: str

@app.post("/messages")
async def send_message(message_request: MessageRequest):
    """
    Receives a message from client, generates UUID, and forwards to logging service
    """
    repeats = 3

    while repeats > 0:
        logging_service_url = f"{get_service_url('logging')}/messages"
        response = requests.post(logging_service_url, json=payload)
        if response.status_code == 200:
            return {"id": message_id, "status": "Message sent successfully"}
        repeats -= 1

@app.get("/messages")
async def get_messages():
    """
    Retrieves messages from both logging service and messages service
    """
    ...
```

## Logger

It's mostly the same, except for the fact that now communication happens with http and not hazelcast straight up
Here are the notable poitns:

```python
class MessageRequest(BaseModel):
    id: str
    msg: str

@app.post("/messages")
async def log_message(message: MessageRequest):
    """
    Receives a message from facade service, stores it in a hash table, and logs to console
    """
    ...

@app.get("/messages")
async def get_messages():
    """
    Returns all messages stored in the hash table as a string
    """
    ...

@app.on_event("shutdown")
def shutdown_event():
    """
    Shutdown Hazelcast client on application exit
    """
    hz_client.shutdown()
```

## General arch

I set up a docker-compose script. Here it is:
```docker
version: "3.8"

services:
  # Controllers
  controller-1:
    image: apache/kafka:latest
    container_name: controller-1
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: controller
      KAFKA_LISTENERS: CONTROLLER://:9093
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@controller-1:9093,2@controller-2:9093,3@controller-3:9093
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0

  controller-2:
    image: apache/kafka:latest
    container_name: controller-2
    environment:
      KAFKA_NODE_ID: 2
      KAFKA_PROCESS_ROLES: controller
      KAFKA_LISTENERS: CONTROLLER://:9093
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@controller-1:9093,2@controller-2:9093,3@controller-3:9093
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0

  controller-3:
    image: apache/kafka:latest
    container_name: controller-3
    environment:
      KAFKA_NODE_ID: 3
      KAFKA_PROCESS_ROLES: controller
      KAFKA_LISTENERS: CONTROLLER://:9093
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@controller-1:9093,2@controller-2:9093,3@controller-3:9093
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0

  broker-1:
    image: apache/kafka:latest
    container_name: broker-1
    ports:
      - 29092:9092
    environment:
      KAFKA_NODE_ID: 4
      KAFKA_PROCESS_ROLES: broker
      KAFKA_LISTENERS: 'PLAINTEXT://:19092,PLAINTEXT_HOST://:9092'
      KAFKA_ADVERTISED_LISTENERS: 'PLAINTEXT://broker-1:19092,PLAINTEXT_HOST://localhost:29092'
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@controller-1:9093,2@controller-2:9093,3@controller-3:9093
      KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS: 0
    depends_on:
      - controller-1
      - controller-2
      - controller-3

  # Message Service (two instances)
  message-service-1:
    build:
      context: ./message-service
    container_name: message-service-1
    environment:
      KAFKA_BROKER_URL: "broker-1:19092"
      KAFKA_TOPIC: "messages"
    depends_on:
      - broker-1
    networks:
      - kafka-net

  message-service-2:
    build:
      context: ./message-service
    container_name: message-service-2
    environment:
      KAFKA_BROKER_URL: "broker-1:19092"
      KAFKA_TOPIC: "messages"
    depends_on:
      - broker-1
    networks:
      - kafka-net

  # Hazelcast Service
  hazelcast:
    image: hazelcast/hazelcast:latest
    container_name: hazelcast
    environment:
      - JAVA_OPTS=-Dhazelcast.local.localAddress=hazelcast
    ports:
      - "5701:5701"
    networks:
      - kafka-net

  logging_service_1:
    build:
      context: ./logging_service
    container_name: logging_service_1
    depends_on:
      - hazelcast

  logging_service_2:
    build:
      context: ./logging_service
    container_name: logging_service_2
    depends_on:
      - hazelcast
    networks:
      - kafka-net

  logging_service_3:
    build:
      context: ./logging_service
    container_name: logging_service_3
    depends_on:
      - hazelcast
    networks:
      - kafka-net

  # Config server
  config_server:
    build:
      context: ./config_server
    container_name: config_server
    networks:
      - kafka-net

  # Facade Service
  facade-service:
    build:
      context: ./facade-service
    container_name: facade-service
    environment:
      KAFKA_BROKER_URL: "broker-1:19092"
      KAFKA_TOPIC: "messages"
    depends_on:
      - logging_service_1
      - logging_service_2
      - logging_service_3
      - message-service-1
      - message-service-2
      - config_server
    networks:
      - kafka-net
    ports:
      - "8000:8000"

networks:
  kafka-net:
```

## Results

I used curl and created this script:
```
curl -X POST "http://localhost:8000/messages" -H "Content-Type: application/json" -d '{"msg":"Hello, Kafka!"}'

curl -X GET "http://localhost:8000/messages"
```

Here are the logs for ten times:
 ### Facade

```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     172.19.0.1:48262 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48276 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48292 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48304 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48308 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48318 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48330 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48344 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48356 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48360 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48364 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48372 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48374 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48390 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48404 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.1:48414 - "POST /messages HTTP/1.1" 200 OK
```

### Logger 1

No logs lol
```
```

### Logger 2
```
Successfully registered with config server: 172.19.0.5:8000
INFO:     172.19.0.8:60946 - "GET / HTTP/1.1" 404 Not Found
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
INFO:     172.19.0.6:60154 - "POST /messages HTTP/1.1" 422 Unprocessable Content
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Received message - ID: a316ca62-5f03-47ac-9869-23cf38f23c99, Content: Hello, World!
INFO:     172.19.0.6:42476 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 66117caa-7f08-42d2-ae57-62de96c09785, Content: Hello, World!
INFO:     172.19.0.6:42488 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: e18cfa01-23c6-4240-81b6-eb66c18f2ef2, Content: Hello, World!
INFO:     172.19.0.6:42490 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 862d6c1e-c63d-4427-9ebd-5aec8d0768be, Content: Hello, World!
INFO:     172.19.0.6:42498 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 7293cc44-08ad-4f0c-924a-ce607706d0ef, Content: Hello, World!
INFO:     172.19.0.6:42500 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 361ca9c0-f794-4632-b41c-4f5cf7c2b474, Content: Hello, World!
INFO:     172.19.0.6:42516 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: f220d50f-d65a-407e-ba15-d7499f2a193f, Content: Hello, World!
INFO:     172.19.0.6:42520 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 08125baa-d5d2-432b-a97f-baf58c6b22d4, Content: Hello, World!
INFO:     172.19.0.6:42532 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 600404e3-6b4c-4415-b967-ad71a511f650, Content: Hello, World!
INFO:     172.19.0.6:42546 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 56d6ae2d-4db5-45e8-82e0-dfbb087f335e, Content: Hello, World!
INFO:     172.19.0.6:42550 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.6:42556 - "GET /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Received message - ID: e2f4d14d-1e98-4c21-a6e7-9099e830d2c7, Content: Hello, World!
INFO:     172.19.0.8:43136 - "POST /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Received message - ID: 8daba08c-15fd-4666-9ce1-66695b90ad85, Content: Hello, World!
INFO:     172.19.0.8:44816 - "POST /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Received message - ID: 886b410e-d0e9-45c8-9a19-a254cbc29a40, Content: Hello, World!
INFO:     172.19.0.8:36500 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 331be715-47c4-4c96-b314-39e36f6cd6eb, Content: Hello, World!
INFO:     172.19.0.8:36512 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 8799020e-e8a0-4100-81b2-c0a9e6602d54, Content: Hello, World!
INFO:     172.19.0.8:36516 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:36518 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:36522 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:34042 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:34058 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:34060 - "GET /messages HTTP/1.1" 200 OK
Received message - ID: 9d2529a6-93c8-42d3-9415-6faedb53f166, Content: Hello, World!
INFO:     172.19.0.8:45446 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 98c43d65-6d5b-4ba1-89dc-95b650dfa86f, Content: Hello, World!
INFO:     172.19.0.8:45454 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 493cfd33-58f7-4711-8fbf-c7edccec41de, Content: Hello, World!
INFO:     172.19.0.8:45460 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: d61e8825-1402-4a46-b6f2-71350a1cda0d, Content: Hello, World!
INFO:     172.19.0.8:45472 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: dca505f9-7048-4962-8bea-77647cae4c30, Content: Hello, World!
INFO:     172.19.0.8:45478 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: c9a6ec6b-53d7-4353-ba96-74231090f933, Content: Hello, World!
INFO:     172.19.0.8:45486 - "POST /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Received message - ID: aadd0195-d14d-4d61-8874-0c58435898e9, Content: Hello, Kafka!
INFO:     172.19.0.8:42180 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 9b724fe0-8ce9-4e5f-871a-25f7e8a0193d, Content: Hello, Kafka!
INFO:     172.19.0.8:42182 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: c2c022e8-9768-4d2c-a070-e4dbd843cdc9, Content: Hello, Kafka!
INFO:     172.19.0.8:42194 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 07c8e984-9817-427c-beba-e2ee869e850b, Content: Hello, Kafka!
INFO:     172.19.0.8:42208 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 867bb6ec-bc00-40ca-aa8f-11423c38a5cc, Content: Hello, Kafka!
INFO:     172.19.0.8:42222 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: a2fa4f91-acb1-436b-b0db-145082b9f0a5, Content: Hello, Kafka!
INFO:     172.19.0.8:42230 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: b7493938-5237-49e5-aded-fd090d1f70a0, Content: Hello, Kafka!
INFO:     172.19.0.8:42238 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: e51a5a8a-3bd2-4f73-913d-56d99cc39ee3, Content: Hello, Kafka!
INFO:     172.19.0.8:42242 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 2a3003dd-eb45-4ae4-bfbe-9d857dcc550c, Content: Hello, Kafka!
INFO:     172.19.0.8:42256 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: c6feb428-27f5-4447-b779-fdf8e991b660, Content: Hello, Kafka!
INFO:     172.19.0.8:42272 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 072e6845-2746-417f-a90b-6aaa768f18d0, Content: Hello, Kafka!
INFO:     172.19.0.8:42278 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: cc251160-cf09-4162-af19-ad326bb49e6c, Content: Hello, Kafka!
INFO:     172.19.0.8:42290 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 4ba8f8d4-3b51-4234-80f4-ea3f602471a4, Content: Hello, Kafka!
INFO:     172.19.0.8:42302 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 50d9be4d-ebbf-41c9-a0b9-f6968bfd014b, Content: Hello, Kafka!
INFO:     172.19.0.8:42306 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: d0e161a5-23d9-43f0-9388-2dd168a1ad5e, Content: Hello, Kafka!
INFO:     172.19.0.8:42318 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 96c95c46-32ef-402d-97cc-dcc792ee23de, Content: Hello, Kafka!
INFO:     172.19.0.8:42330 - "POST /messages HTTP/1.1" 200 OK
```

### Logger 3

```
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
INFO:     172.19.0.7:55348 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.7:55364 - "GET /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
INFO:     172.19.0.6:36916 - "POST /messages HTTP/1.1" 422 Unprocessable Content
INFO:     172.19.0.6:49508 - "POST /messages HTTP/1.1" 422 Unprocessable Content
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
INFO:     172.19.0.6:52730 - "POST /messages HTTP/1.1" 422 Unprocessable Content
INFO:     172.19.0.6:49810 - "GET / HTTP/1.1" 404 Not Found
INFO:     172.19.0.6:49824 - "GET /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.5:8000
INFO:     172.19.0.8:45418 - "POST /messages HTTP/1.1" 422 Unprocessable Content
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
INFO:     172.19.0.6:59494 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.6:59506 - "GET /messages HTTP/1.1" 200 OK
Received message - ID: 3063c9df-3a04-4d59-95d1-642beada9633, Content: Hello, World!
INFO:     172.19.0.6:45318 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 1e5ce4c2-c58c-469d-a4f2-6d737fe2cc49, Content: Hello, World!
INFO:     172.19.0.6:45334 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 92426e84-6d05-43df-824f-33c7056ba73a, Content: Hello, World!
INFO:     172.19.0.6:45342 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 78cc7e17-2fe7-442d-836c-f9d3c8142450, Content: Hello, World!
INFO:     172.19.0.6:45350 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 93720b7c-7a79-4b05-809e-7bd0ffd6fe79, Content: Hello, World!
INFO:     172.19.0.6:45358 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.6:45370 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.6:45374 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.6:45382 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.6:45396 - "GET /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Successfully registered with config server: 172.19.0.5:8000
Received message - ID: cc2575c7-4b10-422f-971a-0ef2ae4daa3a, Content: Hello, World!
INFO:     172.19.0.8:35216 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 27948927-0656-44d7-9d24-05eaf0a2016b, Content: Hello, World!
INFO:     172.19.0.8:35218 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 732ec9cb-a376-4227-a4fd-3370e1d9c6b4, Content: Hello, World!
INFO:     172.19.0.8:35224 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 9b189963-ccf4-4470-8af8-06d03196ed7d, Content: Hello, World!
INFO:     172.19.0.8:35234 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 44ea9326-30f4-4e75-b7e4-854d74ca41e1, Content: Hello, World!
INFO:     172.19.0.8:35244 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:35248 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:60514 - "GET /messages HTTP/1.1" 200 OK
Received message - ID: a5eeddda-485e-463e-83ed-653c20f849c7, Content: Hello, World!
INFO:     172.19.0.8:33752 - "POST /messages HTTP/1.1" 200 OK
Successfully registered with config server: 172.19.0.4:8000
Successfully registered with config server: 172.19.0.4:8000
Received message - ID: 7820a59f-5926-4554-8500-e7ce4d5df34c, Content: Hello, Kafka!
INFO:     172.19.0.8:42514 - "POST /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:56314 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:40980 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:40994 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:40998 - "GET /messages HTTP/1.1" 200 OK
Received message - ID: 90d76cb5-7a12-4202-8083-565f648a9384, Content: Hello, Kafka!
INFO:     172.19.0.8:41006 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 1ad05300-8491-478d-aee9-97bcd0ed133a, Content: Hello, Kafka!
INFO:     172.19.0.8:41012 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 5cc23f29-7f23-4507-8a05-7c5a43b89d0a, Content: Hello, Kafka!
INFO:     172.19.0.8:41022 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: c818e8b1-a9bf-4f58-be86-ba8f4ee28746, Content: Hello, Kafka!
INFO:     172.19.0.8:41038 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 13be5058-1309-409c-ac2d-fe120da68dda, Content: Hello, Kafka!
INFO:     172.19.0.8:41042 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 66d0a48c-c6b6-410a-ae0a-7b4800ed4f42, Content: Hello, Kafka!
INFO:     172.19.0.8:41046 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 173f2ac9-f075-476c-b00f-56f9936f1051, Content: Hello, Kafka!
INFO:     172.19.0.8:41058 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 5603bd64-490a-47ba-9057-c6d0cfafce27, Content: Hello, Kafka!
INFO:     172.19.0.8:41064 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 84321ef1-bef8-4959-b5ac-009472127cf6, Content: Hello, Kafka!
INFO:     172.19.0.8:41066 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 030afd42-47f0-4bff-937a-c6cb49247c09, Content: Hello, Kafka!
INFO:     172.19.0.8:41070 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 00ebc7a5-af15-4bf3-97a2-e2ae53998d96, Content: Hello, Kafka!
INFO:     172.19.0.8:41078 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: ce506cad-dc8e-42db-acfc-4731aeee6e54, Content: Hello, Kafka!
INFO:     172.19.0.8:41094 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: 72703527-1073-417e-be59-a690f9cce974, Content: Hello, Kafka!
INFO:     172.19.0.8:41100 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: c9aa8b99-4b74-4e48-a819-eadd421acbbc, Content: Hello, Kafka!
INFO:     172.19.0.8:41104 - "POST /messages HTTP/1.1" 200 OK
Received message - ID: b4eee40c-a21c-41a4-b659-d75cabbcbc1e, Content: Hello, Kafka!
INFO:     172.19.0.8:41110 - "POST /messages HTTP/1.1" 200 OK
```
### Messages 1

```
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     172.19.0.8:51592 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:51602 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:53660 - "GET /messages HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     172.19.0.8:52412 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:42648 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:42658 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:42674 - "GET /messages HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Message 3

```
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     172.19.0.8:58620 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:59668 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:59676 - "GET /messages HTTP/1.1" 200 OK
INFO:     172.19.0.8:59692 - "GET /messages HTTP/1.1" 200 OK
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [1]
/app/consumer.py:44: DeprecationWarning:
        on_event is deprecated, use lifespan event handlers instead.

        Read more about it in the
        [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

  @app.on_event("startup")
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Conclusions

Kafka is a pretty useful service. It's great for communication, but i had a lot of trouble setting up the network until i remembered that addressing is not done with `localhost` but `<container_name>`
