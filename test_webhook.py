"""
Script para testar o webhook localmente
Simula mensagens do WhatsApp
"""

import requests
import json
from datetime import datetime

# URL do seu webhook (altere se necessário)
WEBHOOK_URL = "http://localhost:5000/webhook"

def test_verify():
    """Testa a verificação do webhook"""
    print("\n🧪 Testando verificação do webhook...")

    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "seu_token_verificacao",  # Altere conforme .env
        "hub.challenge": "test_challenge_123"
    }

    response = requests.get(WEBHOOK_URL, params=params)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

    if response.text == "test_challenge_123":
        print("✅ Webhook verificado com sucesso!")
    else:
        print("❌ Falha na verificação")


def test_message():
    """Testa recebimento de mensagem"""
    print("\n🧪 Testando recebimento de mensagem...")

    payload = {
        "entry": [
            {
                "id": "123456789",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "5511999999999",
                                    "id": "msg_123",
                                    "timestamp": str(int(datetime.now().timestamp())),
                                    "type": "text",
                                    "text": {
                                        "body": "Olá! Como você funciona?"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(
        WEBHOOK_URL,
        json=payload,
        headers=headers
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✅ Mensagem recebida com sucesso!")
    else:
        print("❌ Erro ao receber mensagem")


def test_health():
    """Testa health check"""
    print("\n🧪 Testando health check...")

    response = requests.get(f"{WEBHOOK_URL.replace('/webhook', '')}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✅ Servidor está online!")
    else:
        print("❌ Servidor offline")


if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Teste do Bot WhatsApp")
    print("=" * 50)

    try:
        test_health()
        test_verify()
        test_message()
    except requests.exceptions.ConnectionError:
        print("\n❌ Não conseguiu conectar ao servidor")
        print("Certifique-se de que está rodando: python main.py")
    except Exception as e:
        print(f"\n❌ Erro: {str(e)}")

    print("\n" + "=" * 50)
