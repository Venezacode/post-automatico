"""Renderiza posts de texto copiando o visual das referências (cards tipográficos 4:5).

Marcação no texto:  *trecho em destaque*   _trecho sublinhado/itálico_   \n = quebra de linha.
Cada estilo decide como mostrar os destaques (alguns ignoram, como nas referências).
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).parent

FAMILIAS = {
    "mont": "fonts/Montserrat.ttf",
    "mont_i": "fonts/Montserrat-Italic.ttf",
    "inter": "fonts/Inter.ttf",
}

# ---------------------------------------------------------------------------
# Estilos (cada um espelha uma das referências)
# ---------------------------------------------------------------------------
ESTILOS = {
    # Daniel Schumacher: papel off-white, extra-bold apertadíssimo, nome centrado embaixo
    "papel": dict(bg="#F4F3EF", cor="#3A3A3C", sec="#58585C", fam="mont", peso=800, tam=132, lh=0.99,
                  tr=-0.058, ml=0.115, mr=0.09, grain=0.045, ass="nome_centro", dest="nenhum", teto=0.70),
    # Alfredo Soares (branco): bold preto + frase em vermelho, @ pequeno abaixo
    "branco_vermelho": dict(bg="#FFFFFF", cor="#0B0B0C", sec="#9B9B9E", fam="mont", peso=700, tam=104, lh=1.03,
                            tr=-0.042, ml=0.07, mr=0.07, ass="handle_abaixo", dest="vermelho", teto=0.62),
    # sucessoo.on: fundo preto, CAIXA ALTA pesada, aspas vermelhas
    "caixa_alta": dict(bg="#050505", cor="#FFFFFF", sec="#A0A0A5", fam="mont", peso=800, tam=88, lh=1.0,
                       tr=-0.022, ml=0.10, mr=0.10, ass="handle_abaixo", dest="nenhum", upper=True, aspas=True, teto=0.52),
    # Pedro Sobral: escuro granulado, texto leve, trechos em negrito itálico sublinhado / vermelho
    "escuro_leve": dict(bg="#0C0C0D", cor="#F4F4F4", sec="#8A8A8E", fam="mont", peso=300, tam=104, lh=1.08,
                        tr=-0.055, ml=0.10, mr=0.08, grain=0.07, ass="handle_abaixo", dest="leve", teto=0.62),
    # Joel Jota: branco, semibold cinza grande
    "semibold_cinza": dict(bg="#FFFFFF", cor="#4A4A4D", sec="#9B9B9E", fam="inter", peso=640, tam=94, lh=1.27,
                           tr=-0.022, ml=0.07, mr=0.07, ass=None, dest="escuro", teto=0.68),
    # maryaclaramarketing: "REGRA DE ...:" + lista, tom marrom
    "regra": dict(bg="#FBFAF7", cor="#6A5F4F", sec="#A8A092", fam="mont", peso=700, tam=72, lh=1.03,
                  tr=-0.04, ml=0.09, mr=0.08, ass="handle_abaixo", dest="nenhum", upper_first=True, teto=0.52),
    # Kaue / Alfredo / William: cabeçalho estilo tweet
    "tweet_claro": dict(bg="#FFFFFF", cor="#0F0F10", sec="#7B7B7E", fam="inter", peso=430, tam=82, lh=1.2,
                        tr=-0.012, ml=0.085, mr=0.085, ass=None, dest="negrito", tweet=True, teto=0.64),
    "tweet_escuro": dict(bg="#000000", cor="#FFFFFF", sec="#8A8A8E", fam="inter", peso=430, tam=82, lh=1.2,
                         tr=-0.012, ml=0.085, mr=0.085, ass=None, dest="negrito", tweet=True, teto=0.64),
}

_cache = {}


def fonte(fam: str, peso: int, tam: int) -> ImageFont.FreeTypeFont:
    k = (fam, peso, tam)
    if k not in _cache:
        caminho = ROOT / FAMILIAS[fam]
        if not caminho.exists():
            raise RuntimeError(f"Fonte ausente: {caminho}. Rode o download das fontes (ver README).")
        f = ImageFont.truetype(str(caminho), tam)
        vals = []
        for ax in f.get_variation_axes():
            nome = ax["name"]
            if nome in (b"Weight", "Weight"):
                vals.append(max(ax["minimum"], min(ax["maximum"], peso)))
            else:  # optical size etc.: usa o máximo (versão "display")
                vals.append(ax["maximum"])
        f.set_variation_by_axes(vals)
        _cache[k] = f
    return _cache[k]


Palavra = Tuple[str, str]  # (texto, tipo)  tipo: n | r (destaque) | u (sublinhado)


def parse(texto: str) -> List[List[Palavra]]:
    paragrafos = []
    tipo = "n"
    for linha in texto.strip().split("\n"):
        palavras: List[Palavra] = []
        colar = False
        for pedaco in re.split(r"([*_])", linha):
            if pedaco == "*":
                tipo = "n" if tipo == "r" else "r"
                continue
            if pedaco == "_":
                tipo = "n" if tipo == "u" else "u"
                continue
            if not pedaco:
                continue
            tokens = pedaco.split()
            if not tokens:
                colar = False
                continue
            if colar and palavras and not pedaco[0].isspace():
                palavras[-1] = (palavras[-1][0] + tokens[0], palavras[-1][1])  # pontuação cola na palavra
                tokens = tokens[1:]
            for w in tokens:
                palavras.append((w, tipo))
            colar = not pedaco[-1].isspace()
        paragrafos.append(palavras)
    return paragrafos


def _spec(est: dict, tipo: str, cfg: dict, tam: int):
    """(fonte, cor, sublinhar) para um tipo de palavra neste estilo."""
    cor, fam, peso = est["cor"], est["fam"], est["peso"]
    vermelho = cfg["visual"]["cor_destaque"]
    dest = est["dest"]
    if tipo == "n" or dest == "nenhum":
        return fonte(fam, peso, tam), cor, False
    if dest == "vermelho":
        return fonte(fam, peso, tam), vermelho, False
    if dest == "escuro":  # destaque = um pouco mais forte e escuro
        return fonte(fam, 720, tam), "#1A1A1C", False
    if dest == "negrito":
        return fonte(fam, 760, tam), cor, False
    if dest == "leve":
        if tipo == "u":
            return fonte("mont_i", 800, tam), "#FFFFFF", True
        return fonte("mont", 800, tam), vermelho, False
    return fonte(fam, peso, tam), cor, False


def _largura(palavra: str, f, tr: float) -> float:
    return f.getlength(palavra) + tr * len(palavra)


def _quebrar(paragrafos, est, cfg, tam, larg_max, upper_first):
    tr = est["tr"] * tam
    base = fonte(est["fam"], est["peso"], tam)
    espaco = base.getlength(" ") + tr
    linhas, maior = [], 0.0
    for pi, par in enumerate(paragrafos):
        if not par:
            linhas.append(None)
            continue
        atual, w_atual = [], 0.0
        for palavra, tipo in par:
            if est.get("upper") or (upper_first and pi == 0):
                palavra = palavra.upper()
            f, cor, ul = _spec(est, tipo, cfg, tam)
            w = _largura(palavra, f, tr)
            extra = espaco if atual else 0
            if atual and w_atual + extra + w > larg_max:
                linhas.append(atual)
                maior = max(maior, w_atual)
                atual, w_atual, extra = [], 0.0, 0
            atual.append((palavra, f, cor, ul, w))
            w_atual += extra + w
        linhas.append(atual)
        maior = max(maior, w_atual)
    return linhas, maior, espaco


def _desenhar_palavra(d, x, y, texto, f, cor, tr):
    for i, ch in enumerate(texto):
        d.text((x, y), ch, font=f, fill=cor)
        if i + 1 < len(texto):
            x += f.getlength(ch + texto[i + 1]) - f.getlength(texto[i + 1]) + tr
        else:
            x += f.getlength(ch) + tr
    return x


def _avatar(perfil: dict, diametro: int) -> Image.Image:
    caminho = ROOT / perfil.get("avatar", "")
    if caminho.is_file():
        img = Image.open(caminho).convert("RGB").resize((diametro, diametro), Image.LANCZOS)
    else:
        img = Image.new("RGB", (diametro, diametro), "#2B2B2E")
        d = ImageDraw.Draw(img)
        ini = "".join(p[0] for p in perfil["nome"].split()[:2]).upper() or "?"
        f = fonte("mont", 800, int(diametro * 0.40))
        d.text(((diametro - f.getlength(ini)) / 2, diametro * 0.27), ini, font=f, fill="#FFFFFF")
    esc = 4
    mask = Image.new("L", (diametro * esc, diametro * esc), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diametro * esc - 1, diametro * esc - 1), fill=255)
    img.putalpha(mask.resize((diametro, diametro), Image.LANCZOS))
    return img


def _selo(d, cx, cy, r):
    pts = []
    for i in range(16):
        ang = math.pi * 2 * i / 16
        rr = r if i % 2 == 0 else r * 0.86
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    d.polygon(pts, fill="#1D9BF0")
    d.line([(cx - r * 0.4, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.32), (cx + r * 0.42, cy - r * 0.3)],
           fill="#FFFFFF", width=max(2, int(r * 0.2)), joint="curve")


def _grao(img: Image.Image, forca: float) -> Image.Image:
    """Granulado sutil de papel/filme."""
    ruido = Image.effect_noise(img.size, 38).convert("RGB")
    cinza = Image.new("RGB", img.size, (128, 128, 128))
    ruido = Image.blend(cinza, ruido, 1.0)
    return Image.blend(img, ImageChops.overlay(img, ruido), forca)


def estilo_valido(estilo: str, texto: str) -> str:
    """'regra' só serve para listas ('Título:' + linhas); senão cai para 'papel'."""
    if estilo == "regra":
        linhas = [l for l in texto.strip().split("\n") if l.strip()]
        if not (len(linhas) >= 3 and linhas[0].rstrip("* _").endswith(":")):
            return "papel"
    return estilo


def renderizar(texto: str, estilo: str, cfg: dict, saida: str) -> str:
    estilo = estilo_valido(estilo, texto)
    est = ESTILOS[estilo]
    W, H = cfg["visual"]["largura"], cfg["visual"]["altura"]
    perfil = cfg["perfil"]
    S = 2
    img = Image.new("RGB", (W * S, H * S), est["bg"])
    d = ImageDraw.Draw(img)

    ml, mr = int(est["ml"] * W * S), int(est["mr"] * W * S)
    larg_max = W * S - ml - mr
    tweet = est.get("tweet", False)
    paragrafos = parse(texto)
    upper_first = est.get("upper_first", False)

    cab_h = (150 + 60) * S if tweet else 0
    teto_h = est["teto"] * H * S

    tam = est["tam"] * S
    while True:
        linhas, maior, espaco = _quebrar(paragrafos, est, cfg, tam, larg_max, upper_first)
        entre = tam * est["lh"]
        altura = sum((entre * 0.55 if l is None else entre) for l in linhas)
        if (altura <= teto_h and maior <= larg_max + 1) or tam <= 26 * S:
            break
        tam -= 2 * S
    tr = est["tr"] * tam

    # bloco = [cabeçalho] + texto + [assinatura]
    handle_gap = 64 * S
    handle_h = 34 * S
    bloco = cab_h + altura
    if est["ass"] == "handle_abaixo":
        bloco += handle_gap + handle_h
    aspas_h = 190 * S if est.get("aspas") else 0
    bloco_total = bloco + aspas_h
    rodape = 150 * S if est["ass"] == "nome_centro" else 0
    y0 = (H * S - rodape - bloco_total) / 2 - H * S * 0.012
    y0 = max(y0, 60 * S)

    y = y0 + aspas_h
    # aspas de abertura
    if est.get("aspas"):
        fa = fonte("mont", 900, 230 * S)
        d.text((ml - 6 * S, y0 - 40 * S), "“", font=fa, fill=cfg["visual"]["cor_destaque"])

    # cabeçalho tweet
    if tweet:
        av = 150 * S
        a = _avatar(perfil, av)
        img.paste(a, (ml, int(y)), a)
        nx = ml + av + 34 * S
        fn = fonte("inter", 720, 52 * S)
        d.text((nx, y + 22 * S), perfil["nome"], font=fn, fill=est["cor"])
        if perfil.get("verificado"):
            _selo(d, nx + fn.getlength(perfil["nome"]) + 36 * S, y + 22 * S + 36 * S, 23 * S)
        d.text((nx, y + 22 * S + 70 * S), "@" + perfil["arroba"], font=fonte("inter", 400, 44 * S), fill=est["sec"])
        y += cab_h

    topo_texto = y
    for linha in linhas:
        if linha is None:
            y += entre * 0.55
            continue
        x = ml
        for i, (palavra, f, cor, ul, w) in enumerate(linha):
            _desenhar_palavra(d, x, y, palavra, f, cor, tr)
            if ul:
                asc, _ = f.getmetrics()
                ly = y + asc + tam * 0.07
                # estende o sublinhado pelo espaço até a próxima palavra sublinhada
                fim = x + w
                if i + 1 < len(linha) and linha[i + 1][3]:
                    fim += espaco
                d.rectangle((x, ly, fim, ly + max(3 * S, tam * 0.045)), fill=cfg["visual"]["cor_destaque"])
            x += w + espaco
        y += entre
    base_texto = y

    # aspas de fechamento
    if est.get("aspas"):
        fa = fonte("mont", 900, 230 * S)
        wq = fa.getlength("”")
        d.text((W * S - mr - wq + 6 * S, base_texto - 150 * S), "”", font=fa, fill=cfg["visual"]["cor_destaque"])

    # assinatura
    if est["ass"] == "handle_abaixo":
        d.text((ml, base_texto + handle_gap - 10 * S), "@" + perfil["arroba"],
               font=fonte("mont", 500, 34 * S), fill=est["sec"])
    elif est["ass"] == "nome_centro":
        f = fonte("mont", 700, 38 * S)
        n = "@" + perfil["arroba"]
        d.text(((W * S - f.getlength(n)) / 2, H * S - 190 * S), n, font=f, fill=est["sec"])

    img = img.resize((W, H), Image.LANCZOS)
    if est.get("grain"):
        img = _grao(img, est["grain"])
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    img.save(saida, "PNG", optimize=True)
    return saida
