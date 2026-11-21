from fastapi import FastAPI, Request
import sqlite3


app = FastAPI()


@app.post("/login")
async def login(request: Request):
    print(f"request = {request}")
    data = await request.json()
    print(data)
    return 200


@app.get("/csv/<string:csvName>")
def getCSV(csvName):
    data = []
    with open("/data/" + csvName) as f:
        data.append(f.read())
    return data
