from fastapi import FastAPI ,HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import json

load_dotenv()

API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

if not API_KEY or not MODEL :
    raise RuntimeError("API KEY OR MODEL NOT FOUND!")

GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/{MODEL}:generateContent?key={API_KEY}"

app = FastAPI(title="FastAPI BACKEND",version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://github-profile-analyzer-frontend.vercel.app"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GitHubLink(BaseModel):
    link : str

GITHUB_SYSTEM_PROMPT = """
You are an expert GitHub profile analyzer.

Your goal is to evaluate a developer's GitHub profile and produce a FAIR, CONSISTENT score out of 100,
along with useful, actionable feedback.

You will receive:
- A GitHub user object (profile data)
- A list of that user's repositories

You MUST return STRICTLY this JSON object:

{
  "score": 0-100,
  "strengths": [],
  "weaknesses": [],
  "tech_stack": [],
  "activity": "",
  "suggestions": []
}

SCORING RULES (VERY IMPORTANT):
- "score" MUST be an INTEGER between 0 and 100 (no decimals, no strings).
- Score the profile as if you are evaluating a student / early-career developer
  for internships or junior roles.
- Use this breakdown as a guideline (but still return a single integer):
  - 0–30: Very weak profile (few repos, little real code, almost no activity).
  - 31–50: Basic profile (some code, mostly small/simple or incomplete projects).
  - 51–70: Decent profile (several real projects, some variety, moderate activity).
  - 71–85: Strong profile (good variety, some solid projects, good activity & polish).
  - 86–100: Outstanding profile (multiple strong projects, clear documentation,
             good activity, signs of depth and consistency).

WHEN SCORING, CONSIDER (from the provided data only):
- Number and quality of repositories (not just count, but how meaningful they look).
- Use of different programming languages and technologies.
- Presence of READMEs, descriptions, topics, and documentation.
- Recent activity and contribution level (if visible).
- Stars, forks, followers vs following (as extra signals, not the main factor).

FIELDS DETAILS:
- "strengths": List of concrete positive points about the profile.
- "weaknesses": List of concrete areas that clearly need improvement.
- "tech_stack": List of main languages, frameworks, and tools inferred from the repos.
- "activity": Short paragraph summarizing how active the user is.
- "suggestions": Practical, specific recommendations to improve the profile.

STRICT FORMAT RULES:
- Output MUST be valid JSON.
- Do NOT wrap the JSON in markdown or code fences.
- Do NOT add any extra keys.
- Do NOT add any explanatory text before or after the JSON.
- Do NOT use comments inside the JSON.
"""



@app.get("/")
async def home():
    return {"prompt":"Yesss FASTAPI is running!!!"}

def extract_username(link: str):
    link = link.rstrip("/")
    return link.split("/")[-1]



async def analyser(link:str):
    username = extract_username(link)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            user = await client.get(f"https://api.github.com/users/{username}")
            repos = await client.get(f"https://api.github.com/users/{username}/repos?per_page=100")

            user_json = user.json()
            repos_json = repos.json()

            return {
                "user": user_json,
                "repos": repos_json
            }
    except Exception as e:
        print("ERROR DETAILS:", str(e))
        raise HTTPException(status_code=500, detail=str(e))   


@app.post("/chat")
async def chat(data:GitHubLink):
    git_data = await analyser(data.link)
    payload = {
        "contents": [
            {   
                
                "parts": [
                    {"text": GITHUB_SYSTEM_PROMPT},
                     {"text": "Here is the GitHub data:\n"
                        + "User:\n" + json.dumps(git_data["user"], indent=2) +
                        "\n\nRepos:\n" + json.dumps(git_data["repos"], indent=2)}

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

        # print("GEMINI RAW RESPONSE:", reply)
        clean = reply.replace("```json", "").replace("```", "").strip()
        #print("Final data = ",clean)
        return json.loads(clean)

        

    except Exception as e:
        print("ERROR DETAILS:", str(e))
        print("RAW RESPONSE:", response.text if 'response' in locals() else 'no response')
        raise HTTPException(status_code=500, detail=str(e))