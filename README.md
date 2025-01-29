# Rust Microservices Demo

This project demonstrates a microservices architecture implemented in Rust, utilizing both gRPC and HTTP protocols for service communication. The system consists of three microservices that work together to process and store messages.

## Architecture

The system consists of three microservices:

- **facade-service**: Acts as an API gateway, accepting HTTP POST/GET requests from clients
- **logging-service**: Stores messages in memory and provides access to them via gRPC
- **messages-service**: A stub service that returns a static message via HTTP

### Communication Flow

#### POST Request Flow:
1. Client sends POST request to facade-service with a message
2. facade-service generates a UUID for the message
3. facade-service forwards the message to logging-service via gRPC
4. logging-service stores the message in memory
5. Response is returned to the client with the UUID

#### GET Request Flow:
1. Client sends GET request to facade-service
2. facade-service requests messages from logging-service via gRPC
3. facade-service requests message from messages-service via HTTP
4. facade-service concatenates responses and returns to client

## Prerequisites

- Rust

## Project Structure

```
├── Cargo.toml
├── proto
│   └── logging.proto
└───src
    ├── facade-service.rs
    ├── logging-service.rs
    └── messages-service.rs
```

## Installation

1. Clone the repository
2. Ensure you have the Protocol Buffers compiler installed
3. Build the project:
```bash
cargo build
```

## Running the Services

Start each service in a separate terminal:

```bash
# Terminal 1 - Start logging-service
cargo run --bin facade-service

# Terminal 2 - Start facade-service
cargo run --bin logging-service

# Terminal 3 - Start messages-service
cargo run --bin messages-service
```

Service addresses:
- facade-service: http://localhost:3000
- logging-service: http://[::1]:50051 (gRPC)
- messages-service: http://localhost:3002

## Testing the Services

You can test the services using curl:

```bash
# Send a message
curl -X POST http://localhost:3000/message \
     -H "Content-Type: application/json" \
     -d '{"msg":"Hello World"}'

# Get all messages
curl http://localhost:3000/messages
```

## Technologies Used

- **Rust**: Programming language
- **tokio**: Async runtime
- **tonic**: gRPC framework
- **axum**: HTTP framework
- **Protocol Buffers**: Data serialization
- **DashMap**: Thread-safe hash map

## Project Components

### Proto Definition

The gRPC service is defined in `proto/logging.proto`:
```protobuf
service Logger {
  rpc LogMessage (LogRequest) returns (LogResponse);
  rpc GetLogs (GetLogsRequest) returns (GetLogsResponse);
}
```

### Services

#### facade-service
- Handles HTTP requests from clients
- Converts between HTTP and gRPC protocols
- Acts as a gateway to other services

#### logging-service
- Provides gRPC endpoints for message storage
- Stores messages in memory using DashMap
- Returns all stored messages when requested

#### messages-service
- Simple HTTP service
- Returns a static message
- Acts as a stub for future implementation

## License

This project is licensed under the BSD 3-Clause License - see the LICENSE file for details.
