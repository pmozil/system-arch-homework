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
