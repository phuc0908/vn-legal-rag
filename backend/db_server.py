from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.law_routes import router as law_router
import uvicorn

app = FastAPI(title="VN Legal DB API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(law_router)

if __name__ == "__main__":
    uvicorn.run("db_server:app", host="0.0.0.0", port=8002, reload=True)
