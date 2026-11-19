# Setup da chave do Google AI Studio (Gemini) — passo a passo

Você só precisa fazer **uma vez**. O login na sua conta Google é a única parte manual.

## 1. Pegar a chave (2 min)
1. Abra https://aistudio.google.com/apikey e entre com sua conta Google.
2. Clique em **Create API key** (escolha ou crie um projeto).
3. Copie a chave (começa com `AIza...`). **Não cole em chat, print ou no repositório.**

## 2. Instalar a chave e ligar a automação (1 comando)
No seu computador, com o [GitHub CLI](https://cli.github.com) instalado:

```bash
gh auth login        # só na primeira vez
./setup.sh           # pede a chave (sem mostrar), valida, grava o secret e dispara o 1º lote
```

O `setup.sh`:
1. valida a chave direto na API do Google;
2. grava como secret `GEMINI_API_KEY` no repositório (nunca vai para o código);
3. dispara o workflow **Gerar lote da semana** (depois roda sozinho todo domingo 09h BRT);
4. mostra o link do painel para revisar.

Sem `gh`? Manual: repositório → Settings → Secrets and variables → Actions → **New repository secret** → nome `GEMINI_API_KEY`.

## 3. Personalizar (referências, idioma, tom)
Tudo em `config.yaml`:
- `conteudo.idioma` — idioma das frases (ex.: "inglês", "espanhol").
- `conteudo.nicho`, `conteudo.tom`, `conteudo.pilares` — temas, autores de referência e estilo.
- `conteudo.evitar`, `conteudo.hashtags`, `conteudo.cta_legenda`.
- `visual.estilos` — quais layouts entram na rotação; `visual.cor_destaque`.
- `agenda.dias` / `agenda.hora` e `ia.modelos`.

Para testar localmente: `GEMINI_API_KEY=... python main.py preview 3`.
Sempre confira a fonte das citações antes de postar (a IA pode errar autoria).
