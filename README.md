# Post Automático — cards de texto para Instagram

Gera posts tipográficos (estilo das suas referências) com frases escritas pela Claude e publica sozinho **3x por semana** (seg, qua, sex às 09h de Brasília).

## 1. Teste local (2 minutos)

```bash
cd post-automatico
.venv/bin/python main.py demo          # 4 exemplos em preview/
```

Edite `config.yaml`: nome, @, nicho, tom, pilares. Coloque sua foto em `assets/avatar.png`.
Para usar uma fonte mais parecida com as referências (Montserrat/Inter Bold), salve em `fonts/bold.ttf` e `fonts/regular.ttf`.

Frases com IA (precisa de chave em console.anthropic.com):

```bash
export ANTHROPIC_API_KEY="sua-chave"
.venv/bin/python main.py preview 3     # gera 3 posts + legendas em preview/
```

## 2. Instagram (API oficial)

1. A conta precisa ser **Profissional** (Criador ou Empresa).
2. Em developers.facebook.com crie um app → tipo **Business** → adicione o produto **Instagram** → "API setup with Instagram login".
3. Adicione sua conta como testador/usuário do app e gere o **token de acesso** (permissão `instagram_business_content_publish`) e anote o **Instagram User ID**.
4. Token dura 60 dias. Renove a cada ~30 dias: `IG_ACCESS_TOKEN=... python main.py renovar-token` e atualize o segredo no GitHub.

## 3. Automação (GitHub Actions, grátis, não precisa do Mac ligado)

1. Crie um repositório **público** no GitHub e suba esta pasta (o Instagram precisa baixar a imagem por URL pública).
2. Em Settings → Secrets → Actions, crie: `ANTHROPIC_API_KEY`, `IG_ACCESS_TOKEN`, `IG_USER_ID`.
3. Aba Actions → "Postar no Instagram" → **Run workflow** para testar na hora.
4. Depois disso roda sozinho seg/qua/sex. Para mudar horário ou dias, edite o `cron` em `.github/workflows/post.yml`.

Cada post fica registrado em `historico.json` (usado também para a IA não repetir frases).
