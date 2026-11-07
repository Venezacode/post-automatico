"""Renderiza posts de texto no estilo das referências (cards tipográficos 4:5).

Marcação de destaque no texto: *frase em destaque*. Quebra de linha: \n.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent

# (fundo, texto, texto secundário)
PALETAS = {
    "claro": ("#F4F3EF", "#3A3A3C", "#6B6B6E"),
    "escuro": ("#050505", "#FFFFFF", "#8E8E93"),
    "tweet_claro": ("#FFFFFF", "#0F0F10", "#7A7A7D"),
    "tweet_escuro": ("#000000", "#FFFFFF", "#8A8A8E"),
}

_CANDIDATOS = {
    "bold": [
        "fonts/bold.ttf", "fonts/bold.otf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
        "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "fonts/regular.ttf", "fonts/regular.otf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
        "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def _achar_fonte(peso: str) -> str:
    for c in _CANDIDATOS[peso]:
        p = Path(c) if c.startswith("/") else ROOT / c
        if p.exists():
            return str(p)
    try:  # Linux: pergunta ao fontconfig
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", "Inter:bold" if peso == "bold" else "Inter"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        if out and os.path.exists(out):
            return out
    except Exception:
        pass
    raise RuntimeError(
        "Nenhuma fonte encontrada. Coloque fonts/bold.ttf e fonts/regular.ttf (ex.: Inter ou Montserrat)."
    )


_cache_fontes = {}


def fonte(peso: str, tamanho: int) -> ImageFont.FreeTypeFont:
    k = (peso, tamanho)
    if k not in _cache_fontes:
        _cache_fontes[k] = ImageFont.truetype(_achar_fonte(peso), tamanho)
    return _cache_fontes[k]


Palavra = Tuple[str, bool]  # (texto, em_destaque)


def parse(texto: str) -> List[List[Palavra]]:
    """Texto com *destaque* -> lista de parágrafos, cada um lista de (palavra, destaque)."""
    paragrafos = []
    destaque = False
    for linha in texto.strip().split("\n"):
        palavras: List[Palavra] = []
        colar = False  # próximo pedaço começa colado no anterior (sem espaço)
        for pedaco in re.split(r"(\*)", linha):
            if pedaco == "*":
                destaque = not destaque
                continue
            if not pedaco:
                continue
            tokens = pedaco.split()
            if not tokens:
                colar = False
                continue
            if colar and palavras and not pedaco[0].isspace():
                palavras[-1] = (palavras[-1][0] + tokens[0], palavras[-1][1])  # pontuação cola na palavra anterior
                tokens = tokens[1:]
            for w in tokens:
                palavras.append((w, destaque))
            colar = not pedaco[-1].isspace()
        paragrafos.append(palavras)
    return paragrafos


def _largura(texto: str, f, tracking: float) -> float:
    return f.getlength(texto) + tracking * len(texto)


def _desenhar_palavra(d, x, y, texto, f, cor, tracking):
    """Desenha com tracking (espaçamento entre letras) negativo, mantendo kerning de pares."""
    for i, ch in enumerate(texto):
        d.text((x, y), ch, font=f, fill=cor)
        if i + 1 < len(texto):
            par = f.getlength(ch + texto[i + 1]) - f.getlength(texto[i + 1])
            x += par + tracking
        else:
            x += f.getlength(ch) + tracking
    return x


def _quebrar(paragrafos, larg_max, peso_base, peso_dest, tam, tracking):
    """Quebra em linhas. Retorna lista de linhas; linha = lista de (palavra, destaque, largura)."""
    linhas = []
    espaco = fonte(peso_base, tam).getlength(" ") + tracking
    for par in paragrafos:
        if not par:
            linhas.append(None)  # linha em branco
            continue
        atual, w_atual = [], 0.0
        for palavra, dest in par:
            f = fonte(peso_dest if dest else peso_base, tam)
            w = _largura(palavra, f, tracking)
            extra = espaco if atual else 0
            if atual and w_atual + extra + w > larg_max:
                linhas.append(atual)
                atual, w_atual = [], 0.0
                extra = 0
            atual.append((palavra, dest, w))
            w_atual += extra + w
        linhas.append(atual)
    return linhas


def _avatar(perfil: dict, diametro: int, cor_fundo: str) -> Image.Image:
    caminho = ROOT / perfil.get("avatar", "")
    if caminho.is_file():
        img = Image.open(caminho).convert("RGB").resize((diametro, diametro), Image.LANCZOS)
    else:
        img = Image.new("RGB", (diametro, diametro), "#2B2B2E")
        d = ImageDraw.Draw(img)
        ini = "".join(p[0] for p in perfil["nome"].split()[:2]).upper() or "?"
        f = fonte("bold", int(diametro * 0.42))
        w = f.getlength(ini)
        d.text(((diametro - w) / 2, diametro * 0.27), ini, font=f, fill="#FFFFFF")
    esc = 4
    mask = Image.new("L", (diametro * esc, diametro * esc), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diametro * esc - 1, diametro * esc - 1), fill=255)
    mask = mask.resize((diametro, diametro), Image.LANCZOS)
    img.putalpha(mask)
    return img


def _selo(d: ImageDraw.ImageDraw, cx, cy, r):
    azul = "#1D9BF0"
    pts = []
    import math
    for i in range(16):
        ang = math.pi * 2 * i / 16
        rr = r if i % 2 == 0 else r * 0.86
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill=azul)
    d.line([(cx - r * 0.4, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.32), (cx + r * 0.42, cy - r * 0.3)],
           fill="#FFFFFF", width=max(2, int(r * 0.2)), joint="curve")


def renderizar(texto: str, estilo: str, cfg: dict, saida: str) -> str:
    W, H = cfg["visual"]["largura"], cfg["visual"]["altura"]
    destaque_cor = cfg["visual"]["cor_destaque"]
    perfil = cfg["perfil"]
    bg, cor_txt, cor_sec = PALETAS[estilo]
    tweet = estilo.startswith("tweet")

    # supersampling 2x para bordas suaves
    S = 2
    img = Image.new("RGB", (W * S, H * S), bg)
    d = ImageDraw.Draw(img)

    margem = int(W * 0.09) * S
    larg_max = W * S - 2 * margem
    topo_texto = 0
    base_cabecalho = 0

    # --- cabeçalho estilo tweet ---
    cab_h = 0
    if tweet:
        av = 150 * S
        cab_h = av + 70 * S
    # --- rodapé / assinatura ---
    rodape_h = 130 * S if not tweet else 110 * S

    # peso: cards "claro/escuro" são bold e compactos; tweet é regular com destaque bold
    peso_base = "regular" if tweet else "bold"
    peso_dest = "bold"
    tracking_em = -0.035 if not tweet else -0.01

    paragrafos = parse(texto)
    area_h = H * S - 2 * margem - cab_h - rodape_h
    tam = (88 if tweet else 140) * S
    while tam > 28 * S:
        tracking = tracking_em * tam
        linhas = _quebrar(paragrafos, larg_max, peso_base, peso_dest, tam, tracking)
        entre = tam * (1.12 if not tweet else 1.28)
        altura = sum((entre * 0.6 if l is None else entre) for l in linhas)
        if altura <= area_h and (not tweet or tam <= 96 * S):
            break
        tam -= 2 * S
    tracking = tracking_em * tam
    linhas = _quebrar(paragrafos, larg_max, peso_base, peso_dest, tam, tracking)
    entre = tam * (1.12 if not tweet else 1.28)
    altura = sum((entre * 0.6 if l is None else entre) for l in linhas)

    bloco_h = cab_h + altura
    y0 = (H * S - rodape_h - bloco_h) / 2 + (0 if not tweet else 0)
    y0 = max(margem, y0)

    # cabeçalho
    y = y0
    if tweet:
        av_img = _avatar(perfil, av, bg)
        img.paste(av_img, (margem, int(y)), av_img)
        nx = margem + av + 36 * S
        fn = fonte("bold", 54 * S)
        d.text((nx, y + 22 * S), perfil["nome"], font=fn, fill=cor_txt)
        if perfil.get("verificado"):
            _selo(d, nx + fn.getlength(perfil["nome"]) + 38 * S, y + 22 * S + 36 * S, 24 * S)
        d.text((nx, y + 22 * S + 74 * S), "@" + perfil["arroba"], font=fonte("regular", 46 * S), fill=cor_sec)
        y += cab_h

    # texto
    for linha in linhas:
        if linha is None:
            y += entre * 0.6
            continue
        x = margem
        for i, (palavra, dest, w) in enumerate(linha):
            f = fonte(peso_dest if dest else peso_base, tam)
            cor = destaque_cor if dest else cor_txt
            _desenhar_palavra(d, x, y, palavra, f, cor, tracking)
            x += w + fonte(peso_base, tam).getlength(" ") + tracking
        y += entre

    # assinatura (estilos claro/escuro)
    if not tweet:
        f = fonte("bold", 40 * S)
        nome = perfil["nome"]
        wn = f.getlength(nome)
        d.text(((W * S - wn) / 2, H * S - margem - 40 * S), nome, font=f, fill=cor_sec)
    else:
        f = fonte("regular", 40 * S)
        t = "@" + perfil["arroba"]
        d.text((margem, H * S - margem - 20 * S), t, font=f, fill=cor_sec)

    img = img.resize((W, H), Image.LANCZOS)
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    img.save(saida, "PNG", optimize=True)
    return saida
