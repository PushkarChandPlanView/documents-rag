#!/bin/bash
set -e

echo "Pulling Ollama models..."

LLM_MODEL=${OLLAMA_LLM_MODEL:-llama3}
EMBED_MODEL=${OLLAMA_EMBED_MODEL:-nomic-embed-text}

ollama pull "${LLM_MODEL}"
echo "Pulled LLM model: ${LLM_MODEL}"

ollama pull "${EMBED_MODEL}"
echo "Pulled embedding model: ${EMBED_MODEL}"

# Optional: pull mistral as fallback
# ollama pull mistral

echo "All models pulled successfully."
ollama list
