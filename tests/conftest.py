"""Configuração dos testes: nada aqui chama o Groq, o backend ou baixa modelos."""

import os
import sys
from pathlib import Path

os.environ.setdefault("GROQ_API_KEY", "chave-de-teste")
sys.path.insert(0, str(Path(__file__).parent.parent))
