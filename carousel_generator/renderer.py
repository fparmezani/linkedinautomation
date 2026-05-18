import asyncio
import os
import webbrowser
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from PIL import Image

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_jinja = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)


async def _render_slides(slides_html: list, output_dir: str) -> list:
    paths = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1080, "height": 1080})
        for i, html in enumerate(slides_html):
            path = os.path.join(output_dir, f"slide_{i+1:02d}.png")
            await page.set_content(html, wait_until="networkidle")
            await page.wait_for_timeout(400)
            await page.screenshot(path=path, type="png")
            paths.append(path)
        await browser.close()
    return paths


def _build_slides_html(carousel_data: dict, author_name: str, author_handle: str, template_name: str = "slide.html") -> list:
    template = _jinja.get_template(template_name)
    slides = carousel_data["slides"]
    total = len(slides)
    result = []
    for i, slide in enumerate(slides):
        slide["slide_num"] = i + 1
        slide["total_slides"] = total
        result.append(template.render(
            slide=slide,
            author_name=author_name,
            author_handle=author_handle,
        ))
    return result


def _create_pdf(png_paths: list, output_path: str):
    images = [Image.open(p).convert("RGB") for p in png_paths]
    images[0].save(output_path, "PDF", save_all=True, append_images=images[1:])


def render_carousel(carousel_data: dict, lang: str, output_dir: str,
                    author_name: str, author_handle: str, template: str = "slide.html") -> tuple:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    slides_html = _build_slides_html(carousel_data, author_name, author_handle, template_name=template)
    png_paths = asyncio.run(_render_slides(slides_html, output_dir))
    pdf_path = os.path.join(output_dir, f"carousel_{lang}.pdf")
    _create_pdf(png_paths, pdf_path)
    return png_paths, pdf_path


def open_preview(topic: str,
                 png_paths_pt: list, post_text_pt: str,
                 png_paths_en: list, post_text_en: str,
                 output_dir: str) -> str:
    template = _jinja.get_template("preview.html")
    imgs_pt = [Path(p).as_uri() for p in png_paths_pt]
    imgs_en = [Path(p).as_uri() for p in png_paths_en]
    html = template.render(
        topic=topic,
        slides_pt=imgs_pt,
        post_text_pt=post_text_pt,
        slides_en=imgs_en,
        post_text_en=post_text_en,
    )
    preview_path = os.path.join(output_dir, "preview.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html)
    webbrowser.open(Path(preview_path).as_uri())
    return preview_path
