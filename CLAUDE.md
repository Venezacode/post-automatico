# Contexto do projeto (leia primeiro)

Ferramenta de **posts de texto para Instagram** (cards tipográficos 4:5) com **citações de filosofia, estoicismo, introspecção, estratégia e história** (Marco Aurélio, Sêneca, Epicteto, Dostoiévski, Nietzsche, Sun Tzu etc.), sempre com **autor** no card (“frase” + “— Autor”) do perfil **@eu.nohan** (Nohan Ventura, selo verificado, foto em `assets/avatar.png` recortada do print do perfil). Meta: **3 posts por semana (seg, qua, sex, 09:00 Brasília)**, gerados na nuvem, com **notificação para o Gabriel revisar/editar antes de publicar**. Funciona de qualquer dispositivo; nada depende do Mac dele.

Este repositório é **público** (precisa ser, para o Instagram/Buffer baixarem as imagens por URL). **Nunca coloque chaves, tokens ou dados pessoais aqui.** Segredos ficam em GitHub → Settings → Secrets → Actions.

## Preferências do Gabriel (respeitar)
- Falar em **português do Brasil**, direto, sem enrolação. Ele pede "faça por mim" e só quer cuidar de logins/senhas.
- Design: **copiar as referências** (ver "Design"). Os estilos tipo **perfil/tweet (foto + nome + selo + @) ele aprovou: não mudar**.
- Sempre mostrar **@eu.nohan** no rodapé dos cards (nunca só o nome). Nos estilos tweet o cabeçalho com nome + @ é o esperado.
- Ele quer ser **notificado** para revisar e editar antes de publicar.

## Regra de ouro: citações verificáveis
Frases atribuídas a figuras históricas são muitas vezes apócrifas (ex.: a de Alexandre, o Grande, "não conquistei a metade do mundo…"; várias de Dostoiévski/Sun Tzu). A IA é instruída a só usar citações de autoria estabelecida e a preencher `obra` e `confianca` (alta/media/baixa) em cada post; isso é salvo em `historico.json` e aparece no painel. **O IA não consegue verificar fontes: sempre conferir a citação antes de postar**, principalmente as com confiança diferente de "alta". Na dúvida, descartar.

## Como funciona
```
domingo 09:00 BRT -> GitHub Actions (.github/workflows/lote.yml)
   main.py lote 3  -> writer.py (IA gera frases+legendas) -> render.py (PNG) -> posts/*.png
                   -> historico.json + agenda.csv (commit no repositório)
   cria issue "Revisar posts da semana" (notificação) -> painel web (docs/index.html, GitHub Pages)
```
- Painel: https://venezacode.github.io/post-automatico/ (lê `historico.json` do repositório; botões copiar legenda / baixar imagem / compartilhar).
- Para mudar um post: editar o texto em `historico.json` e re-renderizar (ver Comandos) ou pedir ao Claude.

## Frases (fila escrita pelo Claude)
As frases vêm de `fila.json` (escritas pelo Claude em sessão, com `obra` e `confianca`). `main.py lote` consome a fila primeiro e só chama IA (Gemini/Claude via API) se a fila acabar e houver chave. Para reabastecer: peça "escreva mais N frases na fila" numa sessão do Claude. Referências do tema: Napoleon Hill, Sun Tzu, Alexandre, Júlio César, Maquiavel, estoicos. Frases virais de autoria duvidosa (ex.: Alexandre "não conquistei a metade do mundo…") ficam fora. Imagens de fundo por IA: **não** usadas (visual dos cards inalterado); a chave Gemini testada tem limite 0 para geração de imagem no plano grátis.

## Arquivos
- `config.yaml` — perfil, nicho/tom/pilares, estilos, dias/hora, IA (`ia.provedor`: `gemini` padrão grátis ou `claude`; `ia.modelos` lista de reserva).
- `writer.py` — prompt e chamada da IA (Gemini via REST com retentativas e fallback de modelos; ou Anthropic). Marcação: `*destaque*` (1 por post) e `_ênfase_` (opcional).
- `render.py` — renderizador (Pillow). Fontes variáveis em `fonts/` (Montserrat, Inter; licença OFL). Estilos em `ESTILOS`.
- `main.py` — comandos (abaixo). `publisher.py` — publicação via API do Instagram (hoje **não usado**, ver Status).
- `docs/index.html` — painel (GitHub Pages, pasta `/docs` da branch `main`).
- `.github/workflows/`: `lote.yml` (gera lote semanal + issue de aviso), `post.yml` (publicar via API, só manual), `modelos.yml` (lista modelos Gemini disponíveis).

## Comandos (Python 3.9+; `pip install -r requirements.txt`)
```
python main.py demo            # 8 exemplos em preview/ (sem IA)
python main.py preview N       # N posts com IA em preview/ (sem salvar)
python main.py lote N          # N posts + agenda.csv nos próximos dias de postagem
PA_DEMO=1 python main.py lote 3   # testa sem IA
```
Re-renderizar um post editado: ler `historico.json`, chamar `render.renderizar(texto, estilo, cfg, arquivo)`.
Segredos esperados no GitHub: `GEMINI_API_KEY` (ou `ANTHROPIC_API_KEY` se `provedor: claude`), opcional `NTFY_TOPIC`; para API do Instagram (futuro): `IG_ACCESS_TOKEN`, `IG_USER_ID`.

## Design (copia das referências)
8 estilos, em rotação (`visual.estilos`): `papel` (off-white, extra-bold apertado, @ centralizado embaixo), `branco_vermelho` (bold preto + frase vermelha, @ pequeno abaixo), `caixa_alta` (preto, CAIXA ALTA, aspas vermelhas), `escuro_leve` (escuro granulado, texto leve, negrito itálico sublinhado + vermelho), `semibold_cinza`, `regra` (lista "REGRA DE X:" em marrom; só para listas), `tweet_claro`, `tweet_escuro` (cabeçalho com foto `assets/avatar.png`, nome, selo, @). Listas "Título:" + linhas usam sempre `regra`. A fonte original das referências deve ser Gilroy (paga); usamos Montserrat como equivalente livre.

## Status e bloqueios (atualizar sempre)
- **Publicação 100% automática NÃO funciona.** App Meta criado (ID 1873467220528830, nome com erro "Post Automatico esta"), mas a conexão ao portfólio "BM 01" trava em "Verificação necessária" (exige confirmar identidade via Google, que precisa de pop-up; no navegador embutido do app não abre). Tentativa no Chrome normal do Gabriel **não deu certo** (motivo não detalhado).
- **Buffer** está conectado ao Instagram (@gabrielvenezaa), mas **não tem importação de CSV**; hoje o agendamento é manual pelo painel.
- **Caminho em andamento:** Make.com (webhook chamado pelo GitHub) -> módulo do Buffer cria **rascunho** com imagem+legenda; Gabriel aprova no app do Buffer. Ainda não configurado; falta o Gabriel entrar/criar conta no Make e autorizar o Buffer. Verificar se o plano grátis do Buffer aceita rascunho com imagem via integração.
- **Pendências de segurança:** excluir e recriar a chave do Gemini (apareceu em print) e atualizar o segredo `GEMINI_API_KEY`.
- Possíveis melhorias: fechar issues de revisão antigas ao criar nova; notificação por ntfy; editar texto direto no painel; mais estilos; ajustar título de lista que não é lista para tweet.

## Como retomar de qualquer lugar
Abra uma sessão do Claude (app, claude.ai/code ou terminal) apontada para o repositório `Venezacode/post-automatico` no GitHub e peça, por exemplo: "gera 6 posts", "troque o texto do post 2", "mude o tom", "continue a integração com Make/Buffer". Qualquer conta do Claude serve, desde que tenha acesso ao repositório.
