# IPeia Acadêmico: especificação de requisitos

| Campo | Valor |
| --- | --- |
| Versão do documento | 1.0 |
| Data | 2026-11-19 |
| Produto | IPeia Acadêmico (antes "AcervoQA"), versão 0.2.0 |
| Repositório | `edidiodantas/Furyu` |
| Responsável | Edídio (usuário e mantenedor) |
| Situação | Rascunho para revisão |

Legenda de status:
- **Implementado:** existe no código do branch `fix/revisao-rag-academico` e tem teste automatizado ou verificação na tela.
- **Parcial:** existe, mas com limitação conhecida.
- **Proposto:** ainda não existe.

## 1. Visão geral

### 1.1 Objetivo

Ajudar uma pessoa pesquisadora a **pesquisar, ler e escrever textos acadêmicos** com base em artigos científicos e livros. O sistema monta um acervo local, responde perguntas citando os documentos e oferece trechos e referências para a escrita. Tudo roda no computador da pessoa, com LLM local (Ollama), sem custo de API e sem enviar os documentos para serviços de IA externos.

### 1.2 Escopo

**Dentro do escopo:** acervo pessoal persistente, busca de artigos em acesso aberto, perguntas e respostas com citações (RAG), exportação das respostas, instalação em Windows 11 e Linux (Deepin/Ubuntu), Docker opcional.

**Fora do escopo:** uso multiusuário ou em servidor público, download de conteúdo com paywall, geração automática de artigos completos, sincronização em nuvem.

### 1.3 Usuário

| Perfil | Descrição |
| --- | --- |
| Pesquisador individual | Professor ou pesquisador que escreve textos e artigos. Usa o sistema sozinho, no próprio PC. Tem conhecimento básico de terminal para instalar. |

### 1.4 Glossário

| Termo | Significado |
| --- | --- |
| Acervo | Conjunto de documentos indexados pelo usuário, salvo em disco |
| Indexar | Extrair texto, dividir em trechos, gerar embeddings e inferir a citação do documento |
| RAG | *Retrieval-Augmented Generation*: o LLM responde com base em trechos recuperados do acervo |
| Embedding | Vetor numérico que representa o sentido de um trecho, usado na busca por similaridade |
| PaperQA2 | Biblioteca de RAG científico (FutureHouse, Apache 2.0) usada como motor |
| Ollama | Servidor local que roda o LLM |

## 2. Requisitos funcionais

### 2.1 Acervo

| ID | Requisito | Prioridade | Status |
| --- | --- | --- | --- |
| RF-01 | Enviar um ou mais documentos pela tela nos formatos PDF, TXT, MD e HTML | Alta | Implementado |
| RF-02 | Validar cada arquivo antes de indexar: extensão permitida, tamanho até 200 MB e assinatura `%PDF` nos PDFs | Alta | Implementado |
| RF-03 | Salvar o arquivo em `PDF_DIR` sem sobrescrever outro de mesmo nome (`nome_2.pdf`) | Alta | Implementado |
| RF-04 | Ignorar um documento cujo conteúdo (SHA-256) já está no acervo | Alta | Implementado |
| RF-05 | Persistir o índice em disco, para que ele sobreviva a recarregar a página e a reiniciar o app ou o PC | Alta | Implementado |
| RF-06 | Listar os documentos do acervo, com nome do arquivo e citação inferida | Média | Implementado |
| RF-07 | Apagar o índice inteiro, com confirmação, mantendo os arquivos | Média | Implementado |
| RF-08 | Remover um documento específico do acervo | Média | Proposto |
| RF-09 | Aceitar livros em EPUB e DOCX | Média | Proposto (EPUB não é lido pelo PaperQA2; DOCX exige o extra `office`) |
| RF-10 | Indexar em lote todos os arquivos de uma pasta já existente | Média | Proposto |

### 2.2 Busca de artigos

| ID | Requisito | Prioridade | Status |
| --- | --- | --- | --- |
| RF-11 | Buscar por tema ou título no Oasisbr (IBICT) e, se não houver resultado, no Semantic Scholar e depois no Crossref | Alta | Implementado |
| RF-12 | Mostrar título, ano, autores, periódico, DOI, resumo e se há PDF aberto | Alta | Implementado |
| RF-13 | Encontrar PDF em acesso aberto pelo Unpaywall (com `CONTACT_EMAIL` válido) e pelo PID do SciELO | Alta | Implementado |
| RF-14 | Baixar o PDF aberto e indexá-lo com um clique, com limite de 40 MB e checagem `%PDF` | Alta | Implementado |
| RF-15 | Continuar a busca e mostrar um aviso quando um catálogo ou o Unpaywall falhar | Alta | Implementado |
| RF-16 | Não baixar conteúdo com paywall | Alta | Implementado (só usa links de acesso aberto) |
| RF-17 | Filtrar a busca por ano, tipo (artigo, tese, livro) e idioma | Baixa | Proposto |

### 2.3 Perguntas e respostas

| ID | Requisito | Prioridade | Status |
| --- | --- | --- | --- |
| RF-18 | Responder perguntas usando apenas o acervo, com citações dos documentos | Alta | Implementado (motor PaperQA2) |
| RF-19 | Validar a pergunta: de 3 a 2.000 caracteres e acervo não vazio | Alta | Implementado |
| RF-20 | Responder no idioma configurado (`ANSWER_LANGUAGE`, padrão português do Brasil) | Alta | Parcial (instrução no fim da pergunta; modelos pequenos podem ignorar) |
| RF-21 | Mostrar os trechos usados como fonte, com documento de origem e relevância | Alta | Implementado |
| RF-22 | Baixar a resposta em Markdown, com pergunta, resposta, referências, data e modelo | Alta | Implementado |
| RF-23 | Exportar as referências em ABNT (NBR 6023) e BibTeX | Alta | Parcial: ABNT implementado (RF-37); BibTeX proposto |
| RF-24 | Guardar o histórico de perguntas e respostas | Média | Proposto |
| RF-25 | Modos de escrita: resumo de um documento, revisão de literatura sobre um tema e comparação entre autores | Média | Parcial: resumo e texto por seções implementados (RF-34); comparação entre autores proposta |

### 2.4 Operação

| ID | Requisito | Prioridade | Status |
| --- | --- | --- | --- |
| RF-26 | Mostrar se o Ollama está no ar e se o modelo configurado está instalado, com a instrução de correção | Alta | Implementado |
| RF-27 | Desabilitar indexação e perguntas quando o Ollama não estiver pronto | Alta | Implementado |
| RF-28 | Detectar troca de `EMBEDDING_MODEL` e oferecer reindexar | Alta | Implementado |
| RF-29 | Oferecer "Apagar índice e recomeçar" quando o índice estiver ilegível | Média | Implementado |
| RF-30 | **Trocar o motor de IA só pelo `.env`** (`LLM_PROVIDER` + `LLM_MODEL`): Ollama, servidor compatível com OpenAI, OpenAI, Anthropic, Gemini e OpenRouter | **Obrigatória** | Implementado (testado com Ollama; provedores na nuvem só por testes de configuração) |
| RF-31 | Modelo de resumo separado (`SUMMARY_LLM_MODEL`) e embedding configurável, incluindo `ollama/...` | Média | Implementado |
| RF-32 | Ajustar o tamanho da resposta e a quantidade de trechos e fontes (`ANSWER_LENGTH`, `EVIDENCE_K`, `ANSWER_MAX_SOURCES`) | Média | Implementado |
| RF-33 | Mostrar se a IA configurada está pronta: Ollama consultado; na nuvem, conferência da chave sem gerar custo | Alta | Implementado |
| RF-34 | Três modos de uso: Pergunta, Resumo de documento (busca restrita ao documento) e Texto acadêmico (uma busca por seção) | Alta | Implementado (falta teste real com IA) |
| RF-35 | Instruções à IA em português acadêmico: norma culta, linguagem impessoal, sem inventar dados | Alta | Implementado |
| RF-36 | Informar os dados bibliográficos de cada documento (livro, artigo, documento on-line); preencher a partir do catálogo nos PDFs baixados | Alta | Implementado |
| RF-37 | Citações no texto no padrão NBR 10520:2023, como (Silva, 2020, p. 15), com opção de caixa alta (`CITATION_UPPERCASE`), e lista de REFERÊNCIAS em ordem alfabética montada pelo código | Alta | Implementado (formato das referências NBR 6023 não conferido no texto oficial) |

## 3. Requisitos não funcionais

| ID | Categoria | Requisito | Status |
| --- | --- | --- | --- |
| RNF-01 | Privacidade | No modo local (padrão), documentos, embeddings e LLM ficam na máquina. Com um provedor na nuvem, a tela avisa que trechos e perguntas são enviados a ele | Implementado |
| RNF-02 | Custo e portabilidade | Os quatro papéis de LLM do PaperQA2 seguem o provedor escolhido, e nenhum cai na OpenAI por omissão (garantido por teste). Custo zero no modo local | Implementado |
| RNF-17 | Arquitetura | Motor de IA desacoplado (adaptador por provedor, em `providers.py`). Obrigatório em todos os projetos IPeia (arquitetura híbrida RAG/CAG) | Implementado |
| RNF-18 | Identidade visual | Logo oficial IPeia no cabeçalho, no favicon e no README (obrigatória em todos os projetos) | Implementado |
| RNF-03 | Segurança | Nenhum segredo no código: configuração só por `.env`, que está no `.gitignore` | Implementado |
| RNF-04 | Segurança | Interface e Ollama acessíveis apenas em `127.0.0.1` | Implementado |
| RNF-05 | Segurança | Nomes de arquivo sanitizados (sem `../`), downloads limitados a `http`/`https` e texto externo escapado na tela | Implementado |
| RNF-06 | Segurança | O índice em `pickle` só é carregado de `PQA_HOME` local, e a documentação alerta contra arquivos de terceiros | Implementado |
| RNF-07 | Confiabilidade | Gravação atômica do índice e do manifesto (arquivo temporário + `os.replace`) | Implementado |
| RNF-08 | Confiabilidade | Falha de indexação não deixa arquivo órfão nem é repetida automaticamente | Implementado |
| RNF-09 | Desempenho | Rodar com 8 a 16 GB de RAM, em CPU ou GPU de 4 a 6 GB, com modelos de 2b a 9b. Resposta típica de 1 a 3 minutos | Não medido nesta revisão |
| RNF-10 | Desempenho | A checagem do Ollama não bloqueia a interface por mais de 3 s e fica em cache por 30 s | Implementado |
| RNF-11 | Portabilidade | Mesmo código no Windows 11 e no Linux (Deepin/Ubuntu), com Python 3.11+. Docker opcional | Implementado |
| RNF-12 | Manutenibilidade | Código modular em camadas, sem dependências circulares, com módulos de até cerca de 300 linhas (exceto a UI) | Implementado |
| RNF-13 | Testabilidade | Testes unitários sem rede e sem Ollama (dependências injetadas), rodando com `python -m pytest` | Implementado (195 testes) |
| RNF-14 | Reprodutibilidade | Versões de dependências fixadas (lock) | Proposto |
| RNF-15 | Usabilidade | Interface em português, com mensagens que dizem o que fazer em caso de erro | Implementado |
| RNF-16 | Integridade acadêmica | Lembrar o usuário de conferir as citações no original | Implementado (aviso no README e no .md exportado) |

## 4. Casos de uso

### UC-01: Montar o acervo com arquivos próprios

- **Ator:** pesquisador
- **Pré-condição:** Ollama no ar, com o modelo instalado.
- **Fluxo principal:**
  1. O usuário seleciona um ou mais arquivos na seção "Enviar documentos".
  2. O sistema valida cada arquivo (RF-02).
  3. O sistema salva o arquivo (RF-03) e o indexa.
  4. O sistema salva o índice em disco (RF-05) e mostra "Indexado: <citação>".
- **Fluxos alternativos:**
  - 2a. Arquivo inválido: o sistema mostra o motivo e não grava nada.
  - 3a. O conteúdo já está no acervo: o sistema ignora o arquivo em silêncio (RF-04).
  - 3b. A indexação falha (por exemplo, o Ollama caiu): o sistema mostra o erro, apaga o arquivo recém-gravado e não tenta de novo nesta sessão.
- **Pós-condição:** o documento aparece em "Ver documentos" e continua lá depois de reiniciar o app.

### UC-02: Buscar e adicionar artigo em acesso aberto

- **Ator:** pesquisador
- **Fluxo principal:**
  1. O usuário digita um tema e clica em "Buscar".
  2. O sistema consulta os catálogos em cascata (RF-11) e completa os PDFs pelo Unpaywall e pelo SciELO (RF-13).
  3. O sistema lista os resultados (RF-12).
  4. O usuário clica em "Baixar PDF aberto e indexar".
  5. O sistema baixa o PDF (RF-14) e segue a partir do passo 3 do UC-01.
- **Fluxos alternativos:**
  - 2a. Um catálogo falha: a busca segue nos outros e mostra um aviso (RF-15).
  - 2b. Todos falham: o sistema mostra "Nenhum catálogo respondeu".
  - 5a. O link devolve HTML (login ou paywall): o sistema mostra o erro e orienta a baixar manualmente.
  - 5b. O PDF já está no acervo: o arquivo baixado é descartado.

### UC-03: Perguntar ao acervo e usar a resposta num texto

- **Ator:** pesquisador
- **Pré-condição:** acervo com pelo menos 1 documento e Ollama pronto.
- **Fluxo principal:**
  1. O usuário escreve a pergunta e clica em "Perguntar".
  2. O sistema valida a pergunta (RF-19), acrescenta a instrução de idioma (RF-20) e consulta o PaperQA2.
  3. O sistema mostra a resposta com citações e os trechos-fonte (RF-21).
  4. O usuário baixa a resposta em `.md` (RF-22) e confere as citações no original.
- **Fluxo alternativo:**
  - 2a. Erro do LLM ou timeout: o sistema mostra a falha e mantém o acervo intacto.

### UC-04: Trocar de modelo

- **Ator:** pesquisador
- **Fluxo:**
  1. O usuário edita `OLLAMA_MODEL` no `.env` e roda `ollama pull`.
  2. O usuário reinicia o app.
- **Fluxo alternativo:**
  - 1a. Se ele trocar o `EMBEDDING_MODEL`, o sistema detecta a mudança (RF-28) e pede para reindexar.

### UC-05: Recuperar de índice corrompido ou incompatível

- **Fluxo:**
  1. Ao abrir, o sistema não consegue ler o `docs.pkl` ou o `meta.json`.
  2. O sistema mostra o motivo e a opção "Apagar índice e recomeçar" (RF-29).
  3. Os arquivos ficam em `documentos/` para serem reenviados.

### UC-06: Resumir um documento ou escrever um texto acadêmico com ABNT

- **Ator:** pesquisador
- **Pré-condição:** acervo com documentos e IA pronta.
- **Fluxo principal:**
  1. Em *Dados da referência (ABNT)*, o usuário preenche autor, título, ano e editora ou periódico de cada documento (RF-36).
  2. Na seção 3, escolhe *Resumo de documento* e o documento, ou *Texto acadêmico*, o tema e as seções (RF-34).
  3. O sistema consulta o acervo com instruções em português acadêmico (RF-35): para o resumo, só trechos do documento; para o texto, uma busca por seção, mostrando o progresso.
  4. O código troca as marcas de citação por (Sobrenome, ano, p. X) e monta as REFERÊNCIAS em ordem alfabética (RF-37).
  5. O usuário baixa o `.md` e revisa citações e páginas no original.
- **Fluxos alternativos:**
  - 1a. PDF baixado pela busca: os dados vêm do catálogo e o usuário só confere.
  - 4a. Documento sem dados ABNT: a citação usa o nome interno e a referência fica marcada como incompleta.
  - 3a. Falha da IA numa seção: as seções já escritas são mantidas e mostradas.

## 5. Arquitetura

### 5.1 Camadas

```
┌──────────────────────────── Entrada (UI) ────────────────────────────┐
│ app.py  (Streamlit: tela, estado da sessão, mensagens)               │
└───────────────┬──────────────────────────────┬───────────────────────┘
                │                              │
┌───────────── Regra de negócio ─────────────┐ │
│ research_service.py                         │ │
│  add_document · ask · reset · build_question│ │
│ writing_service.py (resumo, texto por seções)│ │
│ abnt.py · citations.py · academic_prompts.py │ │
└───────┬───────────────────────┬────────────┘ │
        │                       │              │
┌──── Dados ──────────┐ ┌── Integrações ────────────────────────────────┐
│ library.py          │ │ llm_settings.py  → PaperQA2 Settings (Ollama)  │
│  arquivos, docs.pkl,│ │ ollama_health.py → GET /api/tags               │
│  manifest, meta     │ │ search/          → Oasisbr, S2, Crossref,      │
└─────────────────────┘ │                    Unpaywall, download         │
                        └────────────────────────────────────────────────┘
Utilitários: config.py · async_runner.py · export.py · ui_helpers.py
```

As dependências seguem num só sentido (UI → serviço → dados/integrações), e nenhum módulo de baixo importa o de cima. `search/download.py` reutiliza `sanitize_filename` e `unique_path` de `library.py`, que não importa nada do pacote.

### 5.2 Componentes externos

| Componente | Papel | Observação |
| --- | --- | --- |
| PaperQA2 (`paper-qa`) | Parsing, chunking, embeddings, recuperação e resposta com citações | Modo manual (`Docs.aadd` / `Docs.aquery`), sem agente |
| Motor de IA (LiteLLM) | LLM para os quatro papéis | Ollama por padrão; troca por `.env` (RF-30) |
| sentence-transformers | Embeddings locais (`st-multi-qa-MiniLM-L6-cos-v1`) | Via extra `paper-qa[local]` |
| Streamlit | Interface web local | Só em `127.0.0.1` |
| Oasisbr, Semantic Scholar, Crossref, Unpaywall, SciELO | Descoberta de artigos e de PDFs abertos | APIs públicas. O Semantic Scholar tem limite de taxa sem chave |

### 5.3 Dados persistidos

| Arquivo | Conteúdo | Formato |
| --- | --- | --- |
| `PDF_DIR/*` | Documentos originais | Binário |
| `PQA_HOME/acervo/docs.pkl` | Objeto `Docs` (textos, embeddings, metadados) | pickle |
| `PQA_HOME/acervo/manifest.json` | SHA-256 → arquivo, citação, origem, data | JSON |
| `PQA_HOME/acervo/meta.json` | Modelo de embedding usado | JSON |

### 5.4 Configuração (`.env`)

| Variável | Padrão | Uso |
| --- | --- | --- |
| `LLM_PROVIDER` | `ollama` | Provedor do motor de IA |
| `LLM_MODEL` | `qwen3.5:4b` | Modelo (aceita `OLLAMA_MODEL` por compatibilidade) |
| `LLM_API_BASE` | `http://localhost:11434` no Ollama | Servidor (aceita `OLLAMA_BASE_URL`) |
| `SUMMARY_LLM_MODEL` | igual ao `LLM_MODEL` | Modelo para resumir trechos |
| `LLM_TEMPERATURE` | 0 no Ollama; não enviado nos demais | Temperatura |
| `*_API_KEY` | vazio | Chave do provedor na nuvem |
| `EMBEDDING_API_BASE` | vazio | Servidor do embedding |
| `ANSWER_LENGTH`, `EVIDENCE_K`, `ANSWER_MAX_SOURCES` | `cerca de 300 palavras`, 10, 5 | Tamanho e abrangência da resposta |
| `EMBEDDING_MODEL` | `st-multi-qa-MiniLM-L6-cos-v1` | Embeddings locais |
| `PDF_DIR` | `./documentos` | Arquivos |
| `PQA_HOME` | `./.pqa` | Índice e cache |
| `ANSWER_LANGUAGE` | `português do Brasil` | Idioma das respostas |
| `CONTACT_EMAIL` | vazio | Unpaywall e Crossref (placeholders são ignorados) |
| `SEMANTIC_SCHOLAR_API_KEY` | vazio | Opcional, aumenta o limite de buscas |

## 6. Restrições e premissas

- **Premissa:** o usuário tem permissão de uso dos livros que anexa. O sistema não verifica direitos autorais.
- **Restrição:** a qualidade das respostas depende do modelo local. Modelos de 2b a 4b erram mais que modelos grandes.
- **Restrição:** o formato do `docs.pkl` depende da versão do `paper-qa`. Atualizar a biblioteca pode exigir reindexação.
- **Premissa:** uso por uma pessoa por vez. Não há controle de concorrência entre abas.

## 7. Critérios de aceitação da versão 0.2

1. `python -m pytest` passa sem rede e sem Ollama.
2. Depois de indexar um PDF e reiniciar o app, a pergunta funciona sem reindexar *(validar no PC do usuário com o Ollama)*.
3. A busca com `CONTACT_EMAIL` vazio ou inválido devolve resultados sem erro.
4. `docker compose up --build` sobe a interface em `http://localhost:8501` *(validar no PC com Docker)*.
5. Nenhuma chamada a `api.openai.com` durante a indexação e as perguntas *(validar com o Ollama; garantido pela configuração e coberto por teste)*.

## 8. Rastreabilidade (requisito → código → teste)

| Requisito | Código | Teste |
| --- | --- | --- |
| RF-01, RF-02 | `library.validate_document` | `tests/test_library.py` |
| RF-03, RF-04 | `library.LibraryRepository.store_file`, `unique_path` | `tests/test_library.py` |
| RF-05 | `library.save_docs` / `load_docs` | `tests/test_library.py`, `tests/test_library_paperqa.py` |
| RF-11, RF-15 | `search/service.search_academic` | `tests/test_academic_search.py` |
| RF-13 | `search/unpaywall.py`, `search/parsing.scielo_pid` | `tests/test_academic_search.py` |
| RF-14 | `search/download.download_pdf` | `tests/test_academic_search.py` |
| RF-19, RF-20 | `research_service.build_question` | `tests/test_research_service.py` |
| RF-22 | `export.answer_to_markdown`, `export.document_to_markdown` | `tests/test_export_and_ui.py` |
| RF-26 | `ollama_health.check_ollama` | `tests/test_ollama_health.py` |
| RF-28 | `library._check_embedding_model` | `tests/test_library.py` |
| RNF-02, RF-30 | `providers.py`, `config.load_config`, `llm_settings.build_settings` | `tests/test_providers.py`, `tests/test_config.py`, `tests/test_llm_settings.py` |
| RF-33 | `llm_health.check_llm` | `tests/test_llm_health.py` |
| RF-34 | `writing_service.AcademicWriter` | `tests/test_writing_service.py` |
| RF-35 | `academic_prompts`, `llm_settings.settings_for_mode` | `tests/test_academic_prompts.py`, `tests/test_llm_settings.py` |
| RF-36 | `abnt.build_reference`, `abnt.prefill_from_catalog`, `library.set_reference` | `tests/test_abnt.py`, `tests/test_library.py` |
| RF-37 | `abnt.format_reference`, `citations.format_answer` | `tests/test_abnt.py`, `tests/test_citations.py`, `tests/test_research_service.py` |
| RNF-08 | `research_service.add_document` | `tests/test_research_service.py` |
