"""
dotnet-bot — Pipeline principal
Uso:
  python orchestrator.py           # interativo: abre preview, pede ENTER para publicar
  python orchestrator.py --auto    # automatico: abre preview e publica sem confirmacao
"""

import os
import sys
import argparse
from datetime import date
from dotenv import load_dotenv

load_dotenv(override=True)

from content_generator.generator  import get_next_topic, generate_carousel, mark_topic_used
from carousel_generator.renderer  import render_carousel, open_preview
from linkedin_publisher.auth      import refresh_token_if_needed
from linkedin_publisher.publisher import publish_carousel

AUTHOR_NAME   = os.getenv("LINKEDIN_DISPLAY_NAME", "Fernando Parmezani")
AUTHOR_HANDLE = os.getenv("LINKEDIN_HANDLE",       "@fparmezani")
OUTPUT_BASE   = os.path.join(os.path.dirname(__file__), "output")


def _separator(char="-", width=52):
    print(char * width)


def run(auto: bool = False):
    today      = date.today().isoformat()
    output_dir = os.path.join(OUTPUT_BASE, today)

    _separator("=")
    print(f"  dotnet-bot  |  {today}")
    _separator("=")

    # 0. Refresh token proactively (no-op if no refresh token)
    refresh_token_if_needed()

    # 1. Pick topic
    topic_obj = get_next_topic()
    topic     = topic_obj["topic"]
    print(f"\n  Topic: {topic}\n")
    _separator()

    # 2. Generate content (PT + EN)
    print("[1/4] Generating content with Claude...")
    print("  PT-BR...", end=" ", flush=True)
    data_pt = generate_carousel(topic, "pt")
    print("done")

    print("  EN...  ", end=" ", flush=True)
    data_en = generate_carousel(topic, "en")
    print("done")

    # 3. Render slides
    _separator()
    print("[2/4] Rendering slides with Playwright...")
    print("  PT-BR...", end=" ", flush=True)
    png_pt, pdf_pt = render_carousel(
        data_pt, "pt",
        os.path.join(output_dir, "pt"),
        AUTHOR_NAME, AUTHOR_HANDLE,
    )
    print(f"done  ({len(png_pt)} slides)")

    print("  EN...  ", end=" ", flush=True)
    png_en, pdf_en = render_carousel(
        data_en, "en",
        os.path.join(output_dir, "en"),
        AUTHOR_NAME, AUTHOR_HANDLE,
    )
    print(f"done  ({len(png_en)} slides)")

    # 4. Preview
    _separator()
    print("[3/4] Opening preview in browser...")
    open_preview(
        topic        = topic,
        png_paths_pt = png_pt,
        post_text_pt = data_pt["post_text"],
        png_paths_en = png_en,
        post_text_en = data_en["post_text"],
        output_dir   = output_dir,
    )

    if auto:
        print("\n  Modo automatico: publicando em 10 segundos...")
        print("  (Feche o terminal ou pressione Ctrl+C para cancelar)\n")
        import time
        try:
            for i in range(10, 0, -1):
                print(f"  {i}...", end=" ", flush=True)
                time.sleep(1)
            print()
        except KeyboardInterrupt:
            print("\n\n  Cancelado. Nada foi publicado.\n")
            sys.exit(0)
    else:
        print("\n  Revise os slides no browser.")
        print("  Pressione ENTER para publicar ou Ctrl+C para cancelar.\n")
        try:
            input("  > ")
        except KeyboardInterrupt:
            print("\n\n  Cancelado. Nada foi publicado.\n")
            sys.exit(0)

    # 5. Publish
    _separator()
    print("[4/4] Publishing to LinkedIn...")

    print("\n  [PT-BR]")
    title_pt = data_pt["slides"][0]["title"]
    id_pt    = publish_carousel(png_pt, data_pt["post_text"], title_pt)
    print(f"    Post ID: {id_pt}")

    print("\n  [EN]")
    title_en = data_en["slides"][0]["title"]
    id_en    = publish_carousel(png_en, data_en["post_text"], title_en)
    print(f"    Post ID: {id_en}")

    # 6. Mark topic done
    mark_topic_used(topic_obj["id"])

    _separator("=")
    print(f"  Done! Topic '{topic}' marked as used.")
    print(f"  Output saved to: output/{today}/")
    _separator("=")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", action="store_true", help="Publica sem pedir confirmacao")
    args = parser.parse_args()
    run(auto=args.auto)
