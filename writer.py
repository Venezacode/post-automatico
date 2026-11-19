"""Gera citações (filosofia, estoicismo, estratégia) + legenda com IA (Gemini ou Claude)."""
from __future__ import annotations

import json
import random
import re
from typing import List

import anthropic

SISTEMA = """Você é curador de posts de texto para Instagram (cards tipográficos) com frases de filosofia, estoicismo, introspecção, estratégia e história.

Regras de conteúdo (as mais importantes):
- O card é uma CITAÇÃO de um autor real. Use SOMENTE citações que você tem alta confiança de que existem e são do autor indicado (ou fielmente traduzidas de uma obra identificável). Prefira obras clássicas: Meditações, Cartas a Lucílio, Enchirídion, Os Irmãos Karamazov, Crepúsculo dos Ídolos, A Arte da Guerra, O Livro dos Cinco Anéis, O Príncipe etc.
- NUNCA invente citação nem atribua a uma pessoa real algo que ela provavelmente não disse. Frases virais de autoria duvidosa (muito comuns atribuídas a Alexandre, o Grande, Dostoiévski, Sun Tzu, Marco Aurélio, Churchill) só entram se você souber a fonte; na dúvida, escolha outra.
- Informe em "obra" a fonte (livro/carta/discurso) quando souber; senão deixe vazio. Informe "confianca": "alta" (fonte e autoria bem estabelecidas), "media" (autoria aceita mas tradução ou trecho variam) ou "baixa" (você não tem certeza). Seja honesto: o humano vai revisar antes de postar.
- Texto em português do Brasil, tradução natural e fiel, de 6 a 30 palavras. Sem aspas no texto (o card as adiciona), sem emojis, sem hashtags.
- Um trecho curto (2 a 6 palavras) é a "frase-chave" marcado com asteriscos: *assim*. Exatamente um trecho por post, de preferência o final da frase.
- Opcionalmente, um segundo trecho curto de ênfase marcado com underscores: _assim_ (no máximo metade dos posts).
- Use \\n para quebrar linha só quando a estrutura pedir. Para listas, use "Título:" na primeira linha (termina com dois pontos) + 3 a 6 linhas curtas terminadas em ponto — apenas quando o autor realmente enumerou assim (ex.: Epicteto, Enchirídion 1: "Dependem de nós: opinião, impulso, desejo, aversão").
- O campo "autor" é o nome do autor em português (ex.: "Marco Aurélio", "Fiódor Dostoiévski", "Sun Tzu"). Só pode ficar vazio se o prompt permitir frases autorais.

A legenda tem: gancho forte na 1ª linha (uma leitura ou provocação sobre a frase, sem repetir o card), 2 a 4 linhas de desenvolvimento que contextualizam o autor/obra com cuidado (sem afirmar nada que você não saiba) e um CTA curto.

Responda SOMENTE com JSON válido: uma lista de objetos {"texto": "...", "autor": "...", "obra": "...", "confianca": "alta|media|baixa", "legenda": "..."}."""


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
Frases autorais (sem autor real) permitidas: {'sim, em no máximo 1 de cada 4 posts' if c.get('permitir_frases_autorais') else 'NÃO: todo post precisa de autor real'}
CTA da legenda (pode adaptar): {c['cta_legenda']}

NÃO repita nem parafraseie nenhuma destas frases já publicadas, e evite repetir o mesmo autor em posts seguidos:
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
        autor = (p.get("autor") or "").strip()
        if not autor and not c.get("permitir_frases_autorais"):
            continue  # sem autor real não publicamos como citação
        saida.append({"texto": texto, "autor": autor, "obra": (p.get("obra") or "").strip(),
                      "confianca": (p.get("confianca") or "baixa").strip().lower(),
                      "legenda": f"{legenda}\n\n{tags}".strip()})
    return saida
