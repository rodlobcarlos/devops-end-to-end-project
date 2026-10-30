from fastapi import FastAPI, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest

app=FastAPI()

REQUEST_COUNTER = Counter(
    "http_requests_total", 
    "Total number of HTTP requests processed",
    ["method", "endpoint", "status"]
)


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def get_healthz():
    REQUEST_COUNTER.labels(method="GET", endpoint="/healthz", status="200").inc()
    return ({"status":"healthy", "version": app.version})


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST) 


# Endpoint to simulate a failure for testing purposes.
@app.get("/items", status_code=status.HTTP_200_OK)
async def get_items(fail: bool = False):
    if fail:
        REQUEST_COUNTER.labels(method="GET", endpoint="/items", status="500").inc()
        return Response(content="Internal Server Error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    REQUEST_COUNTER.labels(method="GET", endpoint="/items", status="200").inc()
    return {"items": ["item-1", "item-2", "item-3"]}