"""Uso:
  python main.py demo             # renderiza frases de exemplo (sem IA, sem Instagram)
  python main.py preview [N]      # gera N posts com IA em preview/ (não salva histórico)
  python main.py criar [N]        # gera N posts, salva em posts/ e marca como pendentes
  python main.py publicar         # publica os pendentes no Instagram
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
    ("claro", "Quem tem medo\nde investir em\nmarketing continuará pagando\no *preço de não vender.*"),
    ("escuro", "REGRA DE MARKETING:\n\nConteúdo atrai.\nRepetição faz lembrar.\nBastidor aproxima.\nOpinião posiciona.\nHistória conecta.\n*Postar todo dia vende.*"),
    ("tweet_claro", "Porrada de marketing:\n\nSeu produto pode ser o melhor do mercado.\n\nSe a comunicação for *genérica,* ele vai competir como se fosse igual a todos os outros."),
    ("tweet_escuro", "Oportunidades não surgem do nada. É *você quem as cria.*"),
]


def carregar_cfg() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def carregar_hist() -> list:
    return json.loads(HIST.read_text(encoding="utf-8")) if HIST.exists() else []


def salvar_hist(h: list) -> None:
    HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")


def proximo_estilo(cfg: dict, n_existentes: int) -> str:
    est = cfg["visual"]["estilos"]
    return est[n_existentes % len(est)]


def cmd_demo(cfg):
    from render import renderizar
    for i, (estilo, texto) in enumerate(DEMO, 1):
        print("→", renderizar(texto, estilo, cfg, str(ROOT / "preview" / f"demo-{i}-{estilo}.png")))


def cmd_preview(cfg, n):
    from render import renderizar
    from writer import gerar
    hist = carregar_hist()
    for i, p in enumerate(gerar(cfg, n, [h["texto"] for h in hist]), 1):
        estilo = proximo_estilo(cfg, len(hist) + i - 1)
        arq = renderizar(p["texto"], estilo, cfg, str(ROOT / "preview" / f"preview-{i}-{estilo}.png"))
        print(f"→ {arq}\n{p['texto']}\n---\n{p['legenda']}\n")


def cmd_criar(cfg, n):
    from render import renderizar
    from writer import gerar
    hist = carregar_hist()
    for p in gerar(cfg, n, [h["texto"] for h in hist]):
        estilo = proximo_estilo(cfg, len(hist))
        nome = f"{datetime.now():%Y-%m-%d-%H%M%S}-{len(hist)+1}.png"
        renderizar(p["texto"], estilo, cfg, str(ROOT / "posts" / nome))
        hist.append({"texto": p["texto"], "legenda": p["legenda"], "estilo": estilo,
                     "arquivo": f"posts/{nome}", "status": "pendente", "criado": datetime.now().isoformat()})
        print("criado:", nome)
    salvar_hist(hist)


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
    elif cmd == "publicar": cmd_publicar(cfg)
    elif cmd == "renovar-token":
        from publisher import renovar_token
        print(renovar_token())
    else: print(__doc__)


if __name__ == "__main__":
    main()
