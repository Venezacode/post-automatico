"""Publica imagens no Instagram pela API oficial (Instagram API com login do Instagram)."""
from __future__ import annotations

import os
import time

import requests

API = "https://graph.instagram.com/v21.0"


def publicar(image_url: str, legenda: str) -> str:
    token = os.environ["IG_ACCESS_TOKEN"]
    ig_id = os.environ["IG_USER_ID"]

    # 1) cria o container de mídia (o Instagram baixa a imagem da URL pública)
    ultimo_erro = None
    for tentativa in range(6):  # a URL raw do GitHub pode demorar alguns segundos
        r = requests.post(
            f"{API}/{ig_id}/media",
            data={"image_url": image_url, "caption": legenda, "access_token": token},
            timeout=60,
        )
        if r.ok:
            break
        ultimo_erro = r.text
        time.sleep(10)
    else:
        raise RuntimeError(f"Falha ao criar container: {ultimo_erro}")
    container = r.json()["id"]

    # 2) espera ficar pronto
    for _ in range(20):
        s = requests.get(f"{API}/{container}", params={"fields": "status_code", "access_token": token}, timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") == "ERROR":
            raise RuntimeError(f"Container com erro: {s}")
        time.sleep(3)

    # 3) publica
    r = requests.post(f"{API}/{ig_id}/media_publish", data={"creation_id": container, "access_token": token}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Falha ao publicar: {r.text}")
    return r.json()["id"]


def renovar_token() -> str:
    """Tokens duram 60 dias. Renove a cada ~30 dias e atualize o segredo IG_ACCESS_TOKEN."""
    r = requests.get(
        "https://graph.instagram.com/refresh_access_token",
        params={"grant_type": "ig_refresh_token", "access_token": os.environ["IG_ACCESS_TOKEN"]},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]
