# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile, os, subprocess, json, base64, textwrap, signal

app = FastAPI()

class FileInput(BaseModel):
    path: str
    content: str  # UTF-8 text or base64 if binary

class ExecRequest(BaseModel):
    code: str
    files: list[FileInput] | None = None
    timeoutMs: int = 10000  # cap at 30000

@app.post("/execute")
def execute(req: ExecRequest):
    timeout = min(max(req.timeoutMs, 1000), 30000)
    with tempfile.TemporaryDirectory() as work:
        # Write files
        if req.files:
            for f in req.files:
                fp = os.path.join(work, f.path)
                os.makedirs(os.path.dirname(fp), exist_ok=True)
                # Assume text; add your own base64 detection as needed
                with open(fp, "w", encoding="utf-8") as out:
                    out.write(f.content)

        code_path = os.path.join(work, "main.py")
        with open(code_path, "w", encoding="utf-8") as out:
            out.write(req.code)

        # Run python with no site imports to reduce surface
        # Cloud Run provides outer sandboxing; avoid shell=True
        proc = subprocess.Popen(
            ["python", "-S", code_path],
            cwd=work,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,  # allow group kill on timeout
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout / 1000)
            exit_code = proc.returncode
            outcome = "OUTCOME_OK" if exit_code == 0 else "OUTCOME_ERROR"
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            stdout, stderr, exit_code = "", "Timeout", -1
            outcome = "OUTCOME_TIMEOUT"

        # Optionally scan work dir for generated images and inline them
        images = []
        for root, dirs, files in os.walk(work):
            for name in files:
                if name.lower().endswith((".png", ".jpg", ".jpeg")):
                    p = os.path.join(root, name)
                    with open(p, "rb") as f:
                        images.append({
                            "path": os.path.relpath(p, work),
                            "mediaType": "image/png" if name.lower().endswith(".png") else "image/jpeg",
                            "data": base64.b64encode(f.read()).decode("ascii")
                        })

        return {
            "executableCode": {"language": "PYTHON", "code": req.code},
            "codeExecutionResult": {
                "outcome": outcome,
                "exitCode": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "images": images,
            }
        }
