# Systems arch homework 3: Microservices with hazelcast

## Setup

I'll skip hazelcast installation, since  it's the same as in the previous lab.

You'll also need to install deps:

```bash
python3 -m venv venv

source venv/bin/activate

pip install requests fastapi hazelcast-python-client uvicorn
```


## Config server

The config server i made reads services from a JSON file
and returns the IP addresses for the service. Here is the fastapi endpoint:

```python
@app.get("/services/{service_name}")
async def get_service_instances(service_name: str):
    """Get all instances of a specific service"""
    if service_name not in services:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return services[service_name]
```

## Facade

Facade is the same as the last time, except for getting IP addresses
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

It's also mostly the same, except for initialization and closing of the client.

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


I also added a script for initialization:
```bash

#!/usr/bin/env sh

# Create the services_config.json file first (optional)
echo '{
  "logging": [
    {
      "ip": "localhost",
      "port": 8001
    },
    {
      "ip": "localhost",
      "port": 8011
    },
    {
      "ip": "localhost",
      "port": 8111
    }
  ],
  "messages": [
    {
      "ip": "localhost",
      "port": 8002
    }
  ]
}' > services_config.json

echo "Starting Config Server..."
python config_server.py &
sleep 3

echo "Starting first Logging Service instance on port 8001..."
python logger.py --port 8001 &
sleep 2

echo "Starting second Logging Service instance on port 8011..."
python logger.py --port 8011 &
sleep 2

echo "Starting second Logging Service instance on port 8011..."
python logger.py --port 8111 &
sleep 2

# echo "Starting Messages Service on port 8002..."
# python messages_service.py --port 8002 &
# sleep 2

echo "Starting Facade Service on port 8000..."
python facade.py &
sleep 2

echo "All services are now running!"
echo "You can use the following commands to test:"
echo "POST a message: curl -X POST \"http://localhost:8000/messages\" -H \"Content-Type: application/json\" -d '{\"msg\":\"Hello, distributed world!\"}'"
echo "GET messages: curl -X GET \"http://localhost:8000/messages\""

echo "\nRegistered services:"
curl -X GET "http://localhost:8003/services"
```

Overall, the results are the same as task 1. Here is the code I tested with:

## Sending messages

```
# Send a message
curl -X POST http://localhost:3000/message \
     -H "Content-Type: application/json" \
     -d '{"msg":"Hello World"}'

# Get all messages
curl http://localhost:3000/messages
```

## Results

```
``[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"6b5b9426-96bd-4729-aa36-f186394cea68","status":"Message sent successfully"}
[petro@shire scripts[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"6b23a557-3dbc-4a53-9a53-4ed5bd78afc2","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"d96e547e-c1df-4a6a-b41d-22694d61db51","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"0f10c6d3-6d43-41cd-a474-c952c5c79b91","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"4a826037-fd6f-424f-b99e-b02e96b735a0","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"820e5407-78ba-4ba1-b23d-0f2c1ec558ee","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"90d20515-c948-4fbb-b52a-75222a862c20","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"d71f2415-cf98-4093-992c-aa409ebd89f5","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"0778de60-71b1-4d89-925d-5e2253654231","status":"Message sent successfully"}
[petro@shire scripts]$ curl -X POST http://localhost:8000/messages -H     "Content-Type: application/json" -d '{"msg":"Hello"}'
```

## Facade log

```
INFO:     Started server process [41055]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:35236 - "POST /message HTTP/1.1" 404 Not Found
INFO:     127.0.0.1:35332 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35340 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35342 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35344 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35356 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35368 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35376 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35384 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35394 - "POST /messages HTTP/1.1" 200 OK
INFO:     127.0.0.1:35410 - "POST /messages HTTP/1.1" 200 OK
```

## Config server log:

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8003 (Press CTRL+C to quit)
INFO:     127.0.0.1:45562 - "POST /services HTTP/1.1" 200 OK
INFO:     127.0.0.1:40034 - "POST /services HTTP/1.1" 200 OK
INFO:     127.0.0.1:40050 - "POST /services HTTP/1.1" 200 OK
INFO:     127.0.0.1:40694 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40700 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40702 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40706 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40718 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40722 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40734 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40746 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40762 - "GET /services/logging HTTP/1.1" 200 OK
INFO:     127.0.0.1:40764 - "GET /services/logging HTTP/1.1" 200 OK
```
