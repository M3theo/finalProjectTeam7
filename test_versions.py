import os, shutil, sqlite3, sys, tempfile
from fastapi.testclient import TestClient
import main, main_secure

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_STORAGE = os.path.join(PROJECT_DIR, "instance", "storage")


def setup_env(module):
    tmp_dir = tempfile.mkdtemp()
    storage_dir = os.path.join(tmp_dir, "storage")
    shutil.copytree(SOURCE_STORAGE, storage_dir)
    db_path = os.path.join(tmp_dir, "workspace.db")
    with open(os.path.join(PROJECT_DIR, "init.sql")) as f:
        sqlite3.connect(db_path).executescript(f.read())
    module.DB_PATH = db_path
    module.STORAGE_DIR = storage_dir
    module.sessions.clear()
    return tmp_dir


def login_client(module, username):
    client = TestClient(module.app)
    client.post("/login", json={"username": username, "password": username + "123"})
    return client


def run_scenarios(module):
    tmp_dir = setup_env(module)
    tom = login_client(module, "tom")
    anna = login_client(module, "anna")
    anonymous = TestClient(module.app)
    upload_id = tom.post("/upload", files={"file": ("tom_notes.csv", b"note\nGroup A secret\n")}).json().get("dataset_id")
    results = {
        "tom lists his own group": tom.get("/list").status_code,
        "tom reads his own dataset 1": tom.get("/list/1").status_code,
        "tom reads Group B dataset 2": tom.get("/list/2").status_code,
        "tom downloads Group B dataset 2": tom.get("/download/2").status_code,
        "anna reads Group A dataset 1": anna.get("/list/1").status_code,
        "anna downloads tom's new upload": anna.get(f"/download/{upload_id}").status_code,
        "anonymous reads dataset 1": anonymous.get("/list/1").status_code,
    }
    shutil.rmtree(tmp_dir)
    return results


EXPECTED = {
    "tom lists his own group": 200,
    "tom reads his own dataset 1": 200,
    "tom reads Group B dataset 2": 404,
    "tom downloads Group B dataset 2": 404,
    "anna reads Group A dataset 1": 404,
    "anna downloads tom's new upload": 404,
    "anonymous reads dataset 1": 401,
}

vuln_results = run_scenarios(main)
secure_results = run_scenarios(main_secure)
all_passed = True
print(f"{'scenario':36} {'vulnerable':>10} {'secure':>8}  verdict")
print("-" * 70)
for scenario, expected in EXPECTED.items():
    vuln_status, secure_status = vuln_results[scenario], secure_results[scenario]
    if secure_status != expected:
        verdict = f"FAIL (expected {expected})"
        all_passed = False
    elif vuln_status == secure_status:
        verdict = "same behaviour"
    else:
        verdict = "fixed"
    print(f"{scenario:36} {vuln_status:>10} {secure_status:>8}  {verdict}")
print("-" * 70)
print("secure version: ALL CHECKS PASSED" if all_passed else "secure version: SOME CHECKS FAILED")
sys.exit(0 if all_passed else 1)