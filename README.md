# OCI ARM VM Monitor

A web-based monitoring tool for creating Oracle Cloud ARM VMs. Automatically retries VM creation across availability domains until capacity becomes available.

## Features

- Live monitoring UI with real-time logs
- Server-Sent Events (SSE) for instant updates
- Start/Stop controls
- Environment configuration display
- Cycles through all 3 Ashburn availability domains
- Configurable retry interval

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/OCI_ARM_VM_MONITOR.git
cd OCI_ARM_VM_MONITOR
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your OCI credentials:

```bash
cp .env.example .env
```

Required variables:
- `OCI_TENANCY_OCID` - Your tenancy OCID
- `OCI_USER_OCID` - Your user OCID
- `OCI_FINGERPRINT` - API key fingerprint
- `OCI_PRIVATE_KEY` - Private key content (with `\n` for newlines)
- `OCI_COMPARTMENT_ID` - Compartment OCID
- `OCI_SUBNET_ID` - Subnet OCID
- `OCI_IMAGE_ID` - Ubuntu ARM image OCID
- `OCI_SSH_PUBLIC_KEY` - Your SSH public key

### 3. Run

```bash
python main.py
```

Open http://localhost:8000 in your browser.

## Deploy on Coolify

1. Push to GitHub
2. Add as new application in Coolify
3. Set environment variables in Coolify dashboard
4. Deploy (Coolify auto-detects Python)

## VM Specifications

| Property | Value |
|----------|-------|
| Shape | VM.Standard.A1.Flex |
| OCPUs | 4 (configurable) |
| Memory | 24 GB (configurable) |
| Image | Ubuntu 24.04 ARM |
| Free Tier | Yes (Always Free) |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Monitoring UI |
| `/api/start` | POST | Start VM creation loop |
| `/api/stop` | POST | Stop VM creation loop |
| `/api/status` | GET | Current status |
| `/api/logs` | GET | Get logs |
| `/api/stream` | GET | SSE log stream |
| `/api/config` | GET | Check config status |

## Notes

- ARM free tier is popular and often out of capacity
- The script will keep retrying until a VM is created
- Results are saved to `vm_creation_result.json` on success
- Check all 3 availability domains each round
