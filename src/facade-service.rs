use axum::{
    routing::{get, post},
    Router,
    extract::Json,
    response::IntoResponse,
};
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use std::net::SocketAddr;


pub mod logging {
    tonic::include_proto!("logging");
}
use logging::{
    logger_client::LoggerClient,
    LogRequest, GetLogsRequest,
};



#[derive(Deserialize)]
struct Message {
    msg: String,
}

#[derive(Serialize)]
struct LogMessage {
    id: String,
    msg: String,
}


#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/message", post(handle_post))
        .route("/messages", get(handle_get));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3000));
    println!("Facade service listening on {}", addr);
    axum_server::bind(addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn handle_post(Json(payload): Json<Message>) -> impl IntoResponse {
    let id = Uuid::new_v4().to_string();

    // Connect to logging service via gRPC
    let mut client = LoggerClient::connect("http://[::1]:50051")
        .await
        .unwrap();

    let request = tonic::Request::new(LogRequest {
        id: id.clone(),
        msg: payload.msg.clone(),
    });

    let _ = client.log_message(request).await;

    Json(LogMessage { id, msg: payload.msg })
}

async fn handle_get() -> impl IntoResponse {
    // Get messages from logging service via gRPC
    let mut client = LoggerClient::connect("http://[::1]:50051")
        .await
        .unwrap();

    let request = tonic::Request::new(GetLogsRequest {});
    let response = client.get_logs(request).await.unwrap();
    let logging_messages = response.into_inner().messages.join("\n");

    // Get message from messages service
    let messages_response = reqwest::Client::new()
        .get("http://localhost:3002/message")
        .send()
        .await
        .unwrap()
        .text()
        .await
        .unwrap();

    format!("{}\n{}", logging_messages, messages_response)
}
