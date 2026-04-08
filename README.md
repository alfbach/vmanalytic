# VMAnalytic App

**VMAnalytic** is a web application for analyzing VMware inventory from **RVTools**-style Excel workbooks or from a live **vCenter** connection. It provides overview metrics, risk scoring, migration duration estimates, and charts—without requiring Jupyter.

---

## Features

- **Import** — Upload one or more RVTools `.xlsx` files, or connect to vCenter (via pyVmomi) and build a compatible workbook in memory.
- **Overview** — Execution log and high-level status after analysis.
- **Risk analysis** — Overall risk score, discovered guest OS lists (in/out of scope), pattern-based scope controls, and tabular outputs (e.g. migration complexity).
- **Duration estimate** — Migration time estimates with FTE-based calendar recalculation and per-environment inclusion.
- **Graphics** — Matplotlib figures as PNG previews in the browser.
- **Light UI** — Modern light interface suitable for desktop use; optional **Waitress** (local) or **Gunicorn** (Docker).

---

## Requirements

- **Python 3.12+** (recommended) for running from source.
- **RVTools exports** must include at least sheets: `vInfo`, `vHost`, `vDisk` (names normalized automatically where possible).

Python dependencies are listed in [`requirements.txt`](requirements.txt) (Flask, Waitress, pyVmomi, pandas, NumPy, Matplotlib, openpyxl, etc.).

---

## Installation (from source)

Clone or extract this repository, then from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\activate           # Windows (cmd)

pip install -r requirements.txt
```

---

## Running the application

### Option A — Flask development server

```bash
export FLASK_APP=web.app
flask run --host 127.0.0.1 --port 5000
```

Or use the helper script [`run-web.sh`](run-web.sh) (Linux / macOS).

### Option B — Waitress (recommended for local desktop use)

Starts **Waitress** and opens your default browser (where a display is available).

**Linux / macOS:**

```bash
chmod +x Start-VMAnalytic.sh
./Start-VMAnalytic.sh
```

**Windows:**

```text
Start-VMAnalytic.bat
```

**Manual:**

```bash
export PYTHONPATH="$(pwd)"
python local_server.py
```

Optional environment variables: `HOST` (default `127.0.0.1`), `PORT` (default `5000`), `WAITRESS_THREADS`.

### Option C — Docker

Build and run from the repository root:

```bash
docker build -t vmanalytic .
docker run --rm -p 5000:5000 \
  -e FLASK_SECRET_KEY="$(openssl rand -hex 32)" \
  vmanalytic
```

Then open `http://localhost:5000`.

The image uses **Gunicorn** on port **5000** inside the container.

### Option D — Kubernetes

Manifests live under [`k8s/`](k8s/). Create a secret for `FLASK_SECRET_KEY`, then apply:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl -n vmanalytic create secret generic vmanalytic-secrets \
  --from-literal=flask-secret-key="$(openssl rand -hex 32)"
kubectl apply -k k8s/
```

Edit `k8s/deployment.yaml` to point `image:` at your registry. See comments in [`k8s/kustomization.yaml`](k8s/kustomization.yaml).

### Option E — PyInstaller (standalone binary)

- **Windows:** run [`build-windows-exe.ps1`](build-windows-exe.ps1) on Windows → `dist/VMAnalytic.exe`.
- **Linux / macOS:** run [`build-linux-app.sh`](build-linux-app.sh) on the target OS → `dist/VMAnalytic`.

Bundled runs store writable data under the platform-specific user data directory (see below).

---

## Configuration

| Variable | Description |
|----------|-------------|
| `FLASK_SECRET_KEY` | Secret key for Flask sessions (set in production / Docker / Kubernetes). |
| `HOST` | Bind address for Waitress (default `127.0.0.1`). |
| `PORT` | Port (default `5000`). |
| `VMANALYTIC_ROOT` | Override for the project “root” used for sessions and pattern files (advanced; set automatically for frozen PyInstaller builds). |
| `XDG_DATA_HOME` | Linux: base directory for user data (default `~/.local/share`). |

---

## Data and storage

- **From source:** analysis sessions and uploads are created under `data/uploads/` in the project tree.
- **PyInstaller (frozen):** writable data is stored under:
  - **Windows:** `%LOCALAPPDATA%\VMAnalytic`
  - **Linux:** `$XDG_DATA_HOME/VMAnalytic` (often `~/.local/share/VMAnalytic`)
  - **macOS:** `~/Library/Application Support/VMAnalytic`
- **`helper_files/`** — OS filter and ignore patterns; copied into each session when running from a repository checkout; bundled apps copy defaults into the user data directory on first run.

---

## Project layout (overview)

| Path | Role |
|------|------|
| [`web/`](web/) | Flask app (`app.py`), templates, static assets |
| [`vm_analysis/`](vm_analysis/) | Analysis pipeline (`runner.py`, `body_exec.py`, vCenter collector, etc.) |
| [`helper_files/`](helper_files/) | Pattern text files for OS filtering |
| [`local_server.py`](local_server.py) | Waitress entry point for desktop use |
| [`k8s/`](k8s/) | Kubernetes manifests |
| [`Dockerfile`](Dockerfile) | Container image |

---

## License

This program is **free software**: you can redistribute it and/or modify it under the terms of the **GNU General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version**.

The full text of the GNU General Public License version 2 is included in the [`LICENSE`](LICENSE) file in this repository.

This program is distributed in the hope that it will be useful, but **without any warranty**; without even the implied warranty of **merchantability** or **fitness for a particular purpose**. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see [https://www.gnu.org/licenses/old-licenses/gpl-2.0.html](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html).

### Copyright

Copyright © 2026 VMAnalytic contributors.

To apply the GPL v2 to your own work, add the standard copyright and license notices to each source file, as described in the “How to Apply These Terms to Your New Programs” section at the end of the [`LICENSE`](LICENSE) file.

---

## Third-party components

This software uses several open-source libraries (Flask, pandas, Matplotlib, pyVmomi, etc.). Their respective licenses apply to those components. The GNU GPL v2 applies to **this project’s** combined work when distributed as a whole, subject to the usual GPL compatibility rules for linked libraries.
