# Curador de Física

Aplicación local para contrastar el contenido de videos o PDFs contra PDFs de referencia.

Al iniciarse por primera vez, Curador importa automáticamente la
`base_conocimiento.json` que está un nivel arriba (la del Evaluador de Física)
y crea su propia copia compatible en `Curador/data`. Así compara con el material
que ya preparaste, sin modificar el proyecto original. Esta copia no se sube a
GitHub por privacidad y peso.

## Inicio (Windows)

1. Instalá [FFmpeg](https://ffmpeg.org/download.html) y verificá que `ffmpeg` esté en `PATH` (sólo hace falta para videos).
2. Abrí PowerShell dentro de esta carpeta.
3. Hacé doble clic en `start_curador.bat` (recomendado), o ejecutá: `Set-ExecutionPolicy -Scope Process RemoteSigned; .\launch_windows.ps1`
4. Abrí `http://127.0.0.1:5000`.

También puede iniciarse manualmente con `python -m pip install -r requirements.txt` y `python server.py`.

## Rapidez

El modo **Rápido** usa Whisper `tiny`, mucho más veloz que `base` para CPU. Elegí **Equilibrado** o **Preciso** sólo cuando necesites más calidad. La primera transcripción por modelo y el primer cálculo de cada base pueden tardar más porque se descargan/cargan modelos y se generan embeddings; los siguientes análisis reutilizan esa caché.

## GitHub

Los PDFs, videos, resultados y cachés se ignoran con `.gitignore`; por eso podés subir el código sin incluir material pesado o sensible. PDFs escaneados sin texto requieren OCR antes de ser comparados.
