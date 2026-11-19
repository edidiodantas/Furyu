# IPeia Acadêmico: análise técnica e correções

- **Data:** 2026-11-19
- **Base analisada:** commit `0c51ac1` do `edidiodantas/paperqa-gui-local` (então "AcervoQA"), copiado para o `main` do `edidiodantas/Furyu`
- **Branch de correção:** `fix/revisao-rag-academico`
- **Escopo lido:** todos os 30 arquivos versionados (código, scripts, Docker, guias)

## Como ler este documento

Cada achado diz **o que foi conferido** (arquivo e linha do commit `0c51ac1`), o **impacto**, a **correção** e o **status**. Os itens marcados como *suposição* não foram comprovados por execução e estão sinalizados.

Ambientes de verificação:

1. **Container Linux, sem Ollama:** Python 3.13, `paper-qa 2026.8.12`, `streamlit 1.67.0`, `httpx 0.28.1`. Rodei os testes unitários, o lint e a tela via `streamlit.testing.AppTest`.
2. **PC do usuário (2026-11-19):** Linux, Python 3.12.15, Ollama 0.40.2, GTX 750 com 4 GB, modelo `llama3.2:3b`. O teste ponta a ponta passou:
   - um texto de teste foi indexado em 83,5 s, tempo que inclui o download do modelo de embedding;
   - duas perguntas foram respondidas corretamente, em português e com citação, em 49,6 s e 29,1 s;
   - depois de recriar o serviço a partir do disco, o acervo continuou lá, sem reindexar;
   - a tela subiu e o `/_stcore/health` respondeu `ok`;
   - o `ollama ps` mostrou 84% do modelo na GPU.

   Duas limitações apareceram:
   - Em arquivos `.txt`, o PaperQA2 não consegue extrair título, DOI e autores, então a referência sai com campos genéricos (`[Title of Container]`).
   - O modelo de 3B às vezes acrescenta uma frase contraditória à resposta.

## Resumo

| # | Gravidade | Achado | Status |
| --- | --- | --- | --- |
| 1 | Crítica | O acervo vivia só na sessão do navegador e era perdido ao recarregar | Corrigido |
| 2 | Crítica | O Docker quebrava: só o `app.py` era copiado para a imagem | Corrigido |
| 3 | Alta | E-mail recusado pelo Unpaywall derrubava a busca inteira; o `.env.example` trazia um e-mail falso | Corrigido |
| 4 | Alta | Upload com o mesmo nome sobrescrevia outro arquivo; falha de indexação era repetida a cada clique | Corrigido |
| 5 | Alta | Trocar `EMBEDDING_MODEL` corromperia as buscas sem aviso | Corrigido (novo controle) |
| 6 | Média | Um event loop novo a cada chamada, reaproveitando o mesmo `Docs` | Corrigido |
| 7 | Média | `ollama-deepin.sh` baixava os modelos numa pasta e o `rodar-deepin.sh` procurava em outra | Corrigido |
| 8 | Média | O regex do PID SciELO ignorava ISSN terminado em X | Corrigido |
| 9 | Média | O download sobrescrevia arquivo quando `_novo.pdf` já existia | Corrigido |
| 10 | Média | Ollama e Streamlit expostos na rede local (Docker em `0.0.0.0`) | Corrigido |
| 11 | Média | Só aceitava PDF; livros em TXT, MD ou HTML eram recusados | Corrigido |
| 12 | Média | As respostas tendiam a sair em inglês | Mitigado |
| 13 | Média | `app.py` monolítico (505 linhas: UI, configuração, regra e rede juntas) | Corrigido |
| 14 | Média | O único teste (`test_keys.py`) testava uma cópia da lógica, não o código real | Corrigido |
| 15 | Baixa | Checagem do Ollama a cada interação (até 3 s travando a tela) | Corrigido |
| 16 | Baixa | Modelo padrão diferente em três lugares (9b, 2b e 4b) | Corrigido |
| 17 | Baixa | Títulos externos renderizados como Markdown sem escape | Corrigido |
| 18 | Info | Dependências sem versão fixa | Pendente (recomendação) |
| 19 | Info | Falta exportar referências em ABNT/BibTeX | Pendente (requisito futuro) |
| 20 | Info | Sem suporte a EPUB | Pendente (requisito futuro) |

## Achados em detalhe

### 1. O acervo não persistia (crítica)

- **Conferido:** `app.py:152-153` cria `st.session_state.docs = Docs()`. Esse objeto, que guarda os embeddings, só existe na sessão do navegador. `indexed_files` (linha 155) também. O `IndexSettings(index_directory=...)` das linhas 107-111 só é usado pelo modo agente do PaperQA2 (`agent_query`), que o app não chama: ele usa `Docs.aadd` e `Docs.aquery`. O comentário da linha 9 ("o caminho certo é agent.index") dava a impressão de que havia persistência.
- **Impacto:** a cada recarga ou reinício, todos os livros e artigos tinham de ser reindexados. Com LLM local, isso leva minutos por arquivo. Para quem monta um acervo de pesquisa, inviabiliza o uso.
- **Correção:** `ipeia_academico/library.py` grava o `Docs` em `PQA_HOME/acervo/docs.pkl`, com escrita atômica, e mantém um `manifest.json` indexado pelo SHA-256 de cada arquivo. Salvar `Docs` com `pickle` é o método documentado no README do PaperQA2 (seção "Can I save or load?"). `research_service.py` só persiste depois que a indexação dá certo. O teste `tests/test_library_paperqa.py` confirma o ciclo salvar/carregar com o `Docs` real.
- **Risco novo e mitigação:** `pickle` executa código ao carregar. O índice só é lido de `PQA_HOME`, que é local, e o README alerta para nunca carregar um `docs.pkl` de terceiros. Se uma atualização do `paper-qa` deixar o arquivo ilegível, a tela oferece "Apagar índice e recomeçar".

### 2. Docker quebrado (crítica)

- **Conferido:** `Dockerfile:26` copia apenas `app.py` e `entrypoint.sh`. O `app.py` importa `academic_search` (linha 34) e lê `assets/fonts.css` (linha 215).
- **Impacto:** o container falharia na primeira execução, com `ModuleNotFoundError`. *Suposição de execução: não construí a imagem, porque o ambiente não tem Docker. A conclusão vem da leitura dos imports.*
- **Correção:** o Dockerfile agora copia `ipeia_academico/`, `assets/` e `.streamlit/`.

### 3. Unpaywall derrubava a busca (alta)

- **Conferido:** `academic_search.py:391-392` relança o `RuntimeError` do HTTP 422 dentro de `attach_unpaywall_pdfs`, chamado por `search_academic` (linha 432) depois que os resultados já tinham chegado. O `.env.example` trazia `CONTACT_EMAIL=pesquisa@suaescola.edu.br`, um placeholder que passa no teste `"@" in email`.
- **Impacto:** quem copiasse o exemplo sem editar podia ver a busca inteira falhar, mesmo com artigos encontrados. Não testei se o Unpaywall de fato recusa esse domínio. O código, porém, trata o 422 justamente como "e-mail recusado".
- **Correção:** `config.py` valida o e-mail e descarta placeholders conhecidos. `attach_unpaywall_pdfs` devolve um aviso em vez de lançar exceção. `search_academic` só lança `SearchError` se **todos** os catálogos falharem, e mostra os avisos dos que falharam. O `.env.example` agora vem com `CONTACT_EMAIL=` vazio.

### 4. Uploads: sobrescrita e repetição de erro (alta)

- **Conferido:** `app.py:316-320` grava em `PDF_DIR / f.name` sem checar se já existe. A deduplicação usa só o nome (linha 317). Se `run_async` falha (linhas 333-335), o nome não entra em `indexed_files`, e o Streamlit reenvia a lista de uploads a cada interação.
- **Impacto:** (a) dois artigos diferentes chamados `artigo.pdf` faziam o segundo apagar o primeiro; (b) um arquivo com defeito voltava a ser indexado, com chamadas ao LLM, a cada clique em qualquer botão.
- **Correção:** a deduplicação passou a ser por SHA-256 do conteúdo e o nome é único (`nome_2.pdf`). O arquivo é validado (extensão, tamanho e assinatura `%PDF`). Se a indexação falha, o arquivo é apagado e o hash vai para `failed_uploads` da sessão, sem novas tentativas automáticas.

### 5. Troca de modelo de embedding (alta)

- **Conferido:** não havia nenhum registro de qual `EMBEDDING_MODEL` gerou o índice.
- **Impacto:** com o índice agora persistente (item 1), trocar o modelo no `.env` misturaria vetores de espaços diferentes. A busca por similaridade passaria a devolver trechos errados sem nenhum erro visível. *Este risco nasceu da correção 1 e foi tratado junto com ela.*
- **Correção:** `meta.json` guarda o modelo usado. Se ele divergir do `.env`, o app avisa e oferece reindexar.

### 6. Event loop novo a cada chamada (média)

- **Conferido:** `app.py:172-181` roda cada corrotina com `asyncio.run` numa thread nova, reaproveitando o mesmo `Docs` entre loops diferentes.
- **Impacto:** *suposição, não reproduzida:* clientes HTTP assíncronos (LiteLLM/httpx) guardados dentro do `Docs` ficam presos ao loop que os criou e podem falhar com "Event loop is closed" na segunda chamada. Não reproduzi o erro porque não tenho Ollama aqui. A correção elimina a classe de problema.
- **Correção:** `async_runner.BackgroundLoop` mantém um único loop numa thread dedicada (`st.cache_resource`) e aceita timeout.

### 7. Scripts do Deepin apontando para pastas diferentes (média)

- **Conferido:** `scripts/ollama-deepin.sh:25` usa `OLLAMA_MODELS="/media/Edidio/8662-B4492/ollama-models"`. Já `rodar-deepin.sh:23` e `setup-deepin.sh` usam `$MNT/ollama-models`, e o pendrive dos guias é `8662-B449`, sem o "2" final.
- **Impacto:** o modelo era baixado numa pasta e o servidor iniciado pelo outro script procurava em outra.
- **Correção:** `ollama-deepin.sh` monta o volume e usa `$MNT/ollama-models`, como os demais scripts.

### 8. PID SciELO com ISSN terminado em X (média)

- **Conferido:** `academic_search.py:27` usa `S\d{4}-\d{4}\d{13}`, mas o ISSN pode terminar em `X` (ex.: `0102-311X`).
- **Impacto:** artigos de periódicos com ISSN terminado em X não tinham o PDF SciELO resolvido nem o ano extraído.
- **Correção:** o regex passou a ser `S\d{4}-\d{3}[\dX]\d{13}`, com teste.

### 9. Download sobrescrevia arquivo (média)

- **Conferido:** `academic_search.py:471-472`: se `nome.pdf` existe, o download grava `nome_novo.pdf`. Se esse também já existir, ele é sobrescrito.
- **Correção:** os nomes ficam únicos (`nome_2`, `nome_3`, ...). O esquema da URL é validado e só aceita `http` ou `https`. Um PDF baixado cujo conteúdo já está no acervo é descartado.

### 10. Serviços expostos na rede (média, segurança)

- **Conferido:** `docker-compose.yml` publica `11434:11434` e `8501:8501`, o que no Docker significa todas as interfaces. O Ollama não tem autenticação.
- **Impacto:** qualquer máquina da mesma rede (Wi-Fi da escola, por exemplo) poderia usar o modelo e ver o acervo pela interface.
- **Correção:** as portas ficam presas a `127.0.0.1` e o `.streamlit/config.toml` usa `address = "127.0.0.1"` na execução nativa.

### 11. Só PDF (média)

- **Conferido:** `app.py:309` usa `type=["pdf"]`. O leitor do PaperQA2 (`paperqa/readers.py` da versão instalada) aceita `.txt` e `.html`, e outras extensões caem no leitor de texto genérico. O README do PaperQA2 cita `.pdf, .txt, .md, .html, .docx, .xlsx, .pptx`.
- **Correção:** o app aceita PDF, TXT, MD e HTML. DOCX ficou de fora porque exige o extra `office`, que não está no `requirements.txt`.

### 12. Respostas em inglês (média)

- **Conferido:** os prompts internos do PaperQA2 são em inglês e o app não pedia outro idioma.
- **Mitigação:** `build_question` acrescenta "(Responda em português do Brasil.)", valor configurável em `ANSWER_LANGUAGE`. *Não testei o efeito com o modelo `qwen3.5`. Modelos pequenos podem ignorar a instrução.* Uma solução mais forte seria customizar `settings.prompts.qa`, que deixei como próximo passo.

### 13. Arquitetura monolítica (média)

- **Conferido:** `app.py` tinha 505 linhas misturando configuração, montagem do PaperQA2, rede (checagem do Ollama), regra de indexação e UI. `academic_search.py` tinha 491 linhas.
- **Correção:** o código foi dividido em camadas:
  - entrada: `app.py`, só tela;
  - regra: `research_service.py`;
  - dados: `library.py`;
  - integrações: `search/`, `ollama_health.py` e `llm_settings.py`;
  - utilitários: `export.py`, `ui_helpers.py` e `async_runner.py`.

  As dependências são injetadas (cliente HTTP, `fetch`, `Docs`, relógio) e não há import circular.

### 14. Teste que não testava (média)

- **Conferido:** `test_keys.py` redefine `make_key` com a mesma expressão do `app.py` e testa essa cópia. Uma mudança no app não quebraria o teste.
- **Correção:** a função foi extraída (`ui_helpers.hit_button_key`) e passou a ser testada diretamente. Agora são 126 testes `pytest`, sem rede.

### 15 a 17. Itens menores

- **15:** `ollama_status()` era chamado em todo rerun (`app.py:200`), com timeout de 3 s. Agora fica em cache por 30 s.
- **16:** o padrão era `qwen3.5:9b` no código, `qwen3.5:2b` no `.env.example` e `qwen3.5:4b` no Docker. Ficou `qwen3.5:4b` em todos, que é o modelo recomendado pelos próprios guias. *Não verifiquei se a tag existe no registro do Ollama; mantive o nome usado pelo projeto.*
- **17:** títulos e autores vindos das APIs entravam direto no `st.markdown`. Agora são escapados. O Streamlit não renderiza HTML sem `unsafe_allow_html`, então o risco era de formatação e de links enganosos, não de XSS.

## Pendências (não corrigidas)

1. **Versões fixas:** o `requirements.txt` não fixa versões (`paper-qa[local,pymupdf]>=5`). Uma versão nova do PaperQA2 pode mudar a API de `Settings` ou o formato do `docs.pkl`. Recomendo, depois de validar no seu PC com o Ollama, gerar um `requirements.lock` com `pip freeze`.
2. **Metadados de arquivos sem cabeçalho bibliográfico:** em TXT/MD e em livros, a citação inferida pode sair genérica. Falta permitir que o usuário informe título, autores e ano no envio (o `Docs.aadd` aceita `citation`, `title`, `doi` e `authors`).
3. **Referências em ABNT/BibTeX:** o PaperQA2 gera citações em formato livre. Para escrever artigos, falta uma exportação ABNT (RF-12 do documento de requisitos).
4. **EPUB:** não é suportado pelo PaperQA2 nesta versão. Hoje, converta antes com o Calibre (`ebook-convert livro.epub livro.txt`).
5. **Remover um documento do acervo:** o `Docs` tem `delete`, mas não implementei na tela. Hoje só dá para apagar o índice inteiro.
6. **Licença:** o repositório não tem um arquivo `LICENSE`. O PaperQA2 é Apache 2.0, o que permite uso e modificação, mantendo o aviso.

## Como verificar

```bash
pip install -r requirements-dev.txt
python -m pytest        # 126 testes
ruff check .            # lint
```
