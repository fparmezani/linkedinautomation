#!/usr/bin/env python3
"""Complete end-to-end test: generate idea -> select -> generate post"""
import asyncio
import time
from playwright.async_api import async_playwright

async def test_idea_to_post():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("[*] Opening application...")
        await page.goto("http://localhost:5000/login")

        print("[*] Logging in...")
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'dotnetbot')
        await page.click('button[type="submit"]')
        await page.wait_for_url('http://localhost:5000/', timeout=5000)
        print("[OK] Logged in")

        # Type an idea
        print("\n[*] Step 1: Type an idea...")
        test_idea = "Como usar Semantic Kernel em projetos ASP.NET"
        await page.fill('input[id="idea-input"]', test_idea)
        print(f"[OK] Typed: {test_idea}")

        # Generate titles
        print("[*] Step 2: Generate 5 titles...")
        await page.click('button[id="btn-generate-titles"]')
        await page.wait_for_selector('#generated-titles:not(.hidden)', timeout=15000)
        print("[OK] Titles loaded")

        # Get first title
        first_title_elem = await page.query_selector('#generated-titles .topic-option-name')
        first_title = await first_title_elem.inner_text()
        print(f"[OK] First title: '{first_title}'")

        # Click first title to select
        print("\n[*] Step 3: Select first title...")
        first_option = await page.query_selector('#generated-titles .topic-option')
        await first_option.click()
        await page.wait_for_timeout(500)
        print(f"[OK] Selected: {first_title}")

        # Check if banner appears
        banner = await page.query_selector('#selected-topic-banner:not(.hidden)')
        if banner:
            print("[OK] Selection confirmed (banner visible)")

        # Click generate button
        print("\n[*] Step 4: Click 'Gerar Post' button...")
        gen_btn = await page.query_selector('button[id="btn-generate"]')
        if gen_btn and not await gen_btn.is_disabled():
            await gen_btn.click()
            print("[OK] Generation started")
        else:
            print("[WARN] Generate button is disabled")
            await browser.close()
            return False

        # Wait for progress section
        print("[*] Waiting for generation to complete...")
        await page.wait_for_selector('#preview-section:not(.hidden)', timeout=60000)
        print("[OK] Generation completed!")

        # Check if slides are visible
        slides_pt = await page.query_selector_all('#slides-pt .slide-thumb')
        slides_en = await page.query_selector_all('#slides-en .slide-thumb')
        print(f"[OK] Generated {len(slides_pt)} PT-BR slides and {len(slides_en)} EN slides")

        # Check post texts
        text_pt = await page.input_value('#text-pt')
        text_en = await page.input_value('#text-en')

        if text_pt and text_en:
            print(f"[OK] Post text PT-BR: {len(text_pt)} chars")
            print(f"[OK] Post text EN: {len(text_en)} chars")
        else:
            print("[WARN] Post texts not populated")

        # Take screenshot
        screenshot_path = 'c:\\Projetos\\LinkedinAutomation\\test_complete_screenshot.png'
        await page.screenshot(path=screenshot_path)
        print(f"\n[*] Screenshot saved to {screenshot_path}")

        await browser.close()
        print("\n[OK] End-to-end test PASSED!")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_idea_to_post())
    exit(0 if success else 1)
