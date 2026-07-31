# 🤖 Bot WhatsApp com Claude AI

Bot inteligente para WhatsApp Business que responde automaticamente usando IA Claude.

## 📋 Características

✅ Respostas inteligentes com Claude AI  
✅ Histórico de conversa por cliente  
✅ Webhook validado com Meta  
✅ Indicador de "digitando..."  
✅ Mensagens marcadas como lidas  
✅ Suporte a múltiplos tipos de mensagens  
✅ Logging completo  

---

## 🚀 Setup Rápido

### 1. Pré-requisitos

- Python 3.8+
- Conta Anthropic (Claude API)
- Conta Meta/Facebook (WhatsApp Business)

### 2. Clonar e Instalar

```bash
# Clone o repositório
git clone <seu_repo>
cd whatsapp_bot

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente

```bash
# Copiar arquivo de exemplo
cp .env.example .env

# Editar .env com suas credenciais
nano .env
```

---

## 🔐 Obter Credenciais

### A. WhatsApp Business API

1. **Ir para** [developers.facebook.com](https://developers.facebook.com)
2. **Criar novo app** → Tipo: Business
3. **Adicionar produto**: WhatsApp
4. **Na seção "Getting Started":**
   - Copiar **Access Token** → `WHATSAPP_TOKEN`
   - Copiar **Phone Number ID** → `WHATSAPP_PHONE_ID`
   - Copiar **Business Account ID** → `WHATSAPP_BUSINESS_ACCOUNT_ID`

5. **Criar Verify Token:**
   - Use qualquer string aleatória (ex: `abc123xyz789`)
   - Coloque em `VERIFY_TOKEN`

### B. Claude API Key

1. **Ir para** [console.anthropic.com](https://console.anthropic.com)
2. **Criar nova API Key**
3. Copiar para `CLAUDE_API_KEY`

### C. Seu .env deve ficar assim:

```env
WHATSAPP_TOKEN=EAABi4j2g...
WHATSAPP_PHONE_ID=120239...
WHATSAPP_BUSINESS_ACCOUNT_ID=127349...
VERIFY_TOKEN=meu_token_secreto_123
CLAUDE_API_KEY=sk-ant-v0c...
PORT=5000
DEBUG=False
```

---

## 🏃 Rodar Localmente

### Opção 1: Desenvolvimento Local

```bash
python main.py
```

Servidor rodando em `http://localhost:5000`

### Opção 2: Expor para Internet (ngrok)

```bash
# Terminal 1: Rodar Flask
python main.py

# Terminal 2: Expor com ngrok
ngrok http 5000
```

Será gerada uma URL como: `https://abc123.ngrok.io`

---

## 🔗 Configurar Webhook na Meta

Depois de ter seu servidor rodando (ou ngrok):

### Passos:

1. **No Facebook Developers:**
   - Ir para seu App → WhatsApp → Configuração
   - Seção "Webhook"

2. **Callback URL:**
   ```
   https://abc123.ngrok.io/webhook
   ```

3. **Verify Token:**
   ```
   meu_token_secreto_123
   ```
   (Use o mesmo do `.env`)

4. **Clique em "Verify and Save"**
   - A Meta enviará GET request para validar
   - Se aparecer "✅ Webhook verificado", está funcionando!

5. **Subscribe aos eventos:**
   - Marcar: `messages`
   - Clique em "Subscribe"

---

## 📱 Testar o Bot

1. Enviar mensagem para seu número WhatsApp Business
2. O bot deve responder em segundos com IA Claude

### Exemplo:

```
Você: Olá, como funcionam os horários de atendimento?
Bot: Nossos horários de atendimento são seg-sex das 9h às 18h.
```

---

## 🛠️ Personalizar o Bot

### Mudar o System Prompt (comportamento)

Editar `claude_handler.py` e alterar `self.system_prompt`:

```python
self.system_prompt = """Você é um assistente de suporte técnico.
Responda perguntas sobre nossos produtos em tom profissional.
Se não souber, sugira encaminhar para um especialista."""
```

### Adicionar Lógica Customizada

Em `main.py`, na função `handle_message()`, você pode:

```python
# Exemplo: Detectar palavras-chave
if "horário" in message_text.lower():
    response_text = "Estamos abertos seg-sex das 9h às 18h"
else:
    response_text = claude_handler.get_response(message_text)
```

---

## 📊 Estrutura de Arquivos

```
whatsapp_bot/
├── main.py                 # Servidor Flask + webhook
├── claude_handler.py       # Integração com Claude
├── config.py              # Configurações
├── requirements.txt       # Dependências Python
├── .env.example          # Template de variáveis
├── .env                  # Variáveis (não commitar!)
└── README.md            # Este arquivo
```

---

## 🚀 Deploy em Produção

### Opção 1: Heroku

```bash
# Criar app
heroku create meu-bot-whatsapp

# Setvar variáveis (usar seu dashboard ou CLI)
heroku config:set WHATSAPP_TOKEN=...
heroku config:set CLAUDE_API_KEY=...

# Deploy
git push heroku main
```

### Opção 2: Railway

1. Conectar repositório GitHub
2. Railway detecta `requirements.txt` automaticamente
3. Setvar variáveis no dashboard
4. Deploy automático

### Opção 3: VPS (DigitalOcean, AWS, etc)

```bash
# SSH na máquina
ssh user@seu_vps

# Clonar repo
git clone <seu_repo>
cd whatsapp_bot

# Instalar dependências
pip install -r requirements.txt

# Rodar com gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app

# (Opcional) Usar PM2 ou systemd para manter rodando
```

---

## 🐛 Troubleshooting

### ❌ "Webhook não valida com Meta"

**Solução:**
- Verificar se `VERIFY_TOKEN` é idêntico em `.env` e Meta
- Certificar que servidor está rodando
- Checar logs: `print()` statements em `main.py`

### ❌ "Erro de API do Claude"

**Solução:**
- Validar `CLAUDE_API_KEY` está correto
- Checar se tem créditos na Anthropic
- Ver logs de erro: `logger.error()`

### ❌ "Mensagens não são recebidas"

**Solução:**
- Verificar se webhook está subscrito em `messages`
- Validar número de telefone está correto
- Checar se app está aprovado (status em Meta)

### ❌ "Muita latência nas respostas"

**Solução:**
- Claude às vezes leva alguns segundos
- Aumentar timeout do WhatsApp (difícil)
- Considerar usar modelo mais rápido (Claude Haiku)

---

## 📝 Logs

Ver o que está acontecendo:

```bash
# Terminal rodando servidor
# Logs aparecem em tempo real
# Exemplo:
# 📨 Mensagem recebida: {...}
# 📱 De: 5511999999999 | Mensagem: Olá
# ✅ Resposta gerada
```

---

## 🔒 Segurança

⚠️ **IMPORTANTE:**

- Nunca commitar `.env` com credenciais reais
- Usar secrets no GitHub Actions / CI/CD
- Validar tokens em requisições
- Usar HTTPS em produção (https://seu_dominio.com/webhook)
- Rotacionar API keys periodicamente

---

## 📚 Recursos

- [Claude API Docs](https://docs.anthropic.com/)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [ngrok Docs](https://ngrok.com/docs)

---

## 💬 Suporte

- Problemas? Checar logs
- Dúvidas sobre Claude? Ver docs da Anthropic
- Dúvidas sobre WhatsApp? Ver docs da Meta

---

## 📄 Licença

MIT License - Use livremente!

---

**Pronto para usar! 🎉**

