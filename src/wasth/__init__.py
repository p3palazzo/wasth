"""WASTH: Web App para Sítios Tradicionais e Históricos

Este pacote define os modelos de dados dos Documentários e fornece
utilitários de validação, normalização e georreferenciamento, além de
utilitários para linha de comando e (futuramente) uma interface web.

Como usar:

    from wasth import Work
"""

__version__ = "0.2.1"

__all__ = ["Work", "f_valida"]

from .core.models import Work
from .core.valida_yaml import f_valida
