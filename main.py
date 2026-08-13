"""
Bot WhatsApp com integração Claude
Webhook para receber e responder mensagens
"""

import os
import json
import logging
import threading
from flask import Flask, request, jsonify
from datetime import datetime
import requests
from dotenv import load_dotenv
from claude_handler import ClaudeHandler

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar Flask
app = Flask(__name__)

# Credenciais
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "seu_token_verificacao")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# Alertas de atendimento humano (e-mail via Brevo API - HTTPS)
ALERT_EMAIL = os.getenv("ALERT_EMAIL")          # quem recebe todos os alertas
ALERT_EMAIL_COMERCIAL = os.getenv("ALERT_EMAIL_COMERCIAL", "marcos08018@gmail.com")  # cópia nos alertas comerciais
ALERT_FROM = os.getenv("ALERT_FROM", "abairro3105@gmail.com")  # remetente
BREVO_API_KEY = os.getenv("BREVO_API_KEY")      # chave da API Brevo

# Inicializar handler Claude
claude_handler = ClaudeHandler(api_key=CLAUDE_API_KEY)

# =====================
# ENDPOINTS WEBHOOK
# =====================

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """
    GET: Verificação inicial do webhook com Meta
    POST: Receber mensagens do WhatsApp
    """

    if request.method == "GET":
        return verify_webhook(request)

    if request.method == "POST":
        return handle_message(request)


def verify_webhook(req):
    """
    Verifica o webhook com Meta
    Meta envia: hub.mode, hub.challenge, hub.verify_token
    """
    mode = req.args.get("hub.mode")
    token = req.args.get("hub.verify_token")
    challenge = req.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ Webhook verificado com sucesso")
        return challenge, 200
    else:
        logger.warning("❌ Falha na verificação do webhook")
        return "Unauthorized", 403


def handle_message(req):
    """
    Processa mensagens recebidas do WhatsApp
    """
    try:
        body = req.get_json()
        logger.info(f"📨 Mensagem recebida: {json.dumps(body, indent=2)}")

        # Extrair dados da mensagem
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return jsonify({"success": True}), 200

        message = messages[0]
        sender_phone = message.get("from")
        message_id = message.get("id")
        timestamp = message.get("timestamp")

        # Extrair texto da mensagem
        message_text = extract_message_text(message)

        if not message_text:
            logger.warning("Mensagem sem texto recebida")
            return jsonify({"success": True}), 200

        logger.info(f"📱 De: {sender_phone} | Mensagem: {message_text}")

        # Marcar como lida
        mark_as_read(message_id)

        # Enviar "digitando..."
        send_typing_indicator(sender_phone)

        # Gerar resposta com Claude (histórico separado por cliente)
        response_text = claude_handler.get_response(message_text, phone_number=sender_phone)

        # Detectar pedido de atendimento humano
        if "[HUMANO]" in response_text:
            response_text = response_text.replace("[HUMANO]", "").strip()
            # Gerar resumo da conversa para a equipe
            summary = claude_handler.summarize_conversation(sender_phone)
            transcript = claude_handler.get_transcript(sender_phone)
            # Enviar alerta por e-mail em segundo plano (não trava a resposta)
            threading.Thread(
                target=send_human_alert,
                args=(sender_phone, message_text, response_text, summary, transcript),
                daemon=True
            ).start()

        # Enviar resposta (corrigindo nono dígito de números brasileiros)
        send_message(fix_brazil_number(sender_phone), response_text)

        return jsonify({"success": True}), 200

    except Exception as e:
        logger.error(f"❌ Erro ao processar mensagem: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def send_human_alert(client_phone, client_message, bot_reply, summary=None, transcript=None):
    """
    Envia e-mail de alerta quando um cliente precisa de atendimento humano.
    Usa a API HTTPS do Brevo (o Render bloqueia SMTP tradicional).
    """
    if not (ALERT_EMAIL and BREVO_API_KEY):
        logger.warning("⚠️ Alerta humano detectado, mas e-mail não configurado (ALERT_EMAIL/BREVO_API_KEY)")
        return

    try:
        phone_fmt = fix_brazil_number(client_phone)
        wa_link = f"https://wa.me/{phone_fmt}"

        summary_block = f"""📋 RESUMO DO QUE O CLIENTE QUER:
{summary}

""" if summary else ""

        transcript_block = f"""📜 CONVERSA COMPLETA:
{transcript}

""" if transcript else ""

        body = f"""🔔 ATENDIMENTO HUMANO SOLICITADO

📱 Cliente: +{phone_fmt}
🔗 Abrir conversa: {wa_link}

{summary_block}💬 Última mensagem do cliente:
"{client_message}"

🤖 O que o bot respondeu:
"{bot_reply}"

{transcript_block}⏰ Recebido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}

--
Bot Grupo Inova Cosmética
"""
        # Destinatários: alertas COMERCIAIS vão também para o e-mail do comercial
        recipients = [{"email": ALERT_EMAIL}]
        is_comercial = summary and "TIPO: Comercial" in summary
        if is_comercial and ALERT_EMAIL_COMERCIAL:
            recipients.append({"email": ALERT_EMAIL_COMERCIAL})

        subject_prefix = "💼 COMERCIAL" if is_comercial else "🔔"

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "sender": {"name": "Bot Grupo Inova", "email": ALERT_FROM},
                "to": recipients,
                "subject": f"{subject_prefix} Cliente aguarda atendimento humano: +{phone_fmt}",
                "textContent": body
            },
            timeout=20
        )

        if response.status_code in (200, 201):
            logger.info(f"📧 Alerta de atendimento humano enviado para {ALERT_EMAIL}")
        else:
            logger.error(f"❌ Brevo retornou erro: {response.status_code} {response.text}")

    except Exception as e:
        logger.error(f"❌ Erro ao enviar alerta por e-mail: {str(e)}")


def fix_brazil_number(phone):
    """
    Corrige números brasileiros sem o nono dígito.
    O WhatsApp entrega o número como 55 + DDD + 8 dígitos (ex: 554191756183),
    mas a API exige o formato com 9 (ex: 5541991756183).
    """
    if phone and phone.startswith("55") and len(phone) == 12:
        return phone[:4] + "9" + phone[4:]
    return phone


def extract_message_text(message):
    """Extrai texto da mensagem em diferentes formatos"""

    # Texto simples
    if "text" in message:
        return message["text"].get("body", "")

    # Imagem com legenda
    if "image" in message:
        return message["image"].get("caption", "[Imagem recebida]")

    # Documento
    if "document" in message:
        return "[Documento recebido]"

    # Áudio
    if "audio" in message:
        return "[Áudio recebido]"

    return None


def send_typing_indicator(phone_number):
    """Envia indicador de "digitando..."ao cliente"""
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "typing": "on"
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        logger.info(f"Digitando indicador enviado para {phone_number}")
    except Exception as e:
        logger.error(f"Erro ao enviar digitando: {str(e)}")


def mark_as_read(message_id):
    """Marca mensagem como lida"""
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id
    }

    try:
        requests.post(url, json=data, headers=headers)
    except Exception as e:
        logger.error(f"Erro ao marcar como lida: {str(e)}")


def send_message(phone_number, message_text):
    """Envia mensagem para o WhatsApp"""
    url = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    # Dividir mensagem se > 4096 caracteres (limite do WhatsApp)
    max_length = 4096
    if len(message_text) > max_length:
        messages = [message_text[i:i+max_length] for i in range(0, len(message_text), max_length)]
    else:
        messages = [message_text]

    for msg in messages:
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "text",
            "text": {
                "preview_url": True,
                "body": msg
            }
        }

        try:
            response = requests.post(url, json=data, headers=headers)
            result = response.json()

            if "id" in result:
                logger.info(f"✅ Mensagem enviada para {phone_number}")
                return result
            else:
                logger.error(f"Erro ao enviar: {result}")
                return None

        except Exception as e:
            logger.error(f"Erro na requisição: {str(e)}")
            return None


# =====================
# ENDPOINTS ADICIONAIS
# =====================

@app.route("/health", methods=["GET"])
def health():
    """Health check do servidor"""
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/", methods=["GET"])
def index():
    """Página inicial"""
    return """
    <h1>🤖 Bot WhatsApp com Claude</h1>
    <p>Servidor rodando com sucesso!</p>
    <ul>
        <li>POST /webhook - Receber mensagens</li>
        <li>GET /health - Status do servidor</li>
    </ul>
    """, 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno do servidor: {str(error)}")
    return jsonify({"error": "Erro interno do servidor"}), 500


# =====================
# INICIAR SERVIDOR
# =====================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False") == "True"

    logger.info(f"🚀 Iniciando bot WhatsApp na porta {port}")
    logger.info(f"DEBUG mode: {debug}")

    # Para produção, use um servidor WSGI (gunicorn, waitress, etc)
    app.run(host="0.0.0.0", port=port, debug=debug)
