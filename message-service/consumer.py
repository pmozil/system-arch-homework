import socket
import uuid
from fastapi import FastAPI
from kafka import KafkaConsumer
import json
import threading
import time
import uvicorn
from typing import List
import requests

app = FastAPI()

# Global list to store consumed messages
messages = []

# Kafka consumer setup
KAFKA_BROKER_URL = "broker-1:9092"  # Kafka broker address
KAFKA_TOPIC = "messages"  # Topic to consume from

# Global Kafka consumer variable and initialization flag
consumer = None
consumer_initialized = False

# Lock for thread-safe message access
message_lock = threading.Lock()


# Function to consume messages in the background
def consume_messages():
    while True:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=[KAFKA_BROKER_URL],
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            api_version=(4, 0, 0),
        )
        for message in consumer:
            if message:
                print(message)
                with message_lock:
                    messages.append(
                        message.value
                    )  # Append consumed message to the list
        consumer.close()
        time.sleep(1)


# Start consuming messages when the FastAPI application starts
@app.on_event("startup")
async def startup_event():
    service_name = "messages"
    port = 8000
    ip = socket.gethostbyname(socket.gethostname())
    sid = f"{service_name}-{str(uuid.uuid4())[:8]}"

    requests.put(
        "http://consul:8500/v1/agent/service/register",
        json={
            "ID": sid,
            "Name": service_name,
            "Address": ip,
            "Port": port,
            "Check": {"HTTP": f"http://{ip}:{port}/health", "Interval": "10s"},
        },
    )

    # Start Kafka consumer in a separate background thread
    threading.Thread(target=consume_messages, daemon=True).start


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/messages")
async def get_messages():
    """Retrieve all consumed messages."""
    with message_lock:
        return {"messages": messages}


@app.get("/is_consumer_initialized")
async def is_consumer_initialized():
    """Check if the consumer has been initialized."""
    return {"consumer_initialized": consumer_initialized}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
