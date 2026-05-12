# Assets gerados em runtime

Os arquivos PNG não ficam versionados para evitar erro em ambientes que não aceitam PR com binários.

Ao instalar ou iniciar no Termux, o script `scripts/create_assets.py` cria automaticamente:

- `assets/green.png`
- `assets/signal.png`

Durante a execução, o bot também gera `assets/green_latest.png` quando confirmar GREEN.
