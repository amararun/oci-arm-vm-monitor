# OCI ARM VM Monitor

A web-based monitoring tool for creating Oracle Cloud ARM VMs. Automatically retries VM creation across availability domains until capacity becomes available.

## Why This Tool?

Oracle Cloud's Always Free ARM instances (4 OCPUs, 24 GB RAM) are highly sought after and frequently out of capacity. This tool automates the retry process, cycling through all availability domains until an instance is successfully provisioned.

## Features

- Live monitoring UI with real-time logs
- Server-Sent Events (SSE) for instant updates
- Start/Stop controls
- Environment configuration display
- Cycles through all 3 availability domains
- Configurable retry intervals
- HTTP Basic Auth protection

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/amararun/oci-arm-vm-monitor.git
cd oci-arm-vm-monitor
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

**Required variables:**

| Variable | Description |
|----------|-------------|
| `AUTH_USERNAME` | HTTP Basic Auth username |
| `AUTH_PASSWORD` | HTTP Basic Auth password |
| `OCI_TENANCY_OCID` | Your tenancy OCID |
| `OCI_USER_OCID` | Your user OCID |
| `OCI_FINGERPRINT` | API key fingerprint |
| `OCI_PRIVATE_KEY` | Private key content (with `\n` for newlines) |
| `OCI_COMPARTMENT_ID` | Compartment OCID |
| `OCI_SUBNET_ID` | Subnet OCID |
| `OCI_IMAGE_ID` | Ubuntu ARM image OCID |
| `OCI_SSH_PUBLIC_KEY` | Your SSH public key |

**Optional variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `OCI_VM_DISPLAY_NAME` | `ubuntu-arm-free` | VM display name |
| `OCI_OCPUS` | `4` | Number of OCPUs |
| `OCI_MEMORY_GBS` | `24` | Memory in GB |
| `OCI_RETRY_INTERVAL` | `60` | Seconds between retry rounds |
| `OCI_AD_DELAY` | `5` | Seconds between AD attempts |

### 3. Run

```bash
python main.py
```

Open http://localhost:8000 in your browser. You'll be prompted for the Basic Auth credentials.

## Deploy

Deploy on your preferred platform (Render, Railway, Coolify, or your own VM) as you normally would. 

## VM Specifications

| Property | Value |
|----------|-------|
| Shape | VM.Standard.A1.Flex |
| OCPUs | 4 (configurable) |
| Memory | 24 GB (configurable) |
| Image | Ubuntu 24.04 ARM |
| Free Tier | Yes (Always Free) |

## API Endpoints

All endpoints require HTTP Basic Auth.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Monitoring UI |
| `/api/start` | POST | Start VM creation loop |
| `/api/stop` | POST | Stop VM creation loop |
| `/api/status` | GET | Current status |
| `/api/logs` | GET | Get logs |
| `/api/stream` | GET | SSE log stream |
| `/api/config` | GET | Check config status |

## Security

- All endpoints are protected with HTTP Basic Auth
- Credentials are stored as environment variables, never in code
- Always deploy behind HTTPS

## Keep-Alive Script (Optional)

Oracle may reclaim idle Always Free instances if usage stays below certain thresholds for extended periods.

**Best approach:** Deploy actual workloads (web apps, APIs, databases) - real usage naturally keeps the instance active.

**Backup option:** If you need a temporary measure while setting up, a simple keep-alive script is included. This is not guaranteed to prevent reclamation - it's just a stopgap.

```bash
sudo cp oci-keepalive.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/oci-keepalive.sh

# Add to crontab (runs every hour)
(crontab -l 2>/dev/null; echo "0 * * * * /usr/local/bin/oci-keepalive.sh") | crontab -
```

The script generates ~60 seconds of light CPU activity. Remove it once you have real workloads running.

## Notes

- ARM free tier is popular and often out of capacity
- The script will keep retrying until a VM is created
- Results are saved to `vm_creation_result.json` on success
- Checks all 3 availability domains each round

## Author

Built by [Amar Harolikar](https://www.linkedin.com/in/amarharolikar/)

Explore 30+ open source AI tools for analytics, databases & automation at [tigzig.com](https://tigzig.com)

## License

MIT
