import os
from pathlib import Path

from playwright.sync_api import sync_playwright


errors = []
failed_requests = []
api_results = {}
screenshot = Path(__file__).with_name("remote-smoke-83.png")
username = os.environ.get("RESONA_WEB_USER")
password = os.environ.get("RESONA_WEB_PASSWORD")
if not username or not password:
    raise SystemExit("Set RESONA_WEB_USER and RESONA_WEB_PASSWORD before running")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        headless=True,
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )
    context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
    page = context.new_page()
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("requestfailed", lambda request: failed_requests.append(f"{request.method} {request.url}"))

    def capture(response):
        for key in ("/resona/user/login", "/resona/emotion/history", "/resona/emotion/stats", "/resona/agent/list"):
            if key in response.url:
                api_results[key] = response.status

    page.on("response", capture)
    page.goto("http://182.92.71.153/resona/", wait_until="networkidle", timeout=60_000)
    assert page.url.startswith("https://sievox.cn/resona/"), page.url
    page.get_by_placeholder("请输入用户名").fill(username)
    page.get_by_placeholder("请输入密码").fill(password)
    page.locator(".login-btn").click()
    page.wait_for_url("**/resona/home", timeout=30_000)
    page.goto("https://sievox.cn/resona/emotion-history", wait_until="domcontentloaded", timeout=60_000)
    page.get_by_text("情绪历史查询", exact=True).wait_for(timeout=30_000)
    page.locator(".emotion-page").evaluate(
        "element => { element.__vue__.dateRange = ['2026-07-15', '2026-07-15']; element.__vue__.doQuery(); }"
    )
    page.locator(".stat-lbl", has_text="总记录数").wait_for(timeout=30_000)
    page.wait_for_function("document.querySelector('.stat-num')?.textContent.trim() === '1205'", timeout=30_000)
    assert page.get_by_text("原始记录", exact=True).is_visible()
    page.screenshot(path=str(screenshot), full_page=True)
    print({
        "final_url": page.url,
        "title": page.title(),
        "total": page.locator(".stat-num").first.text_content().strip(),
        "api_results": api_results,
        "failed_requests": failed_requests,
        "console_errors": errors,
        "screenshot": str(screenshot),
    })
    browser.close()
