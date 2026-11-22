import hashlib, hmac, os, secrets, sqlite3, uuid
from fastapi import FastAPI, Request, Response, UploadFile, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

# TODO (later): disable /docs, /redoc and /openapi.json in production
app = FastAPI()
DB_PATH = "instance/workspace.db"
STORAGE_DIR = "instance/storage"
# TODO (later): add an expiry time to sessions (currently they never expire)
sessions = {}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def check_password(hashed, password):
    algo, salt, expected = hashed.split("$")
    iterations = int(algo.split(":")[2])
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(digest, expected)


def current_user(request):
    user = sessions.get(request.cookies.get("session"))
    if not user:
        raise HTTPException(401, "not logged in")
    return user


# SECURITY FIX (IDOR): the dataset must belong to the logged-in user's group
# vulnerable version: SELECT * FROM datasets WHERE dataset_id = ?  (any group)
# 404 instead of 403 so other groups' dataset IDs cannot be discovered
def get_group_dataset(dataset_id, user):
    dataset = get_db().execute(
        "SELECT * FROM datasets WHERE dataset_id = ? AND group_id = ?",
        (dataset_id, user["group_id"]),
    ).fetchone()
    if not dataset:
        raise HTTPException(404, "dataset not found")
    return dataset


@app.post("/login")
async def login(request: Request, response: Response):
    # TODO (later): validate that username and password are strings
    creds = await request.json()
    user = get_db().execute("SELECT * FROM users WHERE username = ?", (creds.get("username"),)).fetchone()
    if not user or not check_password(user["password_hash"], creds.get("password", "")):
        raise HTTPException(401, "invalid creds")
    token = secrets.token_hex(16)
    sessions[token] = {"user_id": user["user_id"], "username": user["username"], "group_id": user["group_id"]}
    # TODO (later): secure the cookie (samesite="strict", secure=True over HTTPS, max_age)
    response.set_cookie("session", token, httponly=True)
    return sessions[token]


@app.post("/logout")
def logout(request: Request, response: Response):
    sessions.pop(request.cookies.get("session"), None)
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/list")
def list_datasets(request: Request):
    user = current_user(request)
    rows = get_db().execute("SELECT dataset_id, name, original_name FROM datasets WHERE group_id = ?", (user["group_id"],))
    return [dict(row) for row in rows]


@app.get("/list/{dataset_id}", response_class=PlainTextResponse)
def show_dataset(dataset_id: int, request: Request):
    user = current_user(request)
    # SECURITY FIX (IDOR): group check added (vulnerable version: get_dataset(dataset_id))
    dataset = get_group_dataset(dataset_id, user)
    with open(os.path.join(STORAGE_DIR, dataset["stored_name"])) as f:
        return f.read()


@app.get("/download/{dataset_id}")
def download_dataset(dataset_id: int, request: Request):
    user = current_user(request)
    # SECURITY FIX (IDOR): group check added (vulnerable version: get_dataset(dataset_id))
    dataset = get_group_dataset(dataset_id, user)
    return FileResponse(os.path.join(STORAGE_DIR, dataset["stored_name"]), filename=dataset["original_name"])


@app.post("/upload")
async def upload_dataset(file: UploadFile, request: Request):
    user = current_user(request)
    # TODO (later): accept only .csv files, limit the size and check the content is UTF-8 text
    stored_name = f"{uuid.uuid4()}.csv"
    with open(os.path.join(STORAGE_DIR, stored_name), "wb") as f:
        f.write(await file.read())
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO datasets (group_id, owner_id, name, original_name, stored_name) VALUES (?, ?, ?, ?, ?)",
        (user["group_id"], user["user_id"], file.filename, file.filename, stored_name),
    )
    conn.commit()
    return {"dataset_id": cur.lastrowid}