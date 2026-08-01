"""
Handler para integração com Claude API
Gerencia contexto de conversa e gera respostas
"""

import os
import json
import logging
from anthropic import Anthropic
from datetime import datetime

logger = logging.getLogger(__name__)


class ClaudeHandler:
    """Gerencia conversas com Claude e mantém histórico"""

    def __init__(self, api_key=None, max_history=10):
        """
        Inicializa handler Claude

        Args:
            api_key: Chave da API Anthropic (ou usa env var)
            max_history: Número máximo de mensagens no histórico
        """
        self.api_key = api_key or os.getenv("CLAUDE_API_KEY")
        self.client = Anthropic(api_key=self.api_key)
        self.max_history = max_history

        # Armazenar histórico de conversas por telefone
        # Estrutura: {phone_number: [{"role": "user"/"assistant", "content": "..."}, ...]}
        self.conversations = {}

        # Sistema prompt - defina o comportamento do bot aqui
        self.system_prompt = """Você é o assistente virtual do Grupo Inova Cosmética no WhatsApp.

INSTRUÇÕES:
- Responda de forma breve, calorosa e profissional (máximo 3-4 frases)
- Use linguagem natural e amigável, com 1 emoji por mensagem
- Se não souber responder, seja honesto e diga que vai encaminhar para a equipe
- Máximo 1024 caracteres por resposta

CONTEXTO:
- Empresa: Grupo Inova Cosmética (produtos cosméticos)
- Você atende clientes: dúvidas sobre produtos, pedidos, preços e atendimento geral
- Trate o cliente com respeito e ofereça soluções práticas
- Para assuntos que exigem um humano (reclamações graves, negociações), avise que a equipe entrará em contato

ENCAMINHAMENTO PARA HUMANO:
Se o cliente precisar de atendimento humano — reclamação séria, negociação de preços/prazos,
pedido explícito para falar com atendente/pessoa, assunto que você não consegue resolver —
termine sua resposta com o marcador exato [HUMANO] no final.
O cliente NÃO verá esse marcador; ele serve apenas para o sistema avisar a equipe.
Use o marcador apenas quando realmente necessário."""

    def get_response(self, user_message, phone_number=None, model=None):
        model = model or os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
        """
        Gera resposta para uma mensagem do usuário

        Args:
            user_message: Texto da mensagem do usuário
            phone_number: Número do telefone (para manter histórico)
            model: Modelo Claude a usar

        Returns:
            str: Resposta gerada pelo Claude
        """
        try:
            # Usar phone_number como ID de conversa
            if not phone_number:
                phone_number = "default"

            # Obter histórico da conversa
            if phone_number not in self.conversations:
                self.conversations[phone_number] = []

            conversation_history = self.conversations[phone_number]

            # Adicionar mensagem do usuário ao histórico
            conversation_history.append({
                "role": "user",
                "content": user_message
            })

            # Manter apenas últimas N mensagens
            if len(conversation_history) > self.max_history:
                conversation_history = conversation_history[-self.max_history:]

            logger.info(f"📞 Conversa com {phone_number}: {len(conversation_history)} mensagens")

            # Chamar Claude API
            response = self.client.messages.create(
                model=model,
                max_tokens=1024,
                system=self.system_prompt,
                messages=conversation_history
            )

            # Extrair resposta
            assistant_message = response.content[0].text

            # Adicionar resposta ao histórico
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            logger.info(f"✅ Resposta gerada para {phone_number}")
            return assistant_message

        except Exception as e:
            logger.error(f"❌ Erro ao gerar resposta com Claude: {str(e)}", exc_info=True)
            return "Desculpe, tive um problema ao processar sua mensagem. Por favor, tente novamente."

    def clear_conversation(self, phone_number):
        """Limpar histórico de conversa (opcional)"""
        if phone_number in self.conversations:
            del self.conversations[phone_number]
            logger.info(f"🗑️  Histórico limpo para {phone_number}")

    def get_conversation_summary(self, phone_number):
        """Obter resumo da conversa (para debug)"""
        if phone_number not in self.conversations:
            return None

        conv = self.conversations[phone_number]
        return {
            "phone": phone_number,
            "message_count": len(conv),
            "messages": conv
        }


class ConversationMemory:
    """
    Alternativa: Armazenar histórico em arquivo JSON
    Útil se quiser persistência entre reinicializações
    """

    def __init__(self, storage_dir="./conversation_data"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def get_history(self, phone_number):
        """Carregar histórico do arquivo"""
        file_path = os.path.join(self.storage_dir, f"{phone_number}.json")

        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []

    def save_history(self, phone_number, history):
        """Salvar histórico em arquivo"""
        file_path = os.path.join(self.storage_dir, f"{phone_number}.json")

        with open(file_path, 'w') as f:
            json.dump(history, f, indent=2)

    def clear_history(self, phone_number):
        """Deletar histórico"""
        file_path = os.path.join(self.storage_dir, f"{phone_number}.json")

        if os.path.exists(file_path):
            os.remove(file_path)
