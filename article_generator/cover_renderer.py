import asyncio
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

TEMPLATES_DIR = Path(__file__).parent / "templates"
_jinja = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def _get_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


async def _render_cover_async(html: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1200, "height": 627})
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(400)
        await page.screenshot(path=output_path, type="png")
        await browser.close()


def render_article_cover(article_data: dict, output_dir: str,
                         author_name: str, author_handle: str) -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    template = _jinja.get_template("article_cover.html")
    html = template.render(
        headline=article_data.get("headline", article_data.get("topic", "")),
        subheadline=article_data.get("subheadline", ""),
        cover_tag=article_data.get("cover_tag", "AI + .NET"),
        reading_time_min=article_data.get("reading_time_min", 6),
        author_name=author_name,
        author_handle=author_handle,
        author_initials=_get_initials(author_name),
    )

    output_path = os.path.join(output_dir, "article_cover.png")
    asyncio.run(_render_cover_async(html, output_path))
    return output_path
