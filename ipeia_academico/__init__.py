"""IPeia Acadêmico: pesquisa e escrita acadêmica com PaperQA2 + Ollama, 100% local.

Camadas:
- config.py ............ leitura/validação do ambiente (.env)
- llm_settings.py ...... montagem do Settings do PaperQA2 (só Ollama)
- ollama_health.py ..... checagem do servidor Ollama
- library.py ........... acervo persistente (arquivos + índice em disco)
- research_service.py .. regra de negócio: indexar e perguntar
- async_runner.py ...... ponte sync/async para o Streamlit
- search/ .............. busca em catálogos abertos (Oasisbr, S2, Crossref, Unpaywall)
- export.py ............ exportação da resposta para Markdown
- ui_helpers.py ........ funções puras usadas pela interface
"""

__all__ = ["__version__"]
__version__ = "0.2.0"
