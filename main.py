from fastapi import FastAPI ,HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

if not API_KEY or not MODEL :
    raise RuntimeError("API KEY OR MODEL NOT FOUND!")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

app = FastAPI(title="FastAPI BACKEND",version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Prompt(BaseModel):
    prompt : str


@app.get("/")
async def home():
    return {"prompt":"Yesss FASTAPI is running!!!"}

@app.post("/chat")
async def chat(data:Prompt):
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": data.prompt}
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                GEMINI_URL,
                json=payload,
                headers={"Content-Type": "application/json"}
                )
            
            response.raise_for_status()
            result = response.json()

        reply = result["candidates"][0]["content"]["parts"][0]["text"]

        print("GEMINI RAW RESPONSE:", reply)
        return reply
        

    except Exception as e:
        print("ERROR DETAILS:", str(e))
        print("RAW RESPONSE:", response.text if 'response' in locals() else 'no response')
        raise HTTPException(status_code=500, detail=str(e))    