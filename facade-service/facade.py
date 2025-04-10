#!/usr/bin/env python3

import socket
import uuid
import random
import requests
import uvicorn
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kafka import KafkaProducer, KafkaConsumer
import json
import threading


# Request model
class MessageRequest(BaseModel):
    msg: str


class ServiceInstance(BaseModel):
    ip: str
    port: int


app = FastAPI(title="Facade Service")

# Kafka configuration
KAFKA_BROKER_URL = "broker-1:9092"  # Update this with your Kafka broker URL
KAFKA_TOPIC = "messages"  # Kafka topic to send/receive messages

CONFIG_SERVER_URL = "http://config_server:8003/services"


@app.on_event("startup")
def register_facade():
    service_name = "facade"
    service_port = 8000
    service_id = f"{service_name}-{str(uuid.uuid4())[:8]}"
    ip_address = socket.gethostbyname(socket.gethostname())

    data = {
        "ID": service_id,
        "Name": service_name,
        "Address": ip_address,
        "Port": service_port,
        "Check": {
            "HTTP": f"http://{ip_address}:{service_port}/health",
            "Interval": "10s",
        },
    }
    try:
        requests.put("http://consul:8500/v1/agent/service/register", json=data)
    except Exception as e:
        print(f"Consul registration failed: {e}")


@app.on_event("shutdown")
def shutdown_event():
    """Properly close Kafka producer on application shutdown"""
    if producer:
        producer.close()


def get_service_url(service_name: str):
    try:
        res = requests.get(
            f"http://consul:8500/v1/health/service/{service_name}?passing=true"
        )
        services = res.json()
        if not services:
            raise HTTPException(
                status_code=500, detail=f"No healthy instances of {service_name}"
            )
        instance = random.choice(services)["Service"]
        return f"http://{instance['Address']}:{instance['Port']}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consul error: {str(e)}")


def send_to_kafka_async(topic, message):
    try:
        producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BROKER_URL], api_version=(4, 0, 0)
        )
        # Try to test connection first
        if not producer.bootstrap_connected():
            return
        future = producer.send(topic, message.encode("utf-8"))

        # Non-blocking way to check send status
        def on_success(record_metadata):
            print(f"Message sent to {record_metadata.topic}")

        def on_error(excp):
            print(f"Error sending message: {excp}")

        future.add_callback(on_success)
        future.add_errback(on_error)
    except Exception as e:
        print(f"KAFKA PRODUCER ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Kafka producer error: {str(e)}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/messages")
async def send_message(message_request: MessageRequest):
    """Receives a message, generates a UUID, sends it to Kafka, and forwards to the logging service."""
    message_id = str(uuid.uuid4())
    payload = {"id": message_id, "msg": message_request.msg}
    # Send to Kafka asynchronously without blocking
    send_to_kafka_async(KAFKA_TOPIC, message_request.msg)
    try:
        logging_service_url = f"{get_service_url('logging')}/messages"
        response = requests.post(logging_service_url, json=payload)
        if response.status_code == 200:
            return {"id": message_id, "status": "Message sent successfully"}
        else:
            raise HTTPException(
                status_code=500, detail="Failed to forward message to logging service"
            )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with logging service: {str(e)}",
        )


@app.get("/messages")
async def get_messages():
    """Fetch all messages from the logging service and the Kafka consumer."""
    try:
        logging_service_url = f"{get_service_url('logging')}/messages"
        response = requests.get(logging_service_url)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve messages from logging service",
            )

        # Pull messages from Kafka consumer
        kafka_messages = []
        logging_service_url = f"{get_service_url('messages')}/messages"
        kafka_response = requests.get(logging_service_url)

        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve messages from logging service",
            )

        return {
            "messages": {
                "logging_service": response.json(),
                "kafka_messages": kafka_response.json(),
            }
        }

    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with logging service: {str(e)}",
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
