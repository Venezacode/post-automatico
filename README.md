# Post Automático — cards de texto para Instagram

Gera posts tipográficos (estilo das suas referências) com frases escritas pela Claude e publica sozinho **3x por semana** (seg, qua, sex às 09h de Brasília).

## 1. Teste local (2 minutos)

```bash
cd post-automatico
.venv/bin/python main.py demo          # 4 exemplos em preview/
```

Edite `config.yaml`: nome, @, nicho, tom, pilares. Coloque sua foto em `assets/avatar.png`.
Para usar uma fonte mais parecida com as referências (Montserrat/Inter Bold), salve em `fonts/bold.ttf` e `fonts/regular.ttf`.

Frases com IA. **Grátis:** chave do Gemini em aistudio.google.com/apikey (padrão no config.yaml). Pago, opcional: chave da Anthropic e `provedor: claude`.

```bash
export GEMINI_API_KEY="sua-chave"
.venv/bin/python main.py preview 3     # gera 3 posts + legendas em preview/
```

## 2. Agendar sem API (Plano B — Buffer, Later ou Metricool)

O comando `lote` gera as imagens, as legendas e um `agenda.csv` com os próximos seg/qua/sex às 09h:

```bash
.venv/bin/python main.py lote 3
```

No Buffer: Publishing → Bulk upload / Import CSV → envie `agenda.csv`
(colunas: Text, Image URL, Tags, Posting Time). As imagens são baixadas do GitHub público.
No Later/Metricool: importe o CSV ou envie as PNGs de `posts/` e cole as legendas.

**Automático na nuvem:** o workflow `Gerar lote da semana` roda todo domingo, gera os 3 posts da próxima semana e atualiza `agenda.csv` no repositório. Segredo necessário: `GEMINI_API_KEY` (ou `ANTHROPIC_API_KEY` se usar Claude).

## 3. Publicação direta pela API do Instagram (opcional, quando o Meta liberar)

Há um app criado no Meta (ID 1873467220528830), mas o Meta bloqueou a conexão do portfólio por verificação de segurança.
Quando liberar: conectar o portfólio, vincular o Instagram, gerar o token e cadastrar `IG_ACCESS_TOKEN` e `IG_USER_ID`
nos segredos. Depois, rode o workflow `Postar no Instagram` (`main.py criar` + `main.py publicar`).
