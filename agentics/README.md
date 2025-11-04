## Agente simples de leitura de vencimento
### API (FastAPI)

Subir a API:

```bash
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints:
- POST `/extract` (multipart): campo `file` com `.pdf/.jpg/.png/.txt` → retorna JSON de extração e grava em `retornos/`.
- POST `/extract/by-path` (JSON): `{ "path": "arquivo.pdf" }` → busca em `dados/` se necessário.

Saídas padronizadas são gravadas em `retornos/extracao_N.json` e, se inédito, `retornos/transcricao_N.json`.


Este projeto contém um agente básico em Python que lê o conteúdo de um documento (texto ou PDF) e tenta extrair a data de vencimento (vencimento de boleto/fatura/pagamento).

### Instalação rápida

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: . .venv/Scripts/Activate.ps1
pip install -r requirements.txt
```

### Como usar

Requisitos opcionais para PDF:
- Para leitura de PDF, instale `PyPDF2` (opcional). O agente possui fallback para `pdfminer.six` se `PyPDF2` não extrair texto.

```bash
pip install PyPDF2 pdfminer.six  # recomendados para PDFs
```

OCR (opcional, para PDFs escaneados/sem texto):

- Caminho 1 (Tesseract): instale o Tesseract no Windows e use `pytesseract` + `pdf2image` + Poppler.

```bash
pip install pytesseract pdf2image
```

**Configuração do Poppler (Windows):**

O agente detecta automaticamente o Poppler nos caminhos comuns, mas se instalado em outro local, configure via variável de ambiente:

```powershell
# PowerShell
$env:POPPLER_PATH = "C:\caminho\para\poppler\bin"
# Ou adicione ao PATH do sistema
```

**Configuração do Tesseract (opcional):**

O agente detecta automaticamente em `C:\Program Files\Tesseract-OCR\`. Para caminho customizado:

```powershell
$env:TESSERACT_CMD = "C:\caminho\para\tesseract.exe"
```

- Caminho 2 (sem Tesseract): use EasyOCR em CPU.

```bash
pip install easyocr numpy
# Se quiser performance melhor ou evitar conflitos, instale o PyTorch CPU antes:
# pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Observação: o agente tenta em ordem: PyPDF2 → pdfminer.six → OCR com Tesseract → OCR com EasyOCR. Para imagens, tenta Tesseract e depois EasyOCR.

Saídas do agente

O agente grava apenas arquivos JSON sequenciais ao lado do arquivo de entrada:

- `extracao_N.json` com os campos extraídos para uso por outro agente.

Suporte a imagens

- Formatos aceitos: `.png`, `.jpg`, `.jpeg`, `.tif`, `.tiff`, `.bmp`
- Requisitos: `pytesseract` e `Pillow` (instalados com `pip install pytesseract pillow`) e o Tesseract OCR instalado no sistema (Windows: instale o executável e coloque no PATH; selecione idioma português).
- Uso:

```bash
python -m agents.vencimento_agent caminho/da/imagem.jpg
```

Assim como nos PDFs, será gerado apenas o `extracao_N.json`.

Execução a partir do diretório do projeto:

```bash
python -m agents.vencimento_agent caminho/do/arquivo.txt
```

Ou lendo do `stdin` (útil em pipelines):

```bash
type caminho\do\arquivo.txt | python -m agents.vencimento_agent -
```

Saída JSON com campos:
- `due_date`: data normalizada no formato `YYYY-MM-DD`
- `original`: a data conforme encontrada no texto
- `confidence`: `high` | `medium` | `low`

Quando o input é um arquivo (não `stdin`), o agente cria automaticamente um JSON sequencial com os campos extraídos.

Exemplo de entrada (`.txt`):

```
Fatura Nº 12345\n
Vencimento: 15/11/2025\n
Valor: R$ 250,00
```

Saída:

```json
{"due_date": "2025-11-15", "original": "15/11/2025", "confidence": "high"}
```

### Notas

- Heurística simples: o agente procura datas no formato brasileiro (dd/mm/aaaa, dd-mm-aaaa, dd.mm.aaaa e variantes com ano de 2 dígitos) e escolhe a data mais próxima de palavras-chave como "vencimento", "data de vencimento", "pagamento até".
- Para anos com 2 dígitos, assume-se `00-49 => 2000-2049` e `50-99 => 1950-1999`.
- PDFs digitalizados (escaneados) podem não ter texto extraível via `PyPDF2`. Para esses casos, será necessário OCR (ex.: Tesseract). Este projeto não inclui OCR por padrão.

### Endpoints (detalhes e exemplos)

- POST `/extract`
  - multipart/form-data com `file`.
  - Exemplo (PowerShell):
    ```powershell
    curl -Method POST -Uri http://localhost:8000/extract/ -InFile .\dados\Modelo-de-Boleto.pdf -ContentType "multipart/form-data"
    ```
  - Em retorno, além do JSON, arquivos são salvos em `retornos/`.

- POST `/extract/by-path`
  - JSON `{ "path": "caminho\para\arquivo.pdf" }`.
  - Busca automaticamente em `dados/` se o caminho absoluto não existir.

- GET `/extract/returns`
  - Lista arquivos `extracao_*.json` e `transcricao_*.json`.

- GET `/extract/returns/file?path=...`
  - Retorna o conteúdo do arquivo informado (restrito a `retornos/`).

### Variáveis de ambiente suportadas

- `OCR_DPI` (padrão 200): DPI para OCR/conversão de PDFs.
- `OCR_MAX_PAGES` (padrão 1): número máximo de páginas para OCR.
- `TESSERACT_CMD`: caminho do executável do Tesseract (se não estiver no PATH).
- `POPPLER_PATH`: caminho para binários do Poppler no Windows (se necessário).
- `POST_OCR_ENABLED` ("1"/"0"): habilita pós-processamento de OCR com Gemini.
- `GEMINI_API_KEY`: chave para pós-processar o texto OCR (opcional).
- `GEMINI_MODEL` (padrão `gemini-1.5-flash`): modelo usado no pós-processamento.

### Estrutura de diretórios (essencial)

- `dados/`: amostras de entrada.
- `retornos/`: saídas JSON sequenciais (`extracao_N.json`, `transcricao_N.json`).
- `agentics/api/`: aplicação FastAPI.
- `agentics/agents/`: CLI do agente.
- `agentics/core/`: heurísticas de extração/validação.
- `agentics/adapters/`: leitura de PDF/OCR.
- `agentics/io/`: utilitários de escrita/leitura de retornos.

### Frontend (opcional)

Um frontend exemplo está em `baseVisual/frontend`. Para rodar:

```bash
cd baseVisual/frontend
npm install
npm run dev
```

Certifique-se de ajustar o endpoint (`http://localhost:8000`) no frontend, se necessário.


