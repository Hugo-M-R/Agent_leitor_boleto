#!/usr/bin/env python3
"""
Conta quantas requisições HTTP foram feitas durante a execução do servidor FastAPI/Uvicorn,
utilizando os logs padrão do Uvicorn.

Como usar (salve os logs em arquivo):
    uvicorn api.agent:app --host 0.0.0.0 --port 8000 > uvicorn.log
    python scripts/contar_requisicoes.py --log-file uvicorn.log

Também funciona lendo logs via pipe em tempo real:
    uvicorn api.agent:app --host 0.0.0.0 --port 8000 | python scripts/contar_requisicoes.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, TextIO, Tuple

# Exemplo de linha de log do Uvicorn:
# INFO:     127.0.0.1:65473 - "GET /get_last_json_extracted HTTP/1.1" 200 OK
LOG_PATTERN = re.compile(
    r"""
    ^\s*(?:INFO|WARNING|ERROR|DEBUG):\s+        # nível de log do Uvicorn
    (?P<ip>[0-9a-fA-F\.:]+):(?P<port>\d+)\s-   # IP e porta do cliente
    \s*\"(?P<method>[A-Z]+)\s+                # método HTTP
    (?P<path>[^\"]+?)\s+HTTP/1\.[01]\"\s+   # path solicitado
    (?P<status>\d{3})                            # status code
    """,
    re.VERBOSE,
)


def _iter_lines(handle: TextIO) -> Iterable[str]:
    """Itera sobre as linhas vindas de um arquivo ou stdin."""
    while True:
        line = handle.readline()
        if not line:
            break
        yield line.rstrip("\n")


def process_lines(lines: Iterable[str]) -> Tuple[int, Counter, Counter, Counter, Counter, int]:
    """Processa linhas do log e retorna estatísticas."""
    endpoint_counter: Counter = Counter()
    status_counter: Counter = Counter()
    method_counter: Counter = Counter()
    ip_counter: Counter = Counter()
    total_requests = 0
    unmatched = 0

    for line in lines:
        match = LOG_PATTERN.search(line)
        if not match:
            unmatched += 1
            continue

        total_requests += 1
        method = match.group("method")
        path = match.group("path")
        status = match.group("status")
        ip = match.group("ip")

        endpoint_counter[(method, path)] += 1
        status_counter[status] += 1
        method_counter[method] += 1
        ip_counter[ip] += 1

    return total_requests, endpoint_counter, status_counter, method_counter, ip_counter, unmatched


def print_summary(
    total: int,
    endpoint_counter: Counter,
    status_counter: Counter,
    method_counter: Counter,
    ip_counter: Counter,
    unmatched: int,
    top_n: int,
) -> None:
    """Imprime o resumo das estatísticas coletadas."""
    print("\n=== Resumo das Requisições ===")
    print(f"Total identificado: {total}")
    if unmatched:
        print(f"Linhas ignoradas (não pareciam requisições HTTP do Uvicorn): {unmatched}")

    print("\nRequisições por método HTTP:")
    for method, count in method_counter.most_common():
        pct = (count / total * 100) if total else 0
        print(f"  {method:<6} {count:>6} ({pct:5.1f}%)")

    print("\nRequisições por status HTTP:")
    for status, count in status_counter.most_common():
        pct = (count / total * 100) if total else 0
        print(f"  {status:<6} {count:>6} ({pct:5.1f}%)")

    print("\nTop endpoints (método + path):")
    for (method, path), count in endpoint_counter.most_common(top_n):
        pct = (count / total * 100) if total else 0
        print(f"  {count:>6}x ({pct:5.1f}%) {method} {path}")

    print("\nTop IPs de origem:")
    for ip, count in ip_counter.most_common(top_n):
        pct = (count / total * 100) if total else 0
        print(f"  {count:>6}x ({pct:5.1f}%) {ip}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Conta requisições HTTP a partir dos logs do Uvicorn/FastAPI."
    )
    parser.add_argument(
        "--log-file",
        "-f",
        type=Path,
        help="Arquivo de log do Uvicorn. Se não for informado, lê da entrada padrão (stdin).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Quantidade de endpoints/IPs para mostrar no ranking (padrão: 10).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.log_file:
        if not args.log_file.exists():
            print(f"[ERRO] Arquivo não encontrado: {args.log_file}", file=sys.stderr)
            sys.exit(1)

        with args.log_file.open("r", encoding="utf-8") as handle:
            results = process_lines(_iter_lines(handle))
    else:
        if sys.stdin.isatty():
            print("Lendo logs da entrada padrão. Pressione Ctrl+C para encerrar.\n", file=sys.stderr)
        try:
            results = process_lines(_iter_lines(sys.stdin))
        except KeyboardInterrupt:
            print("\nInterrompido pelo usuário.", file=sys.stderr)
            sys.exit(0)

    print_summary(*results, top_n=args.top)


if __name__ == "__main__":
    main()
