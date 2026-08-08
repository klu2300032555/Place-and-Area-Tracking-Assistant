from fastapi import FastAPI
from app.routes.pincode_routes import router as pincode_router
from app.routes.address_routes import router as address_router

app = FastAPI(
    title="PATA Backend",
    version="1.0.0"
)

# Register routes
app.include_router(address_router)
app.include_router(pincode_router)


@app.get("/")
def root():
    return {
        "message": "PATA backend is running",
        "available_routes": [
            "/",
            "/health",
            "/validate-pincode",
            "/analyze-address"
        ]
    }