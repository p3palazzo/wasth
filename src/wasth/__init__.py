"""WASTH: Web App para Sítios Tradicionais e Históricos

Este pacote define os modelos de dados dos Documentários e fornece
utilitários de validação, normalização e georreferenciamento, além de
utilitários para linha de comando e (futuramente) uma interface web.
"""

__version__ = "0.6.0"

__all__ = ["Work"]


from .models import Work
