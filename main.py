from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile, os, subprocess, json, base64, textwrap, signal, sys
import uvicorn
import logging
from firebase_config import firebase_uploader

app = FastAPI(title="Python Code Execution API", version="1.0.0")

class FileInput(BaseModel):
    path: str
    content: str  # UTF-8 text or base64 if binary

class ExecRequest(BaseModel):
    code: str
    files: list[FileInput] | None = None
    timeoutMs: int = 10000  # cap at 30000

@app.get("/")
def read_root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "python-code-execution"}

@app.get("/health")
def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}

@app.post("/execute")
def execute(req: ExecRequest):
    """Execute Python code with optional file inputs"""
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
        
        # Run python (removed -S flag to allow site imports for packages)
        # Cloud Run provides outer sandboxing; avoid shell=True
        # Handle both Unix and Windows environments
        try:
            if os.name == 'posix':  # Unix/Linux (Cloud Run)
                proc = subprocess.Popen(
                    ["python", code_path],
                    cwd=work,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,  # allow group kill on timeout
                )
            else:  # Windows
                proc = subprocess.Popen(
                    ["python", code_path],
                    cwd=work,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
        except Exception as e:
            return {
                "executableCode": {"language": "PYTHON", "code": req.code},
                "codeExecutionResult": {
                    "outcome": "OUTCOME_ERROR",
                    "exitCode": -1,
                    "stdout": "",
                    "stderr": f"Failed to start Python process: {str(e)}",
                    "images": [],
                }
            }
        
        try:
            stdout, stderr = proc.communicate(timeout=timeout / 1000)
            exit_code = proc.returncode
            outcome = "OUTCOME_OK" if exit_code == 0 else "OUTCOME_ERROR"
        except subprocess.TimeoutExpired:
            # Handle timeout differently for Unix vs Windows
            if os.name == 'posix':
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except:
                    proc.kill()
            else:
                proc.kill()
            
            try:
                stdout, stderr = proc.communicate(timeout=1)
            except:
                stdout, stderr = "", ""
            
            stdout += "\n[Process terminated due to timeout]"
            stderr += "\n[Process terminated due to timeout]"
            exit_code = -1
            outcome = "OUTCOME_TIMEOUT"
        
        # Scan work dir for generated images and upload to Firebase
        images = []
        try:
            for root, dirs, files in os.walk(work):
                for name in files:
                    if name.lower().endswith((".png", ".jpg", ".jpeg")):
                        p = os.path.join(root, name)
                        
                        # If Firebase is configured, upload to storage
                        if firebase_uploader.is_configured():
                            with open(p, "rb") as f:
                                image_data = f.read()
                                content_type = "image/png" if name.lower().endswith(".png") else "image/jpeg"
                                
                                # Upload to Firebase and get public URL
                                public_url = firebase_uploader.upload_image(image_data, name, content_type)
                                
                                if public_url:
                                    images.append({
                                        "path": os.path.relpath(p, work),
                                        "url": public_url,
                                        "mediaType": content_type,
                                        "storage": "firebase"
                                    })
                                else:
                                    # Fallback to base64 if Firebase upload fails
                                    images.append({
                                        "path": os.path.relpath(p, work),
                                        "mediaType": content_type,
                                        "data": base64.b64encode(image_data).decode("ascii"),
                                        "storage": "base64"
                                    })
                        else:
                            # Fallback to base64 if Firebase not configured
                            with open(p, "rb") as f:
                                images.append({
                                    "path": os.path.relpath(p, work),
                                    "mediaType": "image/png" if name.lower().endswith(".png") else "image/jpeg",
                                    "data": base64.b64encode(f.read()).decode("ascii"),
                                    "storage": "base64"
                                })
        except Exception as e:
            # If image processing fails, continue without images
            logging.error(f"Image processing failed: {str(e)}")
            pass
        
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

# Handle server startup programmatically for Cloud Run
if __name__ == "__main__":
    # Get port from environment variable (Cloud Run sets this)
    port = int(os.environ.get("PORT", 8080))
    
    # Run uvicorn with proper Cloud Run configuration
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
