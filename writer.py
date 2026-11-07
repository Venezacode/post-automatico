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
- Um trecho curto (2 a 6 palavras) é a "frase-chave" e vai marcado com asteriscos: *assim*. Exatamente um trecho por post, de preferência o final da frase.
- Opcionalmente, um segundo trecho curto de ênfase marcado com underscores: _assim_ (use em no máximo metade dos posts).
- Varie o formato entre os posts: frase curta de impacto (até 12 palavras), frase em duas partes (setup + virada), lista "Regra de X:" com 4 a 6 linhas curtas terminadas em ponto (primeira linha termina com dois pontos), e post em tom de tweet ("Porrada de marketing:" + 2 parágrafos curtos).
- Use \\n para quebrar linha só quando a estrutura pedir (listas, "Título:" + corpo).
- Não use emojis, hashtags nem aspas dentro do card.

A legenda tem: gancho forte na 1ª linha (diferente do card, aprofunda ou provoca), 2 a 4 linhas de desenvolvimento, e um CTA curto.

Responda SOMENTE com JSON válido: uma lista de objetos {"texto": "...", "legenda": "..."}."""


def _gemini(modelo: str, pedido: str) -> str:
    """Google Gemini via REST (camada gratuita do AI Studio). Chave em GEMINI_API_KEY."""
    import os
    import requests
    import time
    ultimo = ""
    for tentativa in range(2):
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": SISTEMA}]},
                    "contents": [{"role": "user", "parts": [{"text": pedido}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 1.0},
                },
                timeout=120,
            )
        except requests.exceptions.RequestException as e:
            ultimo = str(e)
            time.sleep(10)
            continue
        if r.ok:
            break
        ultimo = f"{r.status_code}: {r.text[:400]}"
        if r.status_code not in (429, 500, 502, 503, 504):
            break
        time.sleep(20)
    else:
        raise RuntimeError(f"Gemini falhou: {ultimo}")
    if not r.ok:
        raise RuntimeError(f"Gemini falhou: {ultimo}")
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
    modelo = ia.get("modelo", "claude-sonnet-5-5")
    if provedor == "gemini":
        bruto, erros = None, []
        for m in ia.get("modelos", ["gemini-flash-latest"]):
            try:
                bruto = _gemini(m, pedido)
                break
            except Exception as e:
                erros.append(f"{m}: {str(e)[:160]}")
                print("modelo falhou, tentando o próximo:", erros[-1])
        if bruto is None:
            raise RuntimeError("Todos os modelos Gemini falharam: " + " | ".join(erros))
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
        if texto.count("_") != 2:
            texto = texto.replace("_", "")
        legenda = p["legenda"].replace("\\n", "\n").strip()
        saida.append({"texto": texto, "legenda": f"{legenda}\n\n{tags}".strip()})
    return saida
