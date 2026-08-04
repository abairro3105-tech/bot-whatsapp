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
O marcador exato [HUMANO] no final da sua resposta aciona o alerta para a equipe.
O cliente NÃO vê esse marcador. Existem DUAS regras diferentes, dependendo do assunto:

▶ ASSUNTOS DE SAC (reclamação, problema com pedido/entrega, troca, defeito,
dúvida sobre pedido já feito, insatisfação):
- Encaminhe RÁPIDO: colha apenas o essencial em 1-2 perguntas (o que aconteceu
  e número do pedido, se houver) e já finalize com [HUMANO].
- Não faça o cliente insatisfeito esperar preenchendo formulário.

▶ ASSUNTOS COMERCIAIS (quer revender, atacado, marca própria, parceria,
orçamento, fabricação, distribuição, "falar com o comercial"):
- Antes de encaminhar, você DEVE coletar TODAS estas informações obrigatórias,
  perguntando de forma natural e simpática (uma ou duas por vez, nunca todas juntas):
  1. Já possui CNPJ? Qual?
  2. Qual é o assunto que deseja tratar com o Comercial?
  3. Já possui marca registrada? Qual?
  4. Já trabalha com produtos de marca própria? Quais?
  5. Quais são os canais de venda atuais? (loja física, e-commerce, marketplace,
     redes sociais, revenda, etc)
- REGRA RÍGIDA: NÃO use o marcador [HUMANO] enquanto faltar qualquer resposta.
  Se o cliente pular uma pergunta, retome com educação: explique que essas
  informações são necessárias para direcionar ao especialista certo.
- Se o cliente disser que NÃO tem (ex: não tem CNPJ), isso CONTA como resposta
  válida — registre "não possui" e siga para a próxima.
- Quando tiver TODAS as respostas, confirme com o cliente um resuminho dos dados,
  agradeça, avise que a equipe comercial entrará em contato, e SÓ ENTÃO
  finalize com [HUMANO]."""

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

    def get_transcript(self, phone_number, max_messages=10):
        """
        Retorna as últimas mensagens da conversa em formato legível,
        para incluir no e-mail de alerta da equipe.
        """
        if phone_number not in self.conversations:
            return None

        history = self.conversations[phone_number][-max_messages:]
        lines = []
        for msg in history:
            who = "Cliente" if msg["role"] == "user" else "Bot"
            lines.append(f"[{who}]: {msg['content']}")
        return "\n".join(lines) if lines else None

    def summarize_conversation(self, phone_number):
        """
        Usa o Claude para gerar um resumo curto do que o cliente deseja.
        Usado no e-mail de alerta para a equipe de atendimento humano.
        """
        transcript = self.get_transcript(phone_number, max_messages=20)
        if not transcript:
            return None

        try:
            model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
            response = self.client.messages.create(
                model=model,
                max_tokens=200,
                system=(
                    "Você resume conversas de atendimento para a equipe do Grupo Inova Cosmética. "
                    "Escreva em português, direto ao ponto, sem saudações.\n\n"
                    "Se for assunto COMERCIAL, formate assim:\n"
                    "TIPO: Comercial\n"
                    "ASSUNTO: (o que o cliente quer tratar)\n"
                    "CNPJ: (número informado ou 'não possui')\n"
                    "MARCA REGISTRADA: (qual ou 'não possui')\n"
                    "MARCA PRÓPRIA: (quais produtos ou 'não trabalha')\n"
                    "CANAIS DE VENDA: (os que ele citou)\n"
                    "OBSERVAÇÕES: (qualquer outro dado útil: quantidades, urgência, cidade)\n\n"
                    "Se for assunto de SAC, formate assim:\n"
                    "TIPO: SAC\n"
                    "PROBLEMA: (o que aconteceu)\n"
                    "PEDIDO: (número, se informado)\n"
                    "OBSERVAÇÕES: (dados úteis: produto, urgência, tom do cliente)"
                ),
                messages=[{
                    "role": "user",
                    "content": f"Resuma esta conversa para a equipe de atendimento:\n\n{transcript}"
                }]
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Erro ao resumir conversa: {str(e)}")
            return None

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
