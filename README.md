# VMAnalytic

VMAnalytic is a web application for analyzing VMware inventory from RVTools-style Excel exports or from a live vCenter connection.

The app provides:
- inventory overview and execution logs
- migration risk scoring
- migration duration estimation
- charts and tabular outputs
- an integrated OpenShift install-config helper tab (embedded from `/Users/abach/o-i-creator`)

---

## License (GPL-2.0)

This project is licensed under the **GNU General Public License, version 2.0** (GPL-2.0-only).

You may copy, modify, and redistribute this software under the terms of GPL v2.
See the full license text in the [`LICENSE`](LICENSE) file.

---

## Warranty and Liability Disclaimer

This software is provided **"AS IS"**, without warranty of any kind, express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, and non-infringement.

To the maximum extent permitted by applicable law, the authors and contributors are **not liable** for any claim, damages, or other liability, whether in contract, tort, or otherwise, arising from, out of, or in connection with the software or the use of the software.

---

## Requirements

- Python 3.12+ (recommended)
- pip
- RVTools exports (`.xlsx`) with required sheets such as `vInfo`, `vHost`, `vDisk`
- Optional for embedded OpenShift tab: local project available at `/Users/abach/o-i-creator` (serves static UI under `/oic/`)

---

## Local Setup (Development)

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run with Flask (development server):

```bash
export FLASK_APP=web.app
flask run --host 127.0.0.1 --port 5000
```

Open:

- [http://127.0.0.1:5000](http://127.0.0.1:5000)

Alternative local run helper:

```bash
./run-web.sh
```

---

## Run on a Web Server (Production)

### Option A: Gunicorn (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY="replace-with-a-long-random-value"
gunicorn -w 3 -b 0.0.0.0:5000 web.app:app
```

Use Nginx or Apache as reverse proxy in front of Gunicorn.

### Option B: Waitress

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY="replace-with-a-long-random-value"
python local_server.py
```

### Option C: Docker

```bash
docker build -t vmanalytic .
docker run --rm -p 5000:5000 \
  -e FLASK_SECRET_KEY="replace-with-a-long-random-value" \
  vmanalytic
```

Then open [http://localhost:5000](http://localhost:5000).

### Option D: Podman

Build the image from the project root (uses the included `Dockerfile`):

```bash
podman build -t vmanalytic:latest .
```

Run a local prototype container:

```bash
podman run --rm -p 5050:5000 \
  -e FLASK_SECRET_KEY="$(openssl rand -hex 32)" \
  --name vmanalytic \
  vmanalytic:latest
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

Optional: persist upload sessions and mount an OpenShift install-config helper static export:

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

Stop the container:

```bash
podman stop vmanalytic
```

Notes for Podman on macOS: start the machine first if needed (`podman machine start`). The `:Z` volume options help with SELinux labels on Linux; they are harmless elsewhere.

---

## Deploy on OpenShift

Manifests live under [`k8s/`](k8s/). They work with `oc` (OpenShift CLI) the same way as with `kubectl`.

### 1. Build and push the image

Pick a registry your cluster can pull from (Quay, OpenShift internal registry, etc.):

```bash
# Example: Quay
export REGISTRY=quay.io/<org>
export IMAGE=${REGISTRY}/vmanalytic:latest

podman build -t "${IMAGE}" .
podman push "${IMAGE}"
```

OpenShift internal registry (logged in with `oc`):

```bash
oc new-project vmanalytic   # or: oc project vmanalytic
HOST=$(oc get route default-route -n openshift-image-registry -o jsonpath='{.spec.host}' 2>/dev/null || true)
# Alternative: use ImageStream + build in-cluster (see below)
podman build -t image-registry.openshift-image-registry.svc:5000/vmanalytic/vmanalytic:latest .
# Prefer pushing via an exposed registry route or an external registry your cluster trusts
```

In-cluster build from the Git repo (no local push required):

oc new-project vmanalytic
oc new-build --name=vmanalytic --binary --strategy=docker
oc start-build vmanalytic --from-dir=. --follow


### 2. Create the Flask secret

```bash
oc apply -f k8s/namespace.yaml
oc -n vmanalytic create secret generic vmanalytic-secrets \
  --from-literal=flask-secret-key="$(openssl rand -hex 32)" \
  --dry-run=client -o yaml | oc apply -f -
```

### 3. Point the Deployment at your image

Edit `k8s/deployment.yaml` (or set the image after apply):

```bash
# After applying manifests, set the image you pushed / built:
oc -n vmanalytic set image deployment/vmanalytic \
  app=IMAGE_REF_HERE

# Examples:
#   app=quay.io/<org>/vmanalytic:latest
#   app=image-registry.openshift-image-registry.svc:5000/vmanalytic/vmanalytic:latest
```

### 4. Apply Kubernetes / OpenShift resources

```bash
oc apply -k k8s/
# Or individually:
# oc apply -f k8s/namespace.yaml
# oc apply -f k8s/deployment.yaml
# oc apply -f k8s/service.yaml
```

Optional persistent uploads (edit `k8s/pvc.yaml` storage class, then wire the PVC into the Deployment as described in that file):

```bash
oc apply -f k8s/pvc.yaml
```

### 5. Expose the app (Route)

Prefer an OpenShift Route over the sample Ingress:

```bash
oc -n vmanalytic expose service/vmanalytic --name=vmanalytic
# Or with a fixed host:
# oc -n vmanalytic create route edge vmanalytic --service=vmanalytic --hostname=vmanalytic.apps.example.com

oc -n vmanalytic get route vmanalytic
```

If your cluster uses Ingress instead, uncomment `ingress.yaml` in `k8s/kustomization.yaml`, set `host` / `ingressClassName`, then `oc apply -k k8s/`.

### 6. Verify

```bash
oc -n vmanalytic get pods,svc,route
oc -n vmanalytic logs -f deploy/vmanalytic
```

Open the Route URL from `oc get route`. Analysis jobs can run for several minutes; the container Gunicorn timeout is 600 seconds.

---

## Recommended Environment Variables

- `FLASK_SECRET_KEY` (required for production)
- `HOST` (default `127.0.0.1`)
- `PORT` (default `5000`)
- `VMANALYTIC_ROOT` (optional custom app data root)
- `OIC_STATIC_ROOT` (optional path to o-i-creator static export for `/oic/`)

---

## Notes

- The embedded OpenShift helper is served from `/oic/` when `OIC_STATIC_ROOT` points at a directory that contains `index.html` (and assets). In containers, mount that export and set the env var (see Podman example above).
- If that directory is missing, the OpenShift tab will not load.

---

## Copyright

Copyright (c) 2026 VMAnalytic contributors.
