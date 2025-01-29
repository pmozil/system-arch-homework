## Link to github
[https://github.com/pmozil/system-arch-homework/tree/micro_basics](https://github.com/pmozil/system-arch-homework/tree/micro_basics)


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
|-- Cargo.toml
|-- proto
|   -- logging.proto
|---src
    |-- facade-service.rs
    |-- logging-service.rs
    |-- messages-service.rs
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


## Results

### My commands:
```sh
[petro@shire sa-homework]$ curl -X POST http://localhost:3000/message -H \
    "Content-Type: application/json" -d '{"msg":"Hello"}'
{"id":"b849ed06-1526-4491-bcc5-53f6d29453cf","msg":"Hello"}
[petro@shire sa-homework]$ curl -X POST http://localhost:3000/message -H \
    "Content-Type: application/json" -d '{"msg":"Hello1"}'
{"id":"f45a556c-126f-4d4a-a289-39232e08578e","msg":"Hello1"}
[petro@shire sa-homework]$ curl -X POST http://localhost:3000/message -H \
    "Content-Type: application/json" -d '{"msg":"Hello2"}'
{"id":"146139c0-2f1f-4d89-9b43-5f4598b30960","msg":"Hello2"}
[petro@shire sa-homework]$ curl -X POST http://localhost:3000/message -H \
    "Content-Type: application/json" -d '{"msg":"Hello3"}'
[petro@shire sa-homework]$ curl http://localhost:3000/messages
Hello1
Hello2
Hello
Hello3
```

### Log of facade:

```sh
[petro@shire sa-homework]$ ./target/debug/logging-service
Logging service listening on [::1]:50051
Received message: LogRequest { id: "b849ed06-1526-4491-bcc5-53f6d29453cf", msg: "Hello" }
Received message: LogRequest { id: "f45a556c-126f-4d4a-a289-39232e08578e", msg: "Hello1" }
Received message: LogRequest { id: "146139c0-2f1f-4d89-9b43-5f4598b30960", msg: "Hello2" }
Received message: LogRequest { id: "29925212-808e-478c-9579-ade0e304de0e", msg: "Hello3" }
```

### Log of logger:
```sh
[petro@shire sa-homework]$ ./target/debug/facade-service
Facade service listening on 127.0.0.1:3000`
```

### Log of message
```sh
[petro@shire sa-homework]$ ./target/debug/message-service
Messages service listening on 127.0.0.1:3002
```
