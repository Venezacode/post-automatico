"""Uso:
  python main.py demo             # renderiza frases de exemplo (sem IA, sem Instagram)
  python main.py preview [N]      # gera N posts com IA em preview/ (não salva histórico)
  python main.py criar [N]        # gera N posts, salva em posts/ e marca como pendentes
  python main.py lote [N]         # gera N posts + agenda.csv (Buffer/Later/Metricool) nos próximos seg/qua/sex
  python main.py publicar         # publica os pendentes no Instagram (API oficial, opcional)
  python main.py renovar-token    # imprime um novo token de 60 dias
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
HIST = ROOT / "historico.json"

DEMO = [
    ("papel", "Quem tem medo\nde investir em\nmarketing continuará pagando\no preço de não vender."),
    ("branco_vermelho", "Toda empresa grande já foi\n*uma ideia que alguém achou ridícula.*"),
    ("caixa_alta", "Seu cérebro acredita na história que você repete todos os dias. Então escolha uma história poderosa."),
    ("escuro_leve", "Você nunca vai\n_se sentir pronto,_\nporque estar pronto\nnão é um sentimento,\n*é uma decisão.*"),
    ("semibold_cinza", "O sucesso na vida também é medido pela quantidade de conversas difíceis que você está disposto a ter."),
    ("regra", "REGRA DE MARKETING:\n\nConteúdo atrai.\nRepetição faz lembrar.\nBastidor aproxima.\nOpinião posiciona.\nHistória conecta.\nPostar todo dia vende."),
    ("tweet_claro", "Porrada de marketing:\n\nSeu produto pode ser o melhor do mercado.\n\nSe a comunicação for genérica, ele vai competir como se fosse igual a todos os outros."),
    ("tweet_escuro", "Oportunidades não surgem do nada. É *você quem as cria.*"),
]


def carregar_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def carregar_hist() -> list:
    return json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else []


def salvar_hist(h: list) -> None:
    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def proximo_estilo(cfg: dict, n_existentes: int, texto: str = "") -> str:
    from render import estilo_valido
    est = cfg["visual"]["estilos"]
    linhas = [l for l in texto.strip().split("\n") if l.strip()]
    if len(linhas) >= 3 and linhas[0].rstrip("* _").endswith(":") and "regra" in est:
        return "regra"  # listas "Regra de X:" sempre no estilo de lista
    e = est[n_existentes % len(est)]
    if e == "regra":  # sem lista, não usa o estilo de lista
        e = est[(n_existentes + 1) % len(est)]
    return estilo_valido(e, texto)


def cmd_demo(cfg):
    from render import renderizar
    for i, (estilo, texto) in enumerate(DEMO, 1):
        print("→", renderizar(texto, estilo, cfg, str(ROOT / "preview" / f"demo-{i}-{estilo}.png")))


def cmd_preview(cfg, n):
    from render import renderizar
    from writer import gerar
    hist = carregar_hist()
    for i, p in enumerate(gerar(cfg, n, [h["texto"] for h in hist]), 1):
        estilo = proximo_estilo(cfg, len(hist) + i - 1, p["texto"])
        arq = renderizar(p["texto"], estilo, cfg, str(ROOT / "preview" / f"preview-{i}-{estilo}.png"))
        print(f"→ {arq}\n{p['texto']}\n---\n{p['legenda']}\n")


def cmd_criar(cfg, n):
    from render import renderizar
    from writer import gerar
    hist = carregar_hist()
    for p in gerar(cfg, n, [h["texto"] for h in hist]):
        estilo = proximo_estilo(cfg, len(hist), p["texto"])
        nome = f"{datetime.now():%Y-%m-%d-%H%M%S}-{len(hist)+1}.png"
        renderizar(p["texto"], estilo, cfg, str(ROOT / "posts" / nome))
        hist.append({"texto": p["texto"], "legenda": p["legenda"], "estilo": estilo,
                     "arquivo": f"posts/{nome}", "status": "pendente", "criado": datetime.now().isoformat()})
        print("criado:", nome)
    salvar_hist(hist)


DIAS = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6}


def proximos_horarios(cfg: dict, n: int, apos=None) -> list:
    """Próximos N horários de postagem (dias e hora definidos em config.yaml -> agenda)."""
    from datetime import timedelta
    ag = cfg["agenda"]
    dias = sorted(DIAS[d] for d in ag["dias"])
    hh, mm = map(int, ag.get("hora", "09:00").split(":"))
    ref = apos or datetime.now()
    d = ref.replace(hour=hh, minute=mm, second=0, microsecond=0)
    saida = []
    while len(saida) < n:
        if d > ref and d.weekday() in dias:
            saida.append(d)
        d += timedelta(days=1)
    return saida


def cmd_lote(cfg, n):
    import csv
    from render import renderizar
    hist = carregar_hist()
    if os.environ.get("PA_DEMO"):  # teste sem IA
        posts = [{"texto": t, "legenda": f"Legenda de teste {i}\n\n#marketing"} for i, (_, t) in enumerate(DEMO[:n], 1)]
    else:
        from writer import gerar
        posts = gerar(cfg, n, [h["texto"] for h in hist])
    base = os.environ.get("IMAGE_BASE_URL", cfg.get("repositorio_url_raw", "")).rstrip("/")
    ultimo = None
    pend = [datetime.fromisoformat(h["agendado"]) for h in hist if h.get("agendado")]
    if pend:
        ultimo = max(pend)
    horarios = proximos_horarios(cfg, len(posts), ultimo if ultimo and ultimo > datetime.now() else None)
    linhas = []
    for p, quando in zip(posts, horarios):
        estilo = proximo_estilo(cfg, len(hist), p["texto"])
        nome = f"{quando:%Y-%m-%d}-{len(hist)+1}.png"
        renderizar(p["texto"], estilo, cfg, str(ROOT / "posts" / nome))
        hist.append({"texto": p["texto"], "legenda": p["legenda"], "estilo": estilo, "arquivo": f"posts/{nome}",
                     "status": "agendado-externo", "agendado": quando.isoformat(), "criado": datetime.now().isoformat()})
        linhas.append([p["legenda"], f"{base}/posts/{nome}", "", f"{quando:%Y-%m-%d %H:%M}"])
        print(f"{quando:%a %d/%m %H:%M}  {nome}")
    arq = ROOT / "agenda.csv"
    novo = not arq.exists()
    with arq.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if novo:
            w.writerow(["Text", "Image URL", "Tags", "Posting Time"])
        w.writerows(linhas)
    salvar_hist(hist)
    print("agenda:", arq)


def cmd_publicar(cfg):
    from publisher import publicar
    base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
    if not base:
        sys.exit("Defina IMAGE_BASE_URL (URL pública da pasta do repositório, ver README).")
    hist = carregar_hist()
    pend = [h for h in hist if h["status"] == "pendente"]
    if not pend:
        print("Nada pendente.")
    for h in pend:
        h["ig_media_id"] = publicar(f"{base}/{h['arquivo']}", h["legenda"])
        h["status"] = "publicado"
        h["publicado"] = datetime.now().isoformat()
        print("publicado:", h["arquivo"], h["ig_media_id"])
        salvar_hist(hist)


def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    cmd, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1
    cfg = carregar_cfg()
    if cmd == "demo": cmd_demo(cfg)
    elif cmd == "preview": cmd_preview(cfg, n)
    elif cmd == "criar": cmd_criar(cfg, n)
    elif cmd == "lote": cmd_lote(cfg, n)
    elif cmd == "publicar": cmd_publicar(cfg)
    elif cmd == "renovar-token":
        from publisher import renovar_token
        print(renovar_token())
    else: print(__doc__)


if __name__ == "__main__":
    main()
