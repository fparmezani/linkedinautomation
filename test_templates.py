"""
Script para visualizar os 3 templates lado a lado.
Gera 1 slide de exemplo com cada template para você escolher.
"""

import asyncio
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

# Dados de exemplo
EXAMPLE_SLIDE_COVER = {
    "type": "cover",
    "title": "GitHub Copilot Tips for C# Developers",
    "subtitle": "10 shortcuts that triple your productivity",
    "tag": "AI + .NET"
}

EXAMPLE_SLIDE_CONTENT = {
    "type": "content",
    "title": "Why This Matters Now",
    "points": [
        "GitHub Copilot saves 40% dev time on average",
        "Enterprise teams already using AI assistance",
        "C# has the best Copilot integration in the .NET ecosystem"
    ],
    "code": None
}

EXAMPLE_SLIDE_CODE = {
    "type": "code",
    "title": "Semantic Kernel Example",
    "description": "Building an AI agent in C# with Semantic Kernel",
    "code": """var kernel = new KernelBuilder()
    .WithAzureOpenAITextGenerationService(...)
    .Build();

var result = await kernel.InvokeAsync(
    "GetWeather",
    new ContextVariables("Seattle")
);"""
}

AUTHOR_NAME = "Fernando Parmezani"
AUTHOR_HANDLE = "@fparmezani"

async def render_slide_with_template(slide_data: dict, template_name: str, output_path: str):
    """Renderiza um slide com um template específico."""
    templates_dir = Path(__file__).parent / "carousel_generator" / "templates"
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=True
    )

    template = env.get_template(template_name)

    # Adiciona dados de página
    slide_data["page_num"] = 1
    slide_data["total_pages"] = 6

    html = template.render(
        slide=slide_data,
        author_name=AUTHOR_NAME,
        author_handle=AUTHOR_HANDLE,
        page_num=1,
        total_pages=6
    )

    # Renderiza com Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1080, "height": 1080})
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(300)
        await page.screenshot(path=output_path, type="png")
        await browser.close()

    print(f"[OK] Salvo: {output_path}")


async def main():
    output_dir = Path(__file__).parent / "template_previews"
    output_dir.mkdir(exist_ok=True)

    templates = [
        ("slide.html", "original"),
        ("slide_minimal.html", "minimal"),
        ("slide_card.html", "card"),
    ]

    print("\n[Templates Preview]\n")
    print("Gerando prévias de cada template...")
    print()

    # Gera slide de capa com cada template
    for template_file, template_name in templates:
        output_path = output_dir / f"template_{template_name}_cover.png"
        print(f"Renderizando {template_name} (cover)...", end=" ")
        await render_slide_with_template(EXAMPLE_SLIDE_COVER, template_file, str(output_path))

    # Gera slide de conteúdo com cada template
    for template_file, template_name in templates:
        output_path = output_dir / f"template_{template_name}_content.png"
        print(f"Renderizando {template_name} (content)...", end=" ")
        await render_slide_with_template(EXAMPLE_SLIDE_CONTENT, template_file, str(output_path))

    # Gera slide de código com cada template
    for template_file, template_name in templates:
        output_path = output_dir / f"template_{template_name}_code.png"
        print(f"Renderizando {template_name} (code)...", end=" ")
        await render_slide_with_template(EXAMPLE_SLIDE_CODE, template_file, str(output_path))

    print("\n")
    print("=" * 60)
    print(f"Prévias salvas em: {output_dir}")
    print()
    print("Abra as imagens e escolha qual estilo prefere:")
    print()
    print("1. template_original_*.png   — Original (accent bar + gradiente)")
    print("2. template_minimal_*.png    — Minimalista (linhas + espaço negativo)")
    print("3. template_card_*.png       — Card/Moderno (blocos + borders)")
    print()
    print("Depois, me avise qual escolheu!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
