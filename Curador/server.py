from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from analysis_engine import (
    DATA_DIR, add_reference_pdf, clear_references, compare_text, extract_pdf_text,
    references_summary, transcribe_video, bootstrap_from_existing_project,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2 GB
RESULTS_PATH = DATA_DIR / "resultados.json"

# Conserva y utiliza la base que ya construiste en el proyecto original, pero
# la transforma a una copia propia de Curador antes de servir la aplicación.
IMPORTED_LEGACY_CHUNKS = bootstrap_from_existing_project()


def error(message: str, status: int = 400):
    return jsonify({"ok": False, "error": message}), status


def save_result(kind: str, filename: str, result: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    previous = json.loads(RESULTS_PATH.read_text(encoding="utf-8")) if RESULTS_PATH.exists() else []
    previous.append({"fecha": datetime.now(timezone.utc).isoformat(), "tipo": kind, "archivo": filename,
                     "promedio": result["promedio"], "coincidencias": result["coincidencias"]})
    RESULTS_PATH.write_text(json.dumps(previous[-30:], ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/referencias")
def get_references():
    return jsonify({"ok": True, "referencias": references_summary()})


@app.post("/api/referencias")
def upload_references():
    files = request.files.getlist("archivos")
    if not files or not any(file.filename for file in files):
        return error("Elegí uno o más PDFs de referencia.")
    loaded = []
    with tempfile.TemporaryDirectory() as directory:
        for file in files:
            filename = secure_filename(file.filename or "documento.pdf")
            if not filename.lower().endswith(".pdf"):
                return error(f"{filename}: sólo se aceptan PDFs.")
            path = Path(directory) / filename
            file.save(path)
            loaded.append(add_reference_pdf(path, filename))
    return jsonify({"ok": True, "cargados": loaded, "referencias": references_summary()})


@app.delete("/api/referencias")
def delete_references():
    clear_references()
    return jsonify({"ok": True})


@app.post("/api/analizar")
def analyze():
    file = request.files.get("archivo")
    if not file or not file.filename:
        return error("Elegí un video o un PDF para analizar.")
    filename = secure_filename(file.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".mp4", ".mov", ".mkv", ".avi", ".webm"}:
        return error("Formato no soportado. Usá PDF, MP4, MOV, MKV, AVI o WEBM.")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / filename
        file.save(path)
        if suffix == ".pdf":
            text, kind = extract_pdf_text(path), "PDF"
        else:
            text, kind = transcribe_video(path, request.form.get("calidad", "tiny")), "video"
        result = compare_text(text)
    save_result(kind, filename, result)
    return jsonify({"ok": True, "tipo": kind, "archivo": filename, **result})


@app.get("/api/historial")
def history():
    values = json.loads(RESULTS_PATH.read_text(encoding="utf-8")) if RESULTS_PATH.exists() else []
    return jsonify({"ok": True, "resultados": list(reversed(values))})


@app.errorhandler(413)
def too_large(_):
    return error("El archivo supera el límite de 2 GB.", 413)


@app.errorhandler(Exception)
def unexpected(exception):
    app.logger.exception(exception)
    return error(str(exception), 500)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
