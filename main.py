import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, QueuePool
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import redis

load_dotenv()
app = FastAPI()
DB_URL = os.environ.get("DATABASE_URL")
# Replace with your Redis private IP
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = 6379

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
engine = create_engine(
    DB_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class URL(Base):
    __tablename__ = "urls"
    short = Column(String, primary_key=True, index=True)
    long = Column(String)


Base.metadata.create_all(bind=engine)


class URLRequest(BaseModel):
    long_url: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_short_id(length=6):
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@app.post("/shorten")
def shorten_url(request: URLRequest, db: Session = Depends(get_db)):
    short_id = generate_short_id()
    db_url = URL(short=short_id, long=request.long_url)
    try:
        db.add(db_url)
        db.commit()
    except:
        db.rollback()
        raise HTTPException(status_code=500, detail="DB insert failed")
    return {"short_url": f"http://localhost:8000/{short_id}"}


@app.get("/{short_id}")
def redirect(short_id: str, db: Session = Depends(get_db)):
    cached_url = redis_client.get(short_id)
    if cached_url:
        return {"long_url": cached_url}

    url: type[URL] = db.query(URL).filter(URL.short == short_id).first()
    if not url:
        raise HTTPException(status_code=404, detail="Not found")

    redis_client.set(short_id, url.long, ex=3600)  # cache for 1 hour

    return {"long_url": url.long}
