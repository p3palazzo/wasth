"""WASTH: Web App para Sítios Tradicionais e Históricos

Este pacote define os modelos de dados dos Documentários e fornece
utilitários de validação, normalização e georreferenciamento, além de
utilitários para linha de comando e (futuramente) uma interface web.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("wasth")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["__version__"]
