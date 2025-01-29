use axum::{
    routing::get,
    Router,
};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/message", get(handle_get));

    let addr = SocketAddr::from(([127, 0, 0, 1], 3002));
    println!("Messages service listening on {}", addr);
    axum_server::bind(addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

async fn handle_get() -> &'static str {
    "not implemented yet"
}
