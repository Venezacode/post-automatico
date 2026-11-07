"""Gera frases + legenda com a API da Claude (Anthropic)."""
from __future__ import annotations

import json
import random
import re
from typing import List

import anthropic

SISTEMA = """Você é redator de posts de texto para Instagram (cards tipográficos), no estilo de criadores de marketing e negócios do Brasil.

Características dos posts de referência:
- Frase curta e afirmativa, de 8 a 25 palavras no total.
- Formatos que funcionam: "Regra de marketing:" + lista curta de verbos (Conteúdo atrai. Repetição faz lembrar.); contraste "isso vs. aquilo"; verdade incômoda; inversão de crença comum; frase-sentença ("Estar pronto não é um sentimento, é uma decisão.").
- Linguagem natural, falada, sem jargão vazio. Concreta, nunca vaga.
- Um trecho curto (2 a 6 palavras) é a "frase-chave" e vai marcado com asteriscos: *assim*. Exatamente um trecho por post.
- Use \\n para quebrar linha só quando a estrutura pedir (listas, "Título:" + corpo).
- Não use emojis, hashtags nem aspas dentro do card.

A legenda tem: gancho forte na 1ª linha (diferente do card, aprofunda ou provoca), 2 a 4 linhas de desenvolvimento, e um CTA curto.

Responda SOMENTE com JSON válido: uma lista de objetos {"texto": "...", "legenda": "..."}."""


def _gemini(modelo: str, pedido: str) -> str:
    """Google Gemini via REST (camada gratuita do AI Studio). Chave em GEMINI_API_KEY."""
    import os
    import requests
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"},
        json={
            "systemInstruction": {"parts": [{"text": SISTEMA}]},
            "contents": [{"role": "user", "parts": [{"text": pedido}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0},
        },
        timeout=90,
    )
    if not r.ok:
        raise RuntimeError(f"Gemini falhou ({r.status_code}): {r.text[:400]}")
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def gerar(cfg: dict, quantidade: int, historico: List[str]) -> List[dict]:
    c = cfg["conteudo"]
    pilares = random.sample(c["pilares"], k=min(quantidade, len(c["pilares"])))
    recentes = "\n".join(f"- {t.replace(chr(10), ' ')}" for t in historico[-40:]) or "(nenhum ainda)"
    pedido = f"""Crie {quantidade} post(s) novo(s).
Idioma: {c['idioma']}
Nicho: {c['nicho']}
Tom: {c['tom']}
Um post para cada um destes pilares, nesta ordem: {json.dumps(pilares, ensure_ascii=False)}
Evitar: {json.dumps(c.get('evitar', []), ensure_ascii=False)}
CTA da legenda (pode adaptar): {c['cta_legenda']}

NÃO repita nem parafraseie nenhuma destas frases já publicadas:
{recentes}"""

    ia = cfg.get("ia", {})
    provedor = ia.get("provedor", "gemini")
    modelo = ia.get("modelo", "gemini-3.8-flash" if provedor == "gemini" else "claude-sonnet-5-5")
    if provedor == "gemini":
        bruto = _gemini(modelo, pedido)
    else:
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=modelo, max_tokens=2000, system=SISTEMA,
            messages=[{"role": "user", "content": pedido}],
        )
        bruto = "".join(b.text for b in resp.content if b.type == "text")
    m = re.search(r"\[.*\]", bruto, re.S)
    posts = json.loads(m.group(0) if m else bruto)
    tags = " ".join("#" + h.lstrip("#") for h in c.get("hashtags", []))
    saida = []
    for p in posts[:quantidade]:
        texto = p["texto"].replace("\\n", "\n").strip()
        if texto.count("*") != 2:  # garante um único destaque
            texto = texto.replace("*", "")
        legenda = p["legenda"].replace("\\n", "\n").strip()
        saida.append({"texto": texto, "legenda": f"{legenda}\n\n{tags}".strip()})
    return saida
