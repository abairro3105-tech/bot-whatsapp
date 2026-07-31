"""
Configurações do bot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# WhatsApp Business API
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "token_padrao_123")

# Claude API
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

# Servidor
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("DEBUG", "False") == "True"

# Comportamento do bot
MAX_CONVERSATION_HISTORY = int(os.getenv("MAX_CONVERSATION_HISTORY", 10))
MESSAGE_TIMEOUT = int(os.getenv("MESSAGE_TIMEOUT", 30))

# Validações
REQUIRED_VARS = ["WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID", "CLAUDE_API_KEY"]

def validate_config():
    """Validar se todas as variáveis necessárias estão definidas"""
    missing = [var for var in REQUIRED_VARS if not os.getenv(var)]

    if missing:
        raise ValueError(f"❌ Variáveis de ambiente faltando: {', '.join(missing)}")

    return True
