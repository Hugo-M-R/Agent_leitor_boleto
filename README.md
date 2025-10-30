## Agente simples de leitura de vencimento

Este projeto contém um agente básico em Python que lê o conteúdo de um documento (texto ou PDF) e tenta extrair a data de vencimento (vencimento de boleto/fatura/pagamento).

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


