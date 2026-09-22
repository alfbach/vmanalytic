# VMAnalytic

Web app for analyzing VMware inventory from **RVTools-style `.xlsx` exports** or a **live vCenter** connection (pyVmomi).

**Features**

- Import via file upload or vCenter credentials
- Overview with execution log
- Migration **risk score** (with client-side what-if OS scope + recalculate)
- Migration **duration** estimates (FTE / environment toggles)
- Charts and tabular outputs
- Light / dark UI (PatternFly), EN / DE / FR / ES
- Optional embedded OpenShift install-config helper at `/oic/`

---

## License

**GPL-2.0-only** — see [`LICENSE`](LICENSE).

## Disclaimer

Provided **AS IS**, without warranty. Authors are not liable for damages arising from use of the software, to the maximum extent permitted by law.

---

## Requirements

| Use case | Need |
|----------|------|
| Local / server | Python **3.12+**, pip |
| Input data | RVTools `.xlsx` with sheets `vInfo`, `vHost`, `vDisk` (case-insensitive names are normalized) |
| Containers | Podman or Docker; OpenShift: `oc` CLI after `oc login` |
| `/oic/` tab (optional) | Static export of o-i-creator (`index.html` + assets); set `OIC_STATIC_ROOT` |

---

## Quick start (local)

From the **repository root**:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export FLASK_APP=web.app
flask run --host 127.0.0.1 --port 5050
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

Helpers:

```bash
./run-web.sh                 # Flask
./Start-VMAnalytic.sh        # Waitress + browser (macOS/Linux)
# Windows: Start-VMAnalytic.bat
```

On macOS, port **5000** is often used by AirPlay Receiver — prefer **5050** (or disable AirPlay Receiver).

---

## Production (bare metal / VM)

**Gunicorn**

```bash
source .venv/bin/activate
pip install -r requirements.txt 'gunicorn>=22.0.0'
export FLASK_SECRET_KEY="$(openssl rand -hex 32)"
gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 2 --timeout 600 web.app:app
```

**Waitress**

```bash
export FLASK_SECRET_KEY="$(openssl rand -hex 32)"
python local_server.py
```

Put Nginx/Apache (or an OpenShift Route) in front for TLS and access control.

---

## Podman

Build and run from the repository root (`Dockerfile`):

```bash
podman build -t vmanalytic:latest .

podman run --rm -p 5050:5000 \
  -e FLASK_SECRET_KEY="$(openssl rand -hex 32)" \
  --name vmanalytic \
  vmanalytic:latest
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

With persistent data and optional `/oic/` static mount:

```bash
mkdir -p ./data/uploads ./saved_csv_files

podman run --rm -p 5050:5000 \
  -e FLASK_SECRET_KEY="$(openssl rand -hex 32)" \
  -e OIC_STATIC_ROOT=/app/oic-static \
  -v "$(pwd)/data:/app/data:Z" \
  -v "$(pwd)/saved_csv_files:/app/saved_csv_files:Z" \
  -v "/path/to/o-i-creator/static:/app/oic-static:ro,Z" \
  --name vmanalytic \
  vmanalytic:latest
```

```bash
podman stop vmanalytic
```

macOS: `podman machine start` if the VM is not running. `:Z` is for SELinux on Linux hosts.

**Docker** (same image definition):

```bash
docker build -t vmanalytic:latest .
docker run --rm -p 5050:5000 \
  -e FLASK_SECRET_KEY="$(openssl rand -hex 32)" \
  vmanalytic:latest
```

---

## Deploy on OpenShift

Deploy from the **directory where you start** (repository root: this `README.md` + `Dockerfile`). Log in first: `oc login …`.

Manifests: [`k8s/`](k8s/).

### 1. Project + build from this directory

```bash
cd /path/to/vmanalytic

oc new-project vmanalytic
# or: oc project vmanalytic

oc new-build --name=vmanalytic --binary --strategy=docker
oc start-build vmanalytic --from-dir=. --follow
```

`--from-dir=.` uploads the current directory; OpenShift builds into ImageStream `vmanalytic:latest`. No external registry push needed.

Rebuild later from the same directory:

```bash
oc start-build vmanalytic --from-dir=. --follow
```

### 2. Secret

```bash
oc -n vmanalytic create secret generic vmanalytic-secrets \
  --from-literal=flask-secret-key="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | oc apply -f -
```

### 3. Deploy

```bash
oc apply -k k8s/
oc -n vmanalytic set image deployment/vmanalytic \
  app=image-registry.openshift-image-registry.svc:5000/vmanalytic/vmanalytic:latest
oc -n vmanalytic rollout status deployment/vmanalytic
```

If the Deployment was applied before the first successful build, wait for the build, then run `set image` / `rollout` again.

Optional PVC (edit storage class in `k8s/pvc.yaml`, then wire volumes as documented there):

```bash
oc apply -f k8s/pvc.yaml
```

### 4. Route

```bash
oc -n vmanalytic expose service/vmanalytic --name=vmanalytic
oc -n vmanalytic get route vmanalytic
```

Fixed host (example):

```bash
oc -n vmanalytic create route edge vmanalytic \
  --service=vmanalytic \
  --hostname=vmanalytic.apps.example.com
```

### 5. Verify

```bash
oc -n vmanalytic get pods,svc,route,build,imagestream
oc -n vmanalytic logs -f deploy/vmanalytic
```

Analysis can take several minutes; container Gunicorn timeout is **600s**.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `FLASK_SECRET_KEY` | **Required** in production (sessions / flash) |
| `HOST` / `PORT` | Listen address for local Waitress/Flask helpers |
| `VMANALYTIC_ROOT` | Custom writable data root |
| `OIC_STATIC_ROOT` | Directory with o-i-creator static files for `/oic/` |

---

## Project layout (short)

```
web/              Flask UI (templates, static, i18n)
vm_analysis/      Import, vCenter collect, analysis pipeline
helper_files/     OS / ignore pattern defaults
k8s/              OpenShift / Kubernetes manifests
Dockerfile        Container image (Gunicorn)
```

---

## Notes

- Prefer a strong `FLASK_SECRET_KEY` and network access control; the UI has no built-in login.
- Upload sessions are stored under `data/uploads/` (or the mounted volume in containers).
- Without `OIC_STATIC_ROOT` (or a valid mount), the OpenShift helper tab returns 404 for `/oic/`.

---

Copyright (c) 2026 VMAnalytic contributors.
