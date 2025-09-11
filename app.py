from fastapi import FastAPI, HTTPException
import redis
import databases
import sqlalchemy
import os

# Use environment variables for DB connection (for Docker compatibility)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://demo:password@db:5432/demo"
)

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()
notes = sqlalchemy.Table(
    "notes",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("text", sqlalchemy.String),
)

engine = sqlalchemy.create_engine(DATABASE_URL)
metadata.create_all(engine)

app = FastAPI()

# Redis initialization with error handling
def get_redis_client():
    try:
        r = redis.Redis(host="redis", port=6379, decode_responses=True)
        r.ping()
        return r
    except redis.exceptions.ConnectionError:
        return None

r = get_redis_client()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/cache/{key}")
def cache_get(key: str):
    if not r:
        raise HTTPException(status_code=500, detail="Redis not available")
    val = r.get(key)
    if val is None:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"key": key, "value": val}

@app.post("/cache/{key}/{value}")
def cache_set(key: str, value: str):
    if not r:
        raise HTTPException(status_code=500, detail="Redis not available")
    try:
        r.set(key, value)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/note/{note_text}")
async def create_note(note_text: str):
    query = notes.insert().values(text=note_text)
    last_record_id = await database.execute(query)
    return {"id": last_record_id, "text": note_text}

@app.get("/note/{note_id}")
async def read_note(note_id: int):
    query = notes.select().where(notes.c.id == note_id)
    note = await database.fetch_one(query)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return {"id": note["id"], "text": note["text"]}

@app.get("/")
def root():
    return {"message": "Hello from Bootcamp Day 3"}