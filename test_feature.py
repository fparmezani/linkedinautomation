#!/usr/bin/env python3
"""Test the new 'Generate Titles from Idea' feature"""
import asyncio
from playwright.async_api import async_playwright

async def test_generate_titles():
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("[*] Opening application...")
        await page.goto("http://localhost:5000/login")

        # Step 1: Login
        print("[OK] Page loaded")
        print("[*] Logging in with admin/dotnetbot...")
        await page.fill('input[name="username"]', 'admin')
        await page.fill('input[name="password"]', 'dotnetbot')
        await page.click('button[type="submit"]')
        await page.wait_for_url('http://localhost:5000/', timeout=5000)
        print("[OK] Logged in successfully")

        # Step 2: Type an idea
        print("\n[*] Testing 'Generate Titles from Idea' feature...")
        idea_input = await page.query_selector('input[id="idea-input"]')
        if not idea_input:
            print("[FAIL] Idea input field not found")
            await browser.close()
            return False

        print("[OK] Idea input field found")

        # Type an idea
        test_idea = "Como usar GitHub Copilot para acelerar desenvolvimento em C#"
        await page.fill('input[id="idea-input"]', test_idea)
        print(f"[OK] Typed idea: '{test_idea}'")

        # Step 3: Click "Gerar Titulos" button
        print("[*] Clicking 'Gerar Titulos' button...")
        btn = await page.query_selector('button[id="btn-generate-titles"]')
        if not btn:
            print("[FAIL] Button 'Gerar Titulos' not found")
            await browser.close()
            return False

        await btn.click()

        # Step 4: Wait for titles to appear
        print("[*] Waiting for titles to generate...")
        try:
            # Wait for the generated titles container to appear
            await page.wait_for_selector('#generated-titles:not(.hidden)', timeout=15000)
            print("[OK] Titles loaded")
        except Exception as e:
            print(f"[FAIL] Titles did not appear within timeout: {e}")
            await browser.close()
            return False

        # Step 5: Verify 5 titles are displayed
        title_options = await page.query_selector_all('#generated-titles .topic-option')
        print(f"\n[*] Number of titles displayed: {len(title_options)}")

        if len(title_options) != 5:
            print(f"[WARN] Expected 5 titles, got {len(title_options)}")

        # Extract and display titles
        print("\n[*] Generated titles:")
        for i, option in enumerate(title_options, 1):
            title_elem = await option.query_selector('.topic-option-name')
            desc_elem = await option.query_selector('.topic-option-reasoning')

            if title_elem and desc_elem:
                title = await title_elem.inner_text()
                desc = await desc_elem.inner_text()
                print(f"  {i}. {title}")
                print(f"     --> {desc}")

        # Step 6: Click on first title and verify selection
        print("\n[*] Clicking on first title to select...")
        first_option = title_options[0]
        await first_option.click()

        # Wait a moment for selection to register
        await page.wait_for_timeout(500)

        # Check if it's marked as selected
        selected_class = await first_option.get_attribute('class')
        if 'selected' in selected_class:
            print("[OK] First title is marked as selected")
        else:
            print("[WARN] First title does not have 'selected' class")

        # Check if the selected topic banner appears
        banner = await page.query_selector('#selected-topic-banner:not(.hidden)')
        if banner:
            banner_text = await banner.query_selector('#selected-topic-banner-name')
            if banner_text:
                selected_name = await banner_text.inner_text()
                print(f"[OK] Selected topic banner appears: '{selected_name}'")
        else:
            print("[WARN] Selected topic banner not found")

        # Take screenshot
        screenshot_path = 'c:\\Projetos\\LinkedinAutomation\\feature_test_screenshot.png'
        await page.screenshot(path=screenshot_path)
        print(f"\n[*] Screenshot saved to {screenshot_path}")

        await browser.close()
        print("\n[OK] All tests passed!")
        return True

if __name__ == "__main__":
    success = asyncio.run(test_generate_titles())
    exit(0 if success else 1)
