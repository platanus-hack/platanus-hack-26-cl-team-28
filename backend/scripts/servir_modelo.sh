#!/usr/bin/env bash
# Levanta llama-server con un modelo local en la GPU NVIDIA, listo para scripts/probar_modelo.py.
#
# Uso:
#     scripts/servir_modelo.sh [qwen9|gemma12|qwen4|<repo-hf>[:<cuant>]] [opciones extra de llama-server]
#
# Requiere llama.cpp con CUDA:  sudo pacman -S llama-cpp ggml-cuda
# La primera vez descarga el modelo desde Hugging Face y lo deja en caché.
#
# Variables opcionales:
#     SLOTS    personas atendidas en paralelo
#     CTX      contexto total en tokens, repartido entre los slots
#     PUERTO   puerto local (por defecto 8080)
#     GPU      dispositivo, según `llama-server --list-devices` (por defecto CUDA0)
#     LLAMA_SERVER  ruta al binario si no está en el PATH
set -euo pipefail

modelo="${1:-qwen9}"
# El contexto se reparte entre los slots. Un perfil completo de scripts/personas_muestra.py son
# unos 1.200 tokens (hasta 1.400) y con la política y las preguntas el prompt pasa de 2.000:
# cada slot necesita unos 2.560. Con perfiles cortos (--secciones, o el filtro de scripts/filtro_perfil.py,
# que deja el perfil en 390 a 650 tokens) alcanza con menos; con el filtro no se ha medido todavía.
slots=16
ctx=40960
case "$modelo" in
    # Mismos 20.480 tokens de contexto que antes, que es lo que cabe en 8 GB, en la mitad de slots. Sin medir todavía.
    qwen9)   repo="unsloth/Qwen3.5-9B-GGUF:Q4_K_M"; slots=8; ctx=20480 ;;
    # Con 32.768 ocupó 4,7 GB de los 8; 40.960 está sin medir.
    qwen4)   repo="unsloth/Qwen3.5-4B-GGUF:Q4_K_M" ;;
    # 7 GB de pesos en 8 GB de VRAM: queda espacio para menos contexto. Sin medir todavía.
    gemma12) repo="google/gemma-4-12B-it-qat-q4_0-gguf"; slots=4; ctx=8192 ;;
    */*)     repo="$modelo" ;;
    *)       echo "Modelo desconocido: $modelo (usa qwen9, gemma12, qwen4 o <repo-hf>[:<cuant>])" >&2; exit 2 ;;
esac

servidor="${LLAMA_SERVER:-llama-server}"
if ! command -v "$servidor" >/dev/null; then
    echo "No encuentro llama-server. Instálalo con: sudo pacman -S llama-cpp ggml-cuda" >&2
    exit 1
fi

# --reasoning off: sin razonamiento previo, la respuesta son solo los cinco números.
# --no-mmproj:     no carga el proyector de imágenes, que ocuparía VRAM sin usarse.
# -ngl all:        todas las capas en la GPU; si no caben, falla en vez de usar la CPU en silencio.
# --cache-ram 0:   sin copia de cada prompt a la RAM; aquí solo sirve el caché del prefijo en la GPU.
exec "$servidor" \
    -hf "$repo" \
    --device "${GPU:-CUDA0}" \
    -ngl all \
    --fit off \
    -c "${CTX:-$ctx}" \
    -np "${SLOTS:-$slots}" \
    --reasoning off \
    --no-mmproj \
    --cache-ram 0 \
    --host 127.0.0.1 \
    --port "${PUERTO:-8080}" \
    "${@:2}"
