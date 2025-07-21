import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
DB = "urls.db"

conn = sqlite3.connect(DB)
conn.execute("CREATE TABLE IF NOT EXISTS urls (short TEXT PRIMARY KEY, long TEXT NOT NULL)")
conn.commit()
conn.close()

class URLRequest(BaseModel):
    long_url: str


def generate_short_id(length=6):
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@app.post("/shorten")
def shorten_url(request: URLRequest):
    short_id = generate_short_id()
    with sqlite3.connect(DB) as conn:
        try:
            conn.execute("INSERT INTO urls (short, long) VALUES (?, ?)", (short_id, request.long_url))
            conn.commit()
        except:
            raise HTTPException(status_code=500, detail="Collision or database error")
    return {"short_url": f"http://localhost:8000/{short_id}"}

@app.get("/{short_id}")
def redirect(short_id: str):
    with sqlite3.connect(DB) as conn:
        cursor = conn.execute("SELECT long FROM urls WHERE short=?", (short_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Not found')
        return {"long_url": row[0]}

