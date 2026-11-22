# finalProjectTeam7 – IDOR demo (dataset workspace)

A small FastAPI app where users from two research groups upload and share CSV datasets.
The project contains two versions of the same app:

| File | Version | Description |
|---|---|---|
| `main.py` | **Vulnerable** | Any logged-in user can view or download **any** dataset by its ID, even one belonging to another group (IDOR – Insecure Direct Object Reference). |
| `main_secure.py` | **Secured** | Same app, but a dataset is only returned if it belongs to the logged-in user's group. |

Only the group check is fixed for now. Other improvements (cookie flags, session expiry, upload validation…) are marked with `# TODO (later)` in `main_secure.py`.

## The vulnerability

`/list/{id}` and `/download/{id}` load the dataset with:

```sql
-- main.py (vulnerable)
SELECT * FROM datasets WHERE dataset_id = ?
```

The app only checks that the user is logged in, not that the dataset belongs to their group.
Since dataset IDs are simple numbers (1, 2, 3…), a user can just change the ID in the URL and read other groups' data.

```sql
-- main_secure.py (fixed)
SELECT * FROM datasets WHERE dataset_id = ? AND group_id = ?
```

A dataset from another group now returns `404 dataset not found`, so its existence is not revealed either.

## Project structure

```
finalProjectTeam7/
├── main.py              # vulnerable version
├── main_secure.py       # secured version (group check)
├── test_versions.py     # runs the same scenarios against both versions
├── init.sql             # database schema + test users + datasets
├── instance/storage/    # CSV files, stored under random uuid names
├── requirements.txt     # pinned Python dependencies
├── Dockerfile           # "test" and "production" stages
├── .dockerignore
├── runApp.sh            # builds and runs the secured app in Docker
└── runTest.sh           # builds and runs the tests in Docker
```

## Test data

| User | Password | Group | Owns dataset |
|---|---|---|---|
| lena | `lena123` | Group A | 1 – Soil samples |
| tom | `tom123` | Group A | |
| anna | `anna123` | Group B | 2 – Campus air quality |
| peter | `peter123` | Group B | |

Some rows are marked `UNPUBLISHED - internal only` (Group A) or `CONFIDENTIAL - draft results` (Group B): these should never be visible to the other group.

## API

| Method | Route | Description |
|---|---|---|
| POST | `/login` | JSON body `{"username": "...", "password": "..."}`, sets a `session` cookie |
| POST | `/logout` | Ends the session |
| GET | `/list` | Lists the datasets of the user's group |
| GET | `/list/{id}` | Shows the content of a dataset |
| GET | `/download/{id}` | Downloads a dataset as a CSV file |
| POST | `/upload` | Uploads a file (`file` form field) into the user's group |

## Requirements

- Docker

## Run the tests

```bash
chmod +x runTest.sh runApp.sh   # first time only
./runTest.sh
```

This builds the `test` stage of the Dockerfile and runs `test_versions.py` in an isolated container (no network, read-only filesystem).
The script loads both versions on a temporary copy of the database and compares the results:

```
scenario                             vulnerable   secure  verdict
----------------------------------------------------------------------
tom lists his own group                     200      200  same behaviour
tom reads his own dataset 1                 200      200  same behaviour
tom reads Group B dataset 2                 200      404  fixed
tom downloads Group B dataset 2             200      404  fixed
anna reads Group A dataset 1                200      404  fixed
anna downloads tom's new upload             200      404  fixed
anonymous reads dataset 1                   401      401  same behaviour
----------------------------------------------------------------------
secure version: ALL CHECKS PASSED
```

The exit code is `0` if all checks pass, `1` otherwise.

## Run the app

```bash
./runApp.sh
```

The secured app is available at `http://127.0.0.1:5000` (only from your own machine).
The container runs as a non-root user with a read-only filesystem, no extra Linux capabilities and memory/process limits.
Uploaded files and the database are kept in the `team7-data` Docker volume.

Stop and remove the container:

```bash
docker rm -f team7
```

Reset the data (database and uploads go back to `init.sql`):

```bash
docker volume rm team7-data
```

## Try the vulnerability manually

Run the vulnerable version locally (outside Docker):

```bash
source bin/activate
pip install -r requirements.txt
mkdir -p instance && python -c "import sqlite3; sqlite3.connect('instance/workspace.db').executescript(open('init.sql').read())"
uvicorn main:app --host 127.0.0.1 --port 5000
```

In another terminal, log in as **tom (Group A)** and read **Group B's dataset 2**:

```bash
curl -c cookies.txt -H "Content-Type: application/json" \
     -d '{"username":"tom","password":"tom123"}' http://127.0.0.1:5000/login
curl -b cookies.txt http://127.0.0.1:5000/list        # only dataset 1 (his group)
curl -b cookies.txt http://127.0.0.1:5000/list/2      # Group B's CONFIDENTIAL data
```

With `uvicorn main_secure:app` (or `./runApp.sh`), the last request returns `404 dataset not found`.

Note: running `init.sql` again resets the database.
