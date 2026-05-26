import asyncio
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

INFOGRAPHIC_FORMATS = [
    {"template": "infographic_vertical.html",  "width": 1080, "height": 1920, "suffix": "vertical"},
    {"template": "infographic_square.html",     "width": 1080, "height": 1080, "suffix": "square"},
    {"template": "infographic_wide.html",       "width": 1200, "height": 627,  "suffix": "wide"},
]


def _get_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


async def _render_async(html: str, width: int, height: int, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": width, "height": height})
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(400)
        await page.screenshot(path=output_path, type="png")
        await browser.close()


def render_infographics(data: dict, output_dir: str,
                        author_name: str, author_handle: str) -> list:
    """Render 3 format variations. Returns list of paths."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    context = dict(
        title=data.get("title", ""),
        subtitle=data.get("subtitle", ""),
        cover_tag=data.get("cover_tag", "AI + .NET"),
        blocks=data.get("blocks", []),
        tip=data.get("tip", ""),
        footer_cta=data.get("footer_cta", ""),
        author_name=author_name,
        author_handle=author_handle,
        author_initials=_get_initials(author_name),
    )

    paths = []
    for fmt in INFOGRAPHIC_FORMATS:
        html = _jinja.get_template(fmt["template"]).render(**context)
        out = os.path.join(output_dir, f"infographic_{fmt['suffix']}.png")
        asyncio.run(_render_async(html, fmt["width"], fmt["height"], out))
        paths.append(out)

    return paths
