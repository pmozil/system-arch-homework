#!/usr/bin/env python3

import uuid
import random
import requests
import hazelcast
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Define the request model
class MessageRequest(BaseModel):
    msg: str

class ServiceInstance(BaseModel):
    ip: str
    port: int

app = FastAPI(title="Facade Service")

hz_client = hazelcast.HazelcastClient()
messages_map = hz_client.get_map("messages")

CONFIG_SERVER_URL = "http://localhost:8003/services"

def get_service_url(service_name: str):
    """
    Get a random instance URL for the specified service from the config server
    """
    try:
        response = requests.get(f"{CONFIG_SERVER_URL}/{service_name}")
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get {service_name} instances from config server"
            )
        instances = [ServiceInstance(**inst) for inst in response.json()]
        if not instances:
            raise HTTPException(
                status_code=500,
                detail=f"No instances available for service: {service_name}"
            )
        instance = random.choice(instances)
        return f"http://{instance.ip}:{instance.port}"
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with config server: {str(e)}"
        )

@app.post("/messages")
async def send_message(message_request: MessageRequest):
    """
    Receives a message from client, generates UUID, and forwards to logging service
    """
    message_id = str(uuid.uuid4())
    payload = {
        "id": message_id,
        "msg": message_request.msg
    }
    try:
        repeats = 3

        while repeats > 0:
            logging_service_url = f"{get_service_url('logging')}/messages"
            response = requests.post(logging_service_url, json=payload)
            if response.status_code == 200:
                return {"id": message_id, "status": "Message sent successfully"}
            repeats -= 1

        raise HTTPException(
            status_code=500,
            detail="Failed to forward message to logging service"
        )
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with logging service: {str(e)}"
        )

@app.get("/messages")
async def get_messages():
    """
    Retrieves messages from both logging service and messages service
    """
    try:
        logging_service_url = f"{get_service_url('logging')}/messages"
        messages_service_url = f"{get_service_url('logging')}/messages"
        logging_response = requests.get(logging_service_url)
        if logging_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to get messages from logging service"
            )
        messages_response = requests.get(messages_service_url)
        if messages_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Failed to get messages from messages service"
            )
        combined_response = {
            "logging_service": logging_response.text,
            "messages_service": messages_response.text
        }
        return combined_response
    except requests.RequestException as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error communicating with services: {str(e)}"
        )

@app.on_event("shutdown")
def shutdown_event():
    """
    Shutdown Hazelcast client on application exit
    """
    hz_client.shutdown()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
