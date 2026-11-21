# Instalar o IPeia Acadêmico no notebook a partir do pendrive

O pendrive é exFAT. O exFAT não guarda permissões nem links simbólicos, então
**o app não roda de dentro do pendrive**: o ambiente Python (`.venv`) quebra.
Por isso o pendrive leva um pacote `.zip`, que você extrai no disco do notebook.

Conteúdo da pasta `IPeia-Academico` no pendrive:

- `ipeia-academico.zip`: o código completo (sem `.env`, sem acervo, sem chaves).
- `instalar-notebook.sh`: extrai o zip no disco e instala (Linux).
- `INSTALAR-NOTEBOOK.md`: este guia.

A instalação baixa as bibliotecas Python e o modelo de IA, então **precisa de internet**.
Faça antes do dia da defesa e teste uma vez.

## Linux (Ubuntu ou Deepin)

1. Instale o Python, se faltar: `sudo apt update && sudo apt install -y python3 python3-venv python3-pip unzip`
2. No terminal, na pasta do pendrive:

   ```bash
   bash instalar-notebook.sh
   ```

   Ele extrai em `~/ipeia-academico` (ou na pasta que você passar: `bash instalar-notebook.sh /outra/pasta`)
   e roda `scripts/install-ubuntu.sh`. Se a pasta já existir, ele para e não apaga nada.
3. Instale o Ollama e o modelo:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull qwen3.5:4b
   ```

4. Rode: `bash ~/ipeia-academico/scripts/rodar-ubuntu.sh` e abra http://localhost:8501

## Windows

1. Clique com o botão direito em `ipeia-academico.zip` → **Extrair tudo** → `C:\ipeia-academico`.
2. Siga o `INSTALAR-WINDOWS.md` que está dentro da pasta extraída (Python 3.12, Ollama, `install-windows.bat`).

## Trocar a IA (opcional)

No `.env`, mude `LLM_PROVIDER` e `LLM_MODEL` e coloque a chave do provedor
(veja "Trocar o motor de IA" no `README.md`). Com IA na nuvem, os trechos dos
documentos saem do notebook; a tela avisa.

## Roteiro rápido para a demonstração

1. Faixa verde no topo: a IA está pronta.
2. **1. Enviar documentos**: envie um PDF curto e espere indexar.
3. **Dados da referência (ABNT)**: preencha autor, título, ano e editora.
4. **3. Pergunta, resumo ou texto** → *Resumo de documento* → Resumir.
5. Mostre a resposta com (Sobrenome, ano, p. X), a lista de REFERÊNCIAS e **Mostrar fontes**.
6. Baixe o `.md`.

Com o modelo local num notebook sem GPU, cada resposta pode levar alguns minutos.
Deixe um resultado pronto (o `.md` baixado) como plano B.
