# IPeia Acadêmico

Pesquisa, leitura e escrita acadêmica no seu computador, com IA **100% local** (Ollama), sem custo de API e sem enviar seus arquivos para a nuvem.

Você monta um **acervo** com artigos e livros (PDF, TXT, MD, HTML), busca artigos em acesso aberto (Oasisbr/IBICT, Semantic Scholar, Crossref, Unpaywall) e faz perguntas. As respostas trazem citações dos seus documentos e podem ser baixadas em Markdown para usar na escrita.

Construído sobre o [PaperQA2](https://github.com/Future-House/paper-qa) (Apache 2.0), com interface em Streamlit.

> **Atenção acadêmica:** a IA pode errar ou atribuir uma ideia ao documento errado. Confira cada citação no texto original antes de usá-la em um trabalho.

## Documentação

| Documento | Conteúdo |
| --- | --- |
| [docs/REQUISITOS.md](docs/REQUISITOS.md) | Especificação de requisitos (RF/RNF, casos de uso, arquitetura) |
| [docs/ANALISE-TECNICA.md](docs/ANALISE-TECNICA.md) | Revisão do código: falhas encontradas, correções e pendências |
| [INSTALAR-WINDOWS.md](INSTALAR-WINDOWS.md) | Instalação no Windows 11 |
| [INSTALAR-DEEPIN.md](INSTALAR-DEEPIN.md) | Instalação no Deepin/Linux com pendrive |
| [FUNCOES.txt](FUNCOES.txt) | O que cada parte da tela faz |

## Início rápido (Linux / macOS)

```bash
# 1. Ollama: https://ollama.com/download
ollama pull qwen3.5:4b

# 2. App
git clone https://github.com/edidiodantas/Furyu.git ipeia-academico
cd ipeia-academico
python3 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
cp .env.example .env        # edite CONTACT_EMAIL se quiser usar o Unpaywall

# 3. Rodar
streamlit run app.py        # abre em http://localhost:8501
```

No Windows, use `install-windows.bat` e `rodar-windows.bat` ([guia](INSTALAR-WINDOWS.md)).

## Estrutura

```
app.py                      Interface Streamlit (só tela)
ipeia_academico/
  config.py                 Lê e valida o .env
  llm_settings.py           Settings do PaperQA2 com os 4 papéis de LLM no Ollama
  ollama_health.py          Checa se o Ollama e o modelo estão disponíveis
  library.py                Acervo persistente: arquivos, índice (docs.pkl) e manifesto
  research_service.py       Regra de negócio: indexar e perguntar
  async_runner.py           Event loop único para chamar o PaperQA2 a partir do Streamlit
  search/                   Busca em catálogos abertos e download de PDF
    catalogs.py             Oasisbr, Semantic Scholar, Crossref
    unpaywall.py            PDF aberto pelo DOI
    download.py             Download com limite de tamanho e checagem %PDF
    parsing.py              Extração de metadados (funções puras)
    service.py              Cascata de catálogos + deduplicação
  export.py                 Exporta a resposta para Markdown
  ui_helpers.py             Funções puras da interface
tests/                      Testes unitários (pytest), sem rede e sem Ollama
docs/                       Requisitos e análise técnica
scripts/, *.bat, docker/    Instalação e execução
```

## Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Os testes usam dublês (sem rede, sem Ollama). O teste de `llm_settings` é pulado se o `paper-qa` não estiver instalado.

## Por que configurar os quatro papéis de LLM

O PaperQA2 usa quatro papéis de LLM, e o padrão de todos é um modelo da OpenAI:

| Papel | Setting | Uso |
| --- | --- | --- |
| Resposta + metadados | `llm` + `llm_config` | Indexar e responder |
| Resumos de evidência | `summary_llm` + `summary_llm_config` | Resumir trechos |
| Agente | `agent.agent_llm` + `agent_llm_config` | Modo agente |
| Enriquecimento | `parsing.enrichment_llm` + `enrichment_llm_config` | Figuras/tabelas |

`ipeia_academico/llm_settings.py` aponta os quatro para o Ollama, e `tests/test_llm_settings.py` garante isso. **Não defina `OPENAI_API_KEY`.**

## Onde ficam os dados

| O quê | Onde (padrão) |
| --- | --- |
| Arquivos enviados/baixados | `documentos/` (`PDF_DIR`) |
| Índice do acervo | `.pqa/acervo/docs.pkl` e `.pqa/acervo/manifest.json` (`PQA_HOME`) |

O índice usa `pickle` (forma de salvar documentada pelo PaperQA2). **Nunca carregue um `docs.pkl` recebido de outra pessoa**, porque pickle pode executar código. Se atualizar o `paper-qa` e o índice deixar de abrir, use "Apagar índice" na barra lateral e reindexe.

## Docker (opcional)

```bash
docker compose up --build    # http://localhost:8501
```

As portas ficam presas a `127.0.0.1`. Docker não deixa o LLM mais rápido.

## Problemas comuns

| Problema | Solução |
| --- | --- |
| Erro pedindo OpenAI / GPT-4o | Rode `python -m pytest tests/test_llm_settings.py`; não defina `OPENAI_API_KEY` |
| `Connection refused :11434` | Inicie o Ollama e teste `ollama list` |
| Modelo não encontrado | `ollama pull <modelo do .env>` |
| Resposta em inglês | Ajuste `ANSWER_LANGUAGE` no `.env`; modelos pequenos às vezes ignoram |
| Embedding lento na 1ª vez | Download do modelo HuggingFace na primeira indexação |
| Índice ilegível após atualizar | "Apagar índice" e reindexar |

## Licença e créditos

Interface e código do `ipeia_academico/`: [edidiodantas](https://github.com/edidiodantas). Este repositório ainda não tem arquivo de licença. PaperQA2: FutureHouse, licença Apache 2.0.
