"""
VMAnalytic App — simple web UI for RVTools analysis (no Jupyter required).

Import options:
- Upload local RVTools .xlsx file(s)
- Connect to vCenter (pyVmomi) and build a RVTools-like workbook

  cd /path/to/vma-rvtools-analysis
  pip install -r requirements.txt
  flask --app web.app run --debug
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from vm_analysis.import_session import (
    normalize_rvtools_sheet_names,
    session_from_uploaded_xlsx,
    session_from_vcenter_xlsx,
    validate_rvtools_xlsx,
)
from vm_analysis.runner import run_analysis


def _frozen() -> bool:
    return bool(getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None))


_here = Path(__file__).resolve().parent
if _frozen():
    _web_dir = Path(sys._MEIPASS) / "web"  # type: ignore[misc]
else:
    _web_dir = _here

def _default_frozen_user_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "VMAnalytic"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VMAnalytic"
    xdg = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
    return Path(xdg) / "VMAnalytic"


if os.environ.get("VMANALYTIC_ROOT"):
    WEB_ROOT = Path(os.environ["VMANALYTIC_ROOT"]).resolve()
elif _frozen():
    WEB_ROOT = _default_frozen_user_root()
else:
    WEB_ROOT = _here.parent

app = Flask(
    __name__,
    template_folder=str(_web_dir / "templates"),
    static_folder=str(_web_dir / "static"),
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024  # 256 MB uploads


@app.errorhandler(413)
def _request_entity_too_large(_e):
    flash("Upload too large (maximum 256 MB per request).", "error")
    return redirect(url_for("index"))


@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        import_mode = request.form.get("import_mode") or "upload"

        if import_mode == "upload":
            files = request.files.getlist("rvtools_files")
            files = [f for f in files if f and f.filename]
            if not files:
                flash("Please choose at least one .xlsx file.", "error")
            else:
                tmp_paths: list[tuple[str, Path]] = []
                try:
                    for f in files:
                        name = secure_filename(f.filename) or "export.xlsx"
                        if not name.lower().endswith((".xlsx", ".xls")):
                            flash(f"Skipped (not Excel): {name}", "warning")
                            continue
                        fd, path = tempfile.mkstemp(suffix=".xlsx")
                        os.close(fd)
                        p = Path(path)
                        f.save(p)
                        normalize_rvtools_sheet_names(p)
                        validate_rvtools_xlsx(p)
                        tmp_paths.append((name, p))

                    if not tmp_paths:
                        flash("No valid Excel files to process.", "error")
                    else:
                        session_root, index_nrows = session_from_uploaded_xlsx(
                            WEB_ROOT, tmp_paths
                        )
                        result = run_analysis(session_root, index_nrows=index_nrows)
                except Exception:
                    result = {
                        "success": False,
                        "error": traceback.format_exc(),
                        "log": "",
                        "figures": [],
                        "figure_titles": [],
                        "tables": [],
                        "risk_summary": None,
                        "discovered_os": None,
                        "duration": {"tables": [], "log_excerpt": "", "recalc": None},
                    }
                finally:
                    for _, p in tmp_paths:
                        try:
                            p.unlink(missing_ok=True)
                        except OSError:
                            pass

        elif import_mode == "vcenter":
            host = (request.form.get("vc_host") or "").strip()
            user = (request.form.get("vc_user") or "").strip()
            password = request.form.get("vc_password") or ""
            port = int(request.form.get("vc_port") or 443)
            vc_label = (request.form.get("vc_label") or "vcenter").strip()
            disable_ssl = request.form.get("vc_ssl_skip") == "1"
            if not host or not user:
                flash("vCenter host and username are required.", "error")
            else:
                from vm_analysis.vcenter_collect import collect_to_xlsx

                tmp_xlsx: Path | None = None
                try:
                    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
                    os.close(fd)
                    tmp_xlsx = Path(tmp_path)
                    collect_to_xlsx(
                        host,
                        user,
                        password,
                        port=port,
                        disable_ssl_verify=disable_ssl,
                        out_path=tmp_xlsx,
                    )
                    normalize_rvtools_sheet_names(tmp_xlsx)
                    validate_rvtools_xlsx(tmp_xlsx)
                    session_root, index_nrows = session_from_vcenter_xlsx(
                        WEB_ROOT, tmp_xlsx, vc_label
                    )
                    result = run_analysis(session_root, index_nrows=index_nrows)
                except Exception:
                    result = {
                        "success": False,
                        "error": traceback.format_exc(),
                        "log": "",
                        "figures": [],
                        "figure_titles": [],
                        "tables": [],
                        "risk_summary": None,
                        "discovered_os": None,
                        "duration": {"tables": [], "log_excerpt": "", "recalc": None},
                    }
                finally:
                    if tmp_xlsx is not None:
                        try:
                            tmp_xlsx.unlink(missing_ok=True)
                        except OSError:
                            pass
        else:
            flash("Unknown import mode.", "error")

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "5000")))
