"""Motor de comparación para Curador.

Las referencias se guardan sólo como texto extraído: no se copian PDFs ni videos
subidos, lo que mantiene el repositorio liviano y seguro para GitHub.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
BASE_PATH = DATA_DIR / "base_conocimiento.json"
CACHE_PATH = DATA_DIR / "embeddings_cache.json"

_model = None
_whisper_models: dict[str, Any] = {}


def extract_pdf_text(path: str | Path) -> str:
    """Extrae texto de un PDF digital (los escaneados requieren OCR)."""
    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(page for page in pages if page)
    if not text.strip():
        raise ValueError("No se pudo extraer texto. Si es un PDF escaneado, primero aplicale OCR.")
    return text


def chunk_text(text: str, size: int = 900, overlap: int = 140) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind(". ", start, end)
            if boundary > start + size // 2:
                end = boundary + 1
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = end - overlap
    return chunks


def _load_base() -> list[dict[str, str]]:
    if not BASE_PATH.exists():
        return []
    return json.loads(BASE_PATH.read_text(encoding="utf-8"))


def _save_base(base: list[dict[str, str]]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    BASE_PATH.write_text(json.dumps(base, ensure_ascii=False, indent=2), encoding="utf-8")
    if CACHE_PATH.exists():
        CACHE_PATH.unlink()


def bootstrap_from_existing_project() -> int:
    """Importa una única vez la base del proyecto original si Curador está vacío.

    Convierte su esquema anterior (``libro``) al de Curador (``documento``).
    La copia resultante queda en ``Curador/data`` y desde entonces ambos
    proyectos pueden evolucionar por separado.
    """
    if BASE_PATH.exists() and _load_base():
        return 0
    legacy_path = ROOT.parent / "base_conocimiento.json"
    if not legacy_path.exists():
        return 0
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    converted = []
    for item in legacy:
        text = item.get("texto", "").strip()
        if not text:
            continue
        document = item.get("libro", "Referencia sin nombre")
        converted.append({
            "documento": document,
            "fragmento": str(item.get("fragmento", len(converted) + 1)),
            "texto": text,
            "hash": hashlib.sha256((document + text).encode("utf-8")).hexdigest(),
        })
    if converted:
        _save_base(converted)
    return len(converted)


def add_reference_pdf(path: str | Path, original_name: str) -> dict[str, int | str]:
    text = extract_pdf_text(path)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    base = [item for item in _load_base() if item.get("documento") != original_name]
    chunks = chunk_text(text)
    base.extend({"documento": original_name, "fragmento": str(i + 1), "texto": chunk, "hash": digest}
                for i, chunk in enumerate(chunks))
    _save_base(base)
    return {"documento": original_name, "fragmentos": len(chunks)}


def references_summary() -> list[dict[str, int | str]]:
    summary: dict[str, int] = {}
    for item in _load_base():
        summary[item["documento"]] = summary.get(item["documento"], 0) + 1
    return [{"documento": name, "fragmentos": count} for name, count in sorted(summary.items())]


def clear_references() -> None:
    _save_base([])


def _sentence_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embeddings(base: list[dict[str, str]]):
    from sentence_transformers import util
    import torch

    fingerprint = hashlib.sha256("".join(item["hash"] for item in base).encode()).hexdigest()
    if CACHE_PATH.exists():
        cached = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        if cached.get("fingerprint") == fingerprint:
            return torch.tensor(cached["values"], dtype=torch.float32), util

    model = _sentence_model()
    values = model.encode([item["texto"] for item in base], convert_to_tensor=True)
    CACHE_PATH.write_text(json.dumps({"fingerprint": fingerprint, "values": values.tolist()}), encoding="utf-8")
    return values, util


def compare_text(text: str, limit: int = 8) -> dict[str, Any]:
    base = _load_base()
    if not base:
        raise ValueError("Todavía no hay PDFs de referencia. Cargá al menos uno primero.")
    if not text.strip():
        raise ValueError("El archivo no contiene texto para comparar.")
    model = _sentence_model()
    embeddings, util = _embeddings(base)
    # Un video de varios minutos supera el contexto del modelo si se lo codifica
    # de una vez. Fragmentarlo conserva sus conceptos y se procesa en lote.
    queries = model.encode(chunk_text(text, size=900, overlap=100), convert_to_tensor=True)
    scores = util.cos_sim(queries, embeddings).max(dim=0).values
    best = scores.topk(min(limit, len(base)))
    matches = []
    for index, score in zip(best.indices, best.values):
        item = base[int(index)]
        matches.append({
            "documento": item["documento"], "fragmento": item["fragmento"],
            "puntaje": round(float(score) * 100, 1), "texto": item["texto"]
        })
    average = round(sum(match["puntaje"] for match in matches) / len(matches), 1)
    return {"promedio": average, "coincidencias": matches, "texto": text}


def transcribe_video(path: str | Path, model_size: str = "tiny") -> str:
    """Transcribe. tiny es intencionalmente el valor por defecto para agilizar CPU."""
    import shutil
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("No se encontró ffmpeg en PATH. Instalalo para analizar videos.")
    if model_size not in {"tiny", "base", "small"}:
        model_size = "tiny"
    if model_size not in _whisper_models:
        import whisper
        _whisper_models[model_size] = whisper.load_model(model_size)
    result = _whisper_models[model_size].transcribe(str(path), language="es", fp16=False, verbose=False)
    return result["text"].strip()
