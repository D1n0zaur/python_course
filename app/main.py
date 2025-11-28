from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello, user"}