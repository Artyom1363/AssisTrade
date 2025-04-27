from fastapi import FastAPI
from routes.chat_history import router
from db.database import init_db

init_db()
app = FastAPI()
app.include_router(router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
