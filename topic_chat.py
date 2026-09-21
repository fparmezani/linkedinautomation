"""
topic_chat.py — Chat interativo sobre um tópico específico de C# .NET + AI.

Uso:
  python topic_chat.py                        # pergunta o tópico interativamente
  python topic_chat.py "Semantic Kernel"      # tópico via argumento
  python topic_chat.py --list                 # lista tópicos da fila
"""

import os
import sys
import json
import argparse
import anthropic
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

SYSTEM_PROMPT = """Você é um especialista em C# .NET e Inteligência Artificial com foco em
ajudar desenvolvedores mid-to-senior a usar ferramentas de AI para escrever melhor código,
ser mais produtivo e construir aplicações inteligentes.

Responda de forma clara e prática, sempre com exemplos de código C# quando relevante.
Use português brasileiro nas respostas, a não ser que o usuário pergunte em inglês.
Quando mostrar código, use blocos markdown com a linguagem correta."""

TOPIC_QUEUE_PATH = Path(__file__).parent / "content_generator" / "topics_queue.json"


def load_all_topics() -> list[dict]:
    if not TOPIC_QUEUE_PATH.exists():
        return []
    data = json.loads(TOPIC_QUEUE_PATH.read_text(encoding="utf-8"))
    queue = data.get("queue", [])
    used  = data.get("used", [])
    return queue + used


def list_topics():
    topics = load_all_topics()
    if not topics:
        print("Nenhum tópico encontrado na fila.")
        return
    data = json.loads(TOPIC_QUEUE_PATH.read_text(encoding="utf-8"))
    queue = data.get("queue", [])
    used  = data.get("used", [])
    print("\n  TÓPICOS NA FILA:")
    for t in queue:
        print(f"    [{t['id']:3d}] {t['topic']}")
    if used:
        print("\n  TÓPICOS JÁ USADOS:")
        for t in used[:5]:
            print(f"    [{t['id']:3d}] {t['topic']}")
        if len(used) > 5:
            print(f"         ... e mais {len(used) - 5}")
    print()


def chat(topic: str):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    history: list[dict] = []

    print(f"\n{'='*56}")
    print(f"  Chat sobre: {topic}")
    print(f"{'='*56}")
    print("  (Digite 'sair' ou pressione Ctrl+C para encerrar)\n")

    # Mensagem inicial contextualizando o tópico
    history.append({
        "role": "user",
        "content": f"Vamos conversar sobre o tópico: \"{topic}\". "
                   "Pode fazer uma introdução rápida sobre esse assunto no contexto de C# .NET?"
    })

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=history,
        )
        reply = response.content[0].text
        history.append({"role": "assistant", "content": reply})

        print(f"Claude: {reply}\n")
        print("-" * 56)

        try:
            user_input = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nEncerrando chat. Até mais!\n")
            break

        if not user_input:
            continue
        if user_input.lower() in {"sair", "exit", "quit", "q"}:
            print("\nEncerrando chat. Até mais!\n")
            break

        history.append({"role": "user", "content": user_input})


def main():
    parser = argparse.ArgumentParser(description="Chat sobre um tópico de C# .NET + AI")
    parser.add_argument("topic", nargs="?", help="Tópico para discutir")
    parser.add_argument("--list", "-l", action="store_true", help="Lista os tópicos disponíveis")
    args = parser.parse_args()

    if args.list:
        list_topics()
        return

    topic = args.topic
    if not topic:
        list_topics()
        topic = input("Digite o tópico (ou pressione ENTER para um da fila): ").strip()
        if not topic:
            topics = load_all_topics()
            if topics:
                topic = topics[0]["topic"]
                print(f"  Usando: {topic}")
            else:
                print("Nenhum tópico disponível.")
                sys.exit(1)

    chat(topic)


if __name__ == "__main__":
    main()
