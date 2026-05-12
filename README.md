# Aviator AI System — Telegram Bot

Bot modular em Python para geração automática de sinais Aviator a partir da API de velas `https://app.sscashout.online/api/velas`.

> Projeto criado com foco em Termux, versionamento via GitHub, segurança por `.env`, grupos dinâmicos, botões de afiliado, quiz interativo e auto-otimização de estratégia.

## Jeito mais fácil: configurar no GitHub e só rodar no Termux

Se o repositório é privado e você quer editar tudo pelo GitHub, use este fluxo:

1. Edite no GitHub os arquivos dentro de `aviator-bot/config/`:
   - `bots.json` — token do BotFather e chave Gemini opcional.
   - `groups.json` — grupos que recebem sinais.
   - `links.json` — botão/link de afiliado.
   - `settings.json` — tempos, API, nome do bot e limites.
   - `ai_state.json` — criado automaticamente no Termux; não precisa editar no GitHub.
   - `assets/*.png` — gerados automaticamente no Termux; não ficam no PR para evitar erro de binários.
2. No Termux, rode apenas:

```bash
cd newsletter/aviator-bot
bash scripts/start_termux.sh
```

O script `start_termux.sh` faz `git pull`, ativa/cria o ambiente virtual, instala dependências e inicia `python bot.py`.

> Segurança: mesmo em repositório privado, token no GitHub é sensível. Se quiser máxima segurança, deixe `config/bots.json` com `CHANGE_ME` e use `.env` local. O código aceita os dois modos.

## Estrutura

```text
aviator-bot/
├── bot.py
├── .env
├── requirements.txt
├── config/
│   ├── ai_state.example.json
│   ├── bots.json
│   ├── groups.json
│   ├── links.json
│   └── settings.json
├── core/
│   ├── api.py
│   ├── gemini.py
│   ├── signals.py
│   ├── strategy_ai.py
│   ├── telegram.py
│   └── ui.py
├── assets/
│   └── README.md        # PNGs são gerados no Termux, não versionados
├── logs/
└── scripts/
    ├── configure_credentials.py
    ├── create_assets.py
    ├── install_termux.sh
    ├── set_token.py
    └── start_termux.sh
```


## Instalação em um comando só para copiar e executar

Use este comando completo. O erro `bash: https://github.com/...: No such file or directory` acontece quando se cola só o link do GitHub sem `git clone`.

Também foi removida a dependência `google-generativeai` do install principal para evitar o erro do Termux/Python 3.13 ao compilar `cryptography` via `maturin`/Rust. O Gemini agora usa REST com `httpx`, então não precisa compilar Rust.

```bash
pkg update -y && pkg upgrade -y && \
pkg install -y git python clang libjpeg-turbo zlib freetype && \
cd ~ && \
rm -rf newsletter && \
git clone https://github.com/L7NNON-loop/newsletter.git newsletter && \
cd newsletter/aviator-bot && \
bash scripts/install_termux.sh && \
bash scripts/start_termux.sh
```

Se o GitHub pedir login porque o repositório é privado, informe seu usuário do GitHub e um Personal Access Token no lugar da senha.

Depois da primeira vez, quando mudar qualquer configuração no GitHub, cole só isto no Termux:

```bash
cd ~/newsletter/aviator-bot && bash scripts/start_termux.sh
```

## Instalação no Termux

Primeira instalação:

```bash
pkg update -y && pkg upgrade -y
pkg install -y git

git clone <URL_DO_SEU_REPOSITORIO> newsletter
cd newsletter/aviator-bot
bash scripts/install_termux.sh
```

Depois da primeira instalação, para rodar e puxar configurações novas do GitHub:

```bash
cd newsletter/aviator-bot
bash scripts/start_termux.sh
```

## Configurar token pelo GitHub

O arquivo `aviator-bot/config/bots.json` é o lugar para configurar o BotFather e o Gemini pelo GitHub. Neste ambiente de teste, as credenciais fornecidas foram colocadas em `config/bots.json`; quando terminar os testes, gere novos tokens e substitua esses valores.

Exemplo de formato:

```json
{
  "active_bot": "principal",
  "bots": [
    {
      "name": "principal",
      "telegram_token": "123456789:SEU_TOKEN_DO_BOTFATHER",
      "gemini_api_key": "",
      "active": true
    }
  ]
}
```

Para usar outro bot, adicione outro item e troque `active_bot`:

```json
{
  "active_bot": "bot_vip",
  "bots": [
    {
      "name": "principal",
      "telegram_token": "111111:TOKEN_ANTIGO",
      "gemini_api_key": "",
      "active": false
    },
    {
      "name": "bot_vip",
      "telegram_token": "222222:TOKEN_NOVO",
      "gemini_api_key": "",
      "active": true
    }
  ]
}
```

O bot primeiro tenta ler token do `.env`; se o `.env` estiver `CHANGE_ME`, ele usa o bot ativo em `config/bots.json`.

### Configurar credenciais por comando, sem editar arquivo manualmente

Para gravar credenciais somente no Termux, use:

```bash
cd ~/newsletter/aviator-bot && python scripts/configure_credentials.py --telegram-token "SEU_TOKEN_DO_BOTFATHER" --gemini-key "SUA_API_KEY_GEMINI"
```

Para gravar em `config/bots.json` e depois enviar ao GitHub privado, use:

```bash
cd ~/newsletter/aviator-bot && \
python scripts/configure_credentials.py --github-config --telegram-token "SEU_TOKEN_DO_BOTFATHER" --gemini-key "SUA_API_KEY_GEMINI" && \
git add config/bots.json && \
git commit -m "Configure test bot credentials" && \
git push
```

Depois disso, no Termux, rode `bash scripts/start_termux.sh` para puxar a configuração do GitHub e iniciar.

## Configurar token localmente, sem GitHub

Se não quiser colocar token no GitHub, use o arquivo `.env` local:

```bash
python scripts/set_token.py "SEU_TOKEN_DO_BOTFATHER"
```

Para trocar para outro bot, rode o mesmo comando com o novo token. O script atualiza `TELEGRAM_BOT_TOKEN` no `.env`.

## Configurar grupos pelo GitHub

Edite `aviator-bot/config/groups.json`:

```json
{
  "groups": [
    {
      "name": "Junior",
      "id": "-100399362556",
      "active": true
    }
  ]
}
```

Somente grupos com `active: true` recebem sinais, greens e quiz.

## Configurar link de afiliado pelo GitHub

Edite `aviator-bot/config/links.json` para alterar texto ou URL do botão enviado em todas as mensagens de sinal.

```json
{
  "register_button_text": "📌 REGISTRAR AGORA",
  "register_url": "https://media1.placard.co.mz/redirect.aspx?pid=4241&bid=1690"
}
```

## Configurar tempos e comportamento pelo GitHub

Edite `aviator-bot/config/settings.json`:

```json
{
  "bot_name": "AVIATOR AI SYSTEM",
  "api_url": "https://app.sscashout.online/api/velas",
  "min_candles": 20,
  "ai_state_path": "config/ai_state.json",
  "poll_interval_seconds": 2.5,
  "api_timeout_seconds": 10,
  "signal_cooldown_candles": 1,
  "green_check_window_candles": 6,
  "quiz_interval_minutes": 45,
  "quiz_duration_seconds": 60,
  "players_min": 20,
  "players_max": 100,
  "logs_dir": "logs"
}
```

## Controle pelo grupo

Envie no grupo configurado:

- `ON` — ativa sinais e responde `🟢 SISTEMA ATIVO`.
- `Pare` — pausa sinais e responde `🛑 PARADO`.

## Como funciona

- `core/api.py` consulta a API de velas com `httpx`, valida JSON e usa sempre o último valor como vela mais recente.
- `bot.py` mantém um loop event-driven por mudança de vela, evitando spam de requests com sleep configurável.
- `core/signals.py` analisa no mínimo 20 velas, calcula média, volatilidade e tendência curta, e gera proteção/saída respeitando `proteção < saída`.
- `core/strategy_ai.py` registra vitórias/falhas, win rate, streaks e drawdown, salvando estado local em `config/ai_state.json`, que é criado automaticamente no Termux.
- `core/telegram.py` envia mensagens premium, botão de afiliado, quiz e comandos ON/Pare.
- `core/ui.py` centraliza templates visuais e gera a imagem neon de GREEN.

## Segurança e logs

- Tokens podem vir do `.env` local ou do `config/bots.json` quando você optar por configurar pelo GitHub.
- Para evitar erro de `cryptography`/`maturin` no Termux, o `requirements.txt` principal usa apenas dependências leves; Gemini funciona via REST com `httpx`.
- O arquivo `config/ai_state.json` é estado local de performance e fica fora do Git para não atrapalhar `git pull`.
- PNGs de `assets/` são gerados no Termux por `scripts/create_assets.py` e não são versionados, evitando erro de PR com ficheiros binários.
- Logs ficam em `aviator-bot/logs/aviator-bot.log`.
- Falhas de API são tratadas sem derrubar o processo.

## Publicar no GitHub

```bash
git add .
git commit -m "Add Aviator Telegram bot system"
git remote add origin <URL_DO_REPOSITORIO>
git push -u origin main
```

Antes de publicar em repositório público, confirme que `.env` e `config/bots.json` não contêm token real.
