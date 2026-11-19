#!/usr/bin/env bash
# Valida a chave do Google AI Studio, grava como secret no GitHub e dispara o primeiro lote.
set -euo pipefail
command -v gh >/dev/null || { echo "Instale o GitHub CLI: https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Rode antes: gh auth login"; exit 1; }
REPO="${REPO:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"

if [ -z "${GEMINI_API_KEY:-}" ]; then
  read -rsp "Cole sua chave do Google AI Studio (não aparece na tela): " GEMINI_API_KEY; echo
fi
[ -n "$GEMINI_API_KEY" ] || { echo "Chave vazia."; exit 1; }

echo "Validando chave..."
code=$(curl -s -o /dev/null -w '%{http_code}' -H "x-goog-api-key: $GEMINI_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1")
[ "$code" = "200" ] || { echo "Chave recusada pelo Google (HTTP $code)."; exit 1; }

printf '%s' "$GEMINI_API_KEY" | gh secret set GEMINI_API_KEY --repo "$REPO"
echo "Secret GEMINI_API_KEY gravado em $REPO."

gh workflow run lote.yml --repo "$REPO" -f quantidade=3
echo "Primeiro lote disparado. Acompanhe: gh run list --repo $REPO"
echo "Painel: https://${REPO%%/*}.github.io/${REPO##*/}/"
