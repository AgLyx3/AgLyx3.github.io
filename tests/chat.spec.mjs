import { test, expect } from '@playwright/test';

// Wait helper: waits for chatSend to go disabled then enabled (full request cycle)
async function waitForResponse(page, timeout = 30_000) {
  await page.waitForFunction(() => document.getElementById('chatSend').disabled, { timeout: 5_000 });
  await page.waitForFunction(() => !document.getElementById('chatSend').disabled, { timeout });
}

test.describe('portfolio chat', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Wait for bubble graph to load (confirms /graph succeeded)
    await page.waitForSelector('.bubble-node', { timeout: 15_000 });
  });

  test('landing page loads and bubbles render', async ({ page }) => {
    await expect(page.locator('.landing-name')).toBeVisible();
    await expect(page.locator('.bubble-node').first()).toBeVisible();
  });

  test('chat responds without load-fail errors', async ({ page }) => {
    const input = page.locator('.landing-input');
    await input.fill('what does yixin work on?');
    await input.press('Enter');

    await expect(page.locator('body')).toHaveClass(/state-chat/, { timeout: 5_000 });
    await waitForResponse(page);

    const assistantMsg = page.locator('.message-assistant').first();
    const text = await assistantMsg.innerText();
    expect(text).not.toContain('load fail');
    expect(text).not.toContain('Load fail');
    expect(text.length).toBeGreaterThan(20);
  });

  test('response contains bold formatting', async ({ page }) => {
    await page.locator('.landing-input').fill("what's yixin's current role?");
    await page.locator('.landing-input').press('Enter');

    await expect(page.locator('body')).toHaveClass(/state-chat/, { timeout: 5_000 });
    await waitForResponse(page);

    const html = await page.locator('.message-assistant .msg-text').first().innerHTML();
    expect(html).toContain('<strong>');
  });

  test('follow-up question works in same session', async ({ page }) => {
    const input = page.locator('.landing-input');
    await input.fill('tell me about her AI work');
    await input.press('Enter');

    await expect(page.locator('body')).toHaveClass(/state-chat/, { timeout: 5_000 });
    await waitForResponse(page, 25_000);

    // Ask a follow-up via the composer
    const composer = page.locator('.composer-input');
    await composer.fill("what's her current role?");
    await composer.press('Enter');

    // Second assistant response should appear
    await expect(page.locator('.message-assistant')).toHaveCount(2, { timeout: 40_000 });
  });
});
