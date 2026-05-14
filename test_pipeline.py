"""
Testa geracao + renderizacao + preview (sem publicar).
Rode: python test_pipeline.py
"""
import os
import sys
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

# Garante que o .env e carregado do diretorio do projeto
load_dotenv(Path(__file__).parent / ".env", override=True)

from content_generator.generator import get_next_topic, generate_carousel
from carousel_generator.renderer import render_carousel, open_preview

AUTHOR_NAME   = os.getenv("LINKEDIN_DISPLAY_NAME", "Fernando Parmezani")
AUTHOR_HANDLE = os.getenv("LINKEDIN_HANDLE", "@fparmezani")
today         = date.today().isoformat()
output_dir    = os.path.join(os.path.dirname(__file__), "output", today)

topic_obj = get_next_topic()
topic     = topic_obj["topic"]
print(f"\nTopico: {topic}\n")

print("[1/3] Gerando conteudo com Claude...")
print("  PT-BR...", end=" ", flush=True)
data_pt = generate_carousel(topic, "pt")
print("done")

print("  EN...  ", end=" ", flush=True)
data_en = generate_carousel(topic, "en")
print("done")

print("\n[2/3] Renderizando slides...")
print("  PT-BR...", end=" ", flush=True)
png_pt, pdf_pt = render_carousel(
    data_pt, "pt", os.path.join(output_dir, "pt"), AUTHOR_NAME, AUTHOR_HANDLE
)
print(f"done ({len(png_pt)} slides)")

print("  EN...  ", end=" ", flush=True)
png_en, pdf_en = render_carousel(
    data_en, "en", os.path.join(output_dir, "en"), AUTHOR_NAME, AUTHOR_HANDLE
)
print(f"done ({len(png_en)} slides)")

print("\n[3/3] Abrindo preview no browser...")
open_preview(topic, png_pt, data_pt["post_text"], png_en, data_en["post_text"], output_dir)

print("\n" + "="*50)
print("Slides gerados com sucesso!")
print(f"  PDF PT: {pdf_pt}")
print(f"  PDF EN: {pdf_en}")
print("="*50)
print("\nSe os slides estiverem OK, rode:")
print("  python orchestrator.py")
print("para publicar no LinkedIn.\n")
