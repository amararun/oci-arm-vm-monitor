"""
OCI ARM VM Monitor - FastAPI app to create Oracle Cloud ARM VMs
Retries until capacity is available, with live monitoring UI
"""

from dotenv import load_dotenv
load_dotenv()

import os
import json
import asyncio
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

import oci
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Global state
class AppState:
    is_running: bool = False
    should_stop: bool = False
    current_attempt: int = 0
    last_status: str = "Idle"
    logs: list = []
    vm_created: bool = False
    vm_details: Optional[dict] = None
    task: Optional[asyncio.Task] = None

state = AppState()

# Configuration from environment variables
def get_config():
    return {
        "tenancy_ocid": os.getenv("OCI_TENANCY_OCID"),
        "user_ocid": os.getenv("OCI_USER_OCID"),
        "fingerprint": os.getenv("OCI_FINGERPRINT"),
        "private_key": os.getenv("OCI_PRIVATE_KEY", "").replace("\\n", "\n"),
        "region": os.getenv("OCI_REGION", "us-ashburn-1"),
        "compartment_id": os.getenv("OCI_COMPARTMENT_ID"),
        "subnet_id": os.getenv("OCI_SUBNET_ID"),
        "image_id": os.getenv("OCI_IMAGE_ID"),
        "ssh_public_key": os.getenv("OCI_SSH_PUBLIC_KEY"),
        "display_name": os.getenv("OCI_VM_DISPLAY_NAME", "ubuntu-arm-free"),
        "ocpus": int(os.getenv("OCI_OCPUS", "4")),
        "memory_gbs": int(os.getenv("OCI_MEMORY_GBS", "24")),
        "retry_interval": int(os.getenv("OCI_RETRY_INTERVAL", "60")),
    }

def get_oci_config():
    """Create OCI config dict from environment variables"""
    cfg = get_config()
    return {
        "tenancy": cfg["tenancy_ocid"],
        "user": cfg["user_ocid"],
        "fingerprint": cfg["fingerprint"],
        "key_content": cfg["private_key"],
        "region": cfg["region"],
    }

# Availability domains for Ashburn
AVAILABILITY_DOMAINS = [
    "FpAe:US-ASHBURN-AD-1",
    "FpAe:US-ASHBURN-AD-2",
    "FpAe:US-ASHBURN-AD-3",
]

def add_log(message: str, level: str = "info"):
    """Add a log entry with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {"timestamp": timestamp, "message": message, "level": level}
    state.logs.append(entry)
    # Keep only last 500 logs
    if len(state.logs) > 500:
        state.logs = state.logs[-500:]
    print(f"[{timestamp}] [{level.upper()}] {message}")

async def try_create_vm(compute_client, config: dict, ad: str) -> tuple[bool, str, Optional[dict]]:
    """Try to create VM in specified availability domain"""
    try:
        launch_details = oci.core.models.LaunchInstanceDetails(
            compartment_id=config["compartment_id"],
            availability_domain=ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=config["ocpus"],
                memory_in_gbs=config["memory_gbs"]
            ),
            image_id=config["image_id"],
            display_name=config["display_name"],
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=config["subnet_id"],
                assign_public_ip=True
            ),
            metadata={
                "ssh_authorized_keys": config["ssh_public_key"]
            }
        )

        response = compute_client.launch_instance(launch_details)
        return True, "SUCCESS", response.data.__dict__

    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e.message):
            return False, "Out of capacity", None
        elif "LimitExceeded" in str(e.code):
            return False, "Limit exceeded", None
        else:
            return False, f"Error: {e.message[:100]}", None
    except Exception as e:
        return False, f"Exception: {str(e)[:100]}", None

async def vm_creation_loop():
    """Main loop that retries VM creation across availability domains"""
    config = get_config()
    oci_config = get_oci_config()

    # Validate config
    missing = [k for k, v in config.items() if not v and k not in ["display_name", "ocpus", "memory_gbs", "retry_interval"]]
    if missing:
        add_log(f"Missing config: {', '.join(missing)}", "error")
        state.is_running = False
        state.last_status = "Config Error"
        return

    try:
        compute_client = oci.core.ComputeClient(oci_config)
    except Exception as e:
        add_log(f"Failed to create OCI client: {e}", "error")
        state.is_running = False
        state.last_status = "OCI Client Error"
        return

    add_log(f"Starting VM creation loop (Shape: VM.Standard.A1.Flex, {config['ocpus']} OCPUs, {config['memory_gbs']} GB RAM)", "info")
    add_log(f"Retry interval: {config['retry_interval']} seconds", "info")

    state.current_attempt = 0

    while not state.should_stop and not state.vm_created:
        for ad in AVAILABILITY_DOMAINS:
            if state.should_stop:
                break

            state.current_attempt += 1
            ad_short = ad.split("-")[-1]  # AD-1, AD-2, AD-3

            add_log(f"Attempt {state.current_attempt} - Trying {ad_short}...", "info")
            state.last_status = f"Trying {ad_short}..."

            success, message, details = await try_create_vm(compute_client, config, ad)

            if success:
                state.vm_created = True
                state.vm_details = details
                state.last_status = "VM Created!"
                add_log(f"SUCCESS! VM created in {ad_short}!", "success")

                # Save result to file
                result_file = "vm_creation_result.json"
                with open(result_file, "w") as f:
                    json.dump({
                        "success": True,
                        "timestamp": datetime.now().isoformat(),
                        "availability_domain": ad,
                        "attempts": state.current_attempt,
                        "details": str(details)
                    }, f, indent=2, default=str)
                add_log(f"Result saved to {result_file}", "info")
                break
            else:
                if "Out of capacity" in message:
                    add_log(f"  -> Out of capacity in {ad_short}", "warning")
                else:
                    add_log(f"  -> {message}", "warning")

        if not state.vm_created and not state.should_stop:
            add_log(f"All ADs tried. Waiting {config['retry_interval']} seconds...", "info")
            state.last_status = f"Waiting {config['retry_interval']}s..."

            # Wait with cancellation support
            for _ in range(config['retry_interval']):
                if state.should_stop:
                    break
                await asyncio.sleep(1)

    if state.should_stop and not state.vm_created:
        add_log("Stopped by user", "info")
        state.last_status = "Stopped"

    state.is_running = False

# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    add_log("OCI ARM VM Monitor started", "info")
    yield
    # Shutdown
    state.should_stop = True
    if state.task:
        state.task.cancel()

app = FastAPI(title="OCI ARM VM Monitor", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main monitoring UI"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/start")
async def start_creation():
    """Start the VM creation loop"""
    if state.is_running:
        return JSONResponse({"status": "error", "message": "Already running"}, status_code=400)

    state.is_running = True
    state.should_stop = False
    state.vm_created = False
    state.vm_details = None
    state.logs = []
    state.current_attempt = 0

    # Start background task
    state.task = asyncio.create_task(vm_creation_loop())

    return {"status": "ok", "message": "Started"}

@app.post("/api/stop")
async def stop_creation():
    """Stop the VM creation loop"""
    if not state.is_running:
        return JSONResponse({"status": "error", "message": "Not running"}, status_code=400)

    state.should_stop = True
    add_log("Stop requested...", "info")

    return {"status": "ok", "message": "Stop requested"}

@app.get("/api/status")
async def get_status():
    """Get current status"""
    return {
        "is_running": state.is_running,
        "current_attempt": state.current_attempt,
        "last_status": state.last_status,
        "vm_created": state.vm_created,
        "vm_details": state.vm_details,
        "log_count": len(state.logs)
    }

@app.get("/api/logs")
async def get_logs(since: int = 0):
    """Get logs since index"""
    return {
        "logs": state.logs[since:],
        "total": len(state.logs)
    }

@app.get("/api/stream")
async def stream_logs():
    """Server-Sent Events stream for live logs"""
    async def event_generator():
        last_index = 0
        last_status = ""

        while True:
            # Send new logs
            if len(state.logs) > last_index:
                new_logs = state.logs[last_index:]
                for log in new_logs:
                    yield f"data: {json.dumps({'type': 'log', 'data': log})}\n\n"
                last_index = len(state.logs)

            # Send status updates
            current_status = json.dumps({
                "is_running": state.is_running,
                "current_attempt": state.current_attempt,
                "last_status": state.last_status,
                "vm_created": state.vm_created
            })
            if current_status != last_status:
                yield f"data: {json.dumps({'type': 'status', 'data': json.loads(current_status)})}\n\n"
                last_status = current_status

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        }
    )

@app.get("/api/config")
async def get_config_status():
    """Check if config is set (without exposing values)"""
    config = get_config()
    return {
        "configured": {
            k: bool(v) for k, v in config.items()
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
