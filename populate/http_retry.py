"""
http_retry.py
-------------
Wrapper de requests.get com retry automático e backoff exponencial.

Comportamento por tipo de falha:
  ConnectionError / Timeout  — sempre retenta
  HTTP 429 (rate limit)      — retenta respeitando o header Retry-After
  HTTP 5xx (erro do servidor)— retenta
  HTTP 4xx (erro do cliente) — NÃO retenta (problema na requisição em si)

Fórmula de espera:
  wait = base_wait * (2 ** tentativa) + jitter
  tentativa 0 → ~2s
  tentativa 1 → ~4s
  tentativa 2 → ~8s
  tentativa 3 → ~16s
"""

import logging
import random
import time
from typing import Optional

import requests

log = logging.getLogger(__name__)


def get_with_retry(
    url:         str,
    params:      Optional[dict] = None,
    timeout:     int            = 20,
    max_retries: int            = 3,
    base_wait:   float          = 2.0,
) -> requests.Response:
    """
    GET com retry automático e backoff exponencial.

    Parâmetros
    ----------
    url         : URL completa
    params      : query string como dict
    timeout     : timeout em segundos por tentativa
    max_retries : número máximo de tentativas extras (total = max_retries + 1)
    base_wait   : espera base em segundos (dobra a cada tentativa)

    Retorno
    -------
    requests.Response com status 2xx.

    Exceções
    --------
    Lança a última exceção capturada após esgotar as tentativas.
    As funções chamadoras devem continuar com seu próprio try/except.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):

        try:
            r = requests.get(url, params=params, timeout=timeout)

            # Rate limit — respeita o header Retry-After se presente
            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else base_wait * (2 ** attempt)
                wait += random.uniform(0, 1)
                log.warning(
                    f"Rate limit (429) em {url}. "
                    f"Tentativa {attempt + 1}/{max_retries + 1}. "
                    f"Aguardando {wait:.1f}s..."
                )
                time.sleep(wait)
                continue

            # Erros do servidor (5xx) — retenta
            if r.status_code >= 500:
                exc = requests.exceptions.HTTPError(
                    f"HTTP {r.status_code}", response=r
                )
                raise exc

            # Erros do cliente (4xx) — não retenta
            r.raise_for_status()

            return r

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.HTTPError,
        ) as exc:
            last_exc = exc

            if attempt == max_retries:
                log.error(
                    f"Falha definitiva em {url} "
                    f"após {max_retries + 1} tentativas: {exc}"
                )
                raise

            wait = base_wait * (2 ** attempt) + random.uniform(0, 1)
            log.warning(
                f"Erro em {url}: {exc}. "
                f"Tentativa {attempt + 1}/{max_retries + 1}. "
                f"Retentando em {wait:.1f}s..."
            )
            time.sleep(wait)

    raise last_exc  # nunca alcançado, mas satisfaz o type checker