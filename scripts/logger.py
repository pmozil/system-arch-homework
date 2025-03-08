#!/usr/bin/env python3


import hazelcast
import uvicorn
import requests
import socket
import argparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

class MessageRequest(BaseModel):
    id: str
    msg: str

class ServiceInstance(BaseModel):
    ip: str
    port: int

class ServiceRegistration(BaseModel):
    service_name: str
    instances: List[ServiceInstance]

parser = argparse.ArgumentParser(description='Logging Service')
parser.add_argument('--port', type=int, default=8001, help='Port to run the service on')
parser.add_argument('--config-server', type=str, default='http://localhost:8003', help='Config server URL')
args = parser.parse_args()

app = FastAPI(title="Logging Service")

hz_client = hazelcast.HazelcastClient()
messages_map = hz_client.get_map("messages").blocking()

PORT = args.port
CONFIG_SERVER_URL = args.config_server

@app.on_event("startup")
async def startup_event():
    """
    Register this service instance with the config server on startup
    """
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    if ip_address.startswith("127."):
        ip_address = "localhost"
    try:
        registration = ServiceRegistration(
            service_name="logging",
            instances=[ServiceInstance(ip=ip_address, port=PORT)]
        )
        response = requests.post(f"{CONFIG_SERVER_URL}/services", json=registration.dict())
        if response.status_code == 200:
            print(f"Successfully registered with config server: {ip_address}:{PORT}")
        else:
            print(f"Failed to register with config server: {response.text}")
    except requests.RequestException as e:
        print(f"Error registering with config server: {str(e)}")

@app.post("/messages")
async def log_message(message: MessageRequest):
    """
    Receives a message from facade service, stores it in a hash table, and logs to console
    """
    try:
        messages_map.put(message.id, message.msg)
        print(f"Received message - ID: {message.id}, Content: {message.msg}")
        return {"status": "Message logged successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log message: {str(e)}")

@app.get("/messages")
async def get_messages():
    """
    Returns all messages stored in the hash table as a string
    """
    try:
        all_entries = messages_map.entry_set()
        messages = [entry[1] for entry in all_entries]
        response_text = ", ".join(messages) if messages else "No messages found"
        return response_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve messages: {str(e)}")

@app.on_event("shutdown")
def shutdown_event():
    """
    Shutdown Hazelcast client on application exit
    """
    hz_client.shutdown()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
