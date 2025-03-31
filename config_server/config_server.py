#!/usr/bin/env python3

import json
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

app = FastAPI(title="Config Server")

class ServiceInstance(BaseModel):
    ip: str
    port: int

class ServiceRegistration(BaseModel):
    service_name: str
    instances: List[ServiceInstance]

services: Dict[str, List[ServiceInstance]] = {}

def initialize_services():
    if os.path.exists("services_config.json"):
        with open("services_config.json", "r") as f:
            config = json.load(f)
            for service_name, instances in config.items():
                services[service_name] = [ServiceInstance(**inst) for inst in instances]
    for env_var, value in os.environ.items():
        if env_var.endswith("_SERVICE"):
            service_name = env_var.lower().replace("_service", "")
            instances = []
            for instance in value.split(","):
                if ":" in instance:
                    ip, port = instance.split(":")
                    instances.append(ServiceInstance(ip=ip, port=int(port)))
            if instances:
                services[service_name] = instances

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    initialize_services()
    print(f"Initialized services: {services}")

@app.get("/services/{service_name}")
async def get_service_instances(service_name: str):
    """Get all instances of a specific service"""
    if service_name not in services:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
    return services[service_name]

@app.post("/services")
async def register_service(registration: ServiceRegistration):
    """Register a new service or update an existing one"""
    services[registration.service_name] = registration.instances
    return {"status": "Service registered successfully"}

@app.get("/services")
async def list_services():
    """List all registered services"""
    return services

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
