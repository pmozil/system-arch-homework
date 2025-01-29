use tonic::{transport::Server, Request, Response, Status};
use dashmap::DashMap;
use std::sync::Arc;

pub mod logging {
    tonic::include_proto!("logging");
}

use logging::{
    logger_server::{Logger, LoggerServer},
    LogRequest, LogResponse,
    GetLogsRequest, GetLogsResponse,
};

#[derive(Debug, Default)]
pub struct LoggerService {
    messages: Arc<DashMap<String, String>>,
}

#[tonic::async_trait]
impl Logger for LoggerService {
    async fn log_message(
        &self,
        request: Request<LogRequest>,
    ) -> Result<Response<LogResponse>, Status> {
        let msg = request.into_inner();
        println!("Received message: {:?}", msg);
        self.messages.insert(msg.id, msg.msg);
        Ok(Response::new(LogResponse { success: true }))
    }

    async fn get_logs(
        &self,
        _request: Request<GetLogsRequest>,
    ) -> Result<Response<GetLogsResponse>, Status> {
        let messages: Vec<String> = self.messages
            .iter()
            .map(|entry| entry.value().clone())
            .collect();

        Ok(Response::new(GetLogsResponse { messages }))
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = "[::1]:50051".parse()?;
    let logger = LoggerService {
        messages: Arc::new(DashMap::new()),
    };

    println!("Logging service listening on {}", addr);

    Server::builder()
        .add_service(LoggerServer::new(logger))
        .serve(addr)
        .await?;

    Ok(())
}
