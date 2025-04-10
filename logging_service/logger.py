#!/usr/bin/env python3

import socket
import uuid
import hazelcast
import requests
import socket
import argparse
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os


# Message model
class MessageRequest(BaseModel):
    id: str
    msg: str


class ServiceInstance(BaseModel):
    ip: str
    port: int


class ServiceRegistration(BaseModel):
    service_name: str
    instances: List[ServiceInstance]


app = FastAPI(title="Logging Service")

CONFIG_SERVER_URL = "http://config_server:8003"
PORT = 8000

# Hazelcast client for storing messages
hz_client = hazelcast.HazelcastClient(cluster_members=["hazelcast:5701"])
messages_map = hz_client.get_map("messages").blocking()


@app.on_event("startup")
async def startup_event():
    """Registers this logging service instance with the config server on startup."""
    name = "logging"
    port = PORT
    ip = socket.gethostbyname(socket.gethostname())
    sid = f"{name}-{str(uuid.uuid4())[:8]}"

    requests.put(
        "http://consul:8500/v1/agent/service/register",
        json={
            "ID": sid,
            "Name": name,
            "Address": ip,
            "Port": port,
            "Check": {"HTTP": f"http://{ip}:{port}/health", "Interval": "10s"},
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/messages")
async def log_message(message: MessageRequest):
    """Stores the received message in Hazelcast and logs it to the console."""
    try:
        messages_map.put(message.id, message.msg)
        print(f"Received message - ID: {message.id}, Content: {message.msg}")
        return {"status": "Message logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log message: {str(e)}")


@app.get("/messages")
async def get_messages():
    """Retrieves all stored messages from Hazelcast."""
    try:
        all_entries = messages_map.entry_set()
        messages = {entry[0]: entry[1] for entry in all_entries}
        return messages if messages else {"message": "No messages found"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve messages: {str(e)}"
        )


@app.on_event("shutdown")
def shutdown_event():
    """Shuts down the Hazelcast client when the service stops."""
    hz_client.shutdown()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
