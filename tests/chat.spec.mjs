import { test, expect } from '@playwright/test';

// Wait helper: waits for chatSend to go disabled then enabled (full request cycle)
async function waitForResponse(page, timeout = 30_000) {
  await page.waitForFunction(() => document.getElementById('chatSend').disabled, { timeout: 5_000 });
  await page.waitForFunction(() => !document.getElementById('chatSend').disabled, { timeout });
}

test.describe('portfolio chat', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat.html');
    // Wait for bubble graph to load (confirms /graph succeeded)
    await page.waitForSelector('.bubble-node', { timeout: 15_000 });
  });

  test('landing page loads and bubbles render', async ({ page }) => {
    await expect(page.locator('.landing-name')).toBeVisible();
    await expect(page.locator('.landing-tagline')).toHaveCount(0);
    await expect(page.locator('.bubble-node').first()).toBeVisible();
  });

  test('bubble design preview switches styles without rebuilding the graph', async ({ page }) => {
    await page.goto('/chat.html?bubblePreview=1');
    await page.waitForSelector('.bubble-node', { timeout: 15_000 });

    const firstNode = page.locator('.bubble-node').first();
    await firstNode.evaluate((node) => { node.dataset.previewIdentity = 'kept'; });
    const switcher = page.locator('#bubblePreviewSwitcher');
    await expect(switcher).toBeVisible();

    for (const style of ['dither', 'stepped', 'constellation', 'original']) {
      await switcher.locator(`[data-bubble-style="${style}"]`).click();
      await expect(page.locator('body')).toHaveAttribute('data-bubble-style', style);
      await expect(firstNode.locator(`.bubble-style-${style}`)).toHaveCSS('display', 'block');
      if (style === 'constellation') {
        await expect(firstNode.locator('tspan').first()).toHaveCSS('fill', 'rgb(234, 235, 246)');
      }
    }

    await expect(firstNode).toHaveAttribute('data-preview-identity', 'kept');
  });

  test('cluster preview keeps mobile topics clear of fixed interface regions', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true,
    });
    const page = await context.newPage();
    await page.goto('/chat.html?bubblePreview=1&bubbleStyle=constellation');
    await page.waitForSelector('.bubble-node', { timeout: 15_000 });
    await page.waitForTimeout(400);

    const switcherBox = await page.locator('#bubblePreviewSwitcher').boundingBox();
    const footerBox = await page.locator('.landing-foot').boundingBox();
    const topicBoxes = await page.locator('.bubble-node').evaluateAll((nodes) => nodes.map((node) => {
      const box = node.getBoundingClientRect();
      return { top: box.top, bottom: box.bottom };
    }));
    expect(Math.min(...topicBoxes.map((box) => box.top))).toBeGreaterThan(switcherBox.y + switcherBox.height);
    expect(Math.max(...topicBoxes.map((box) => box.bottom))).toBeLessThan(footerBox.y);

    await context.close();
  });

  test('cluster topics remain clear of the desktop prompt bar', async ({ page }) => {
    await page.goto('/chat.html?bubblePreview=1&bubbleStyle=constellation');
    await page.waitForSelector('.bubble-node', { timeout: 15_000 });
    await page.waitForTimeout(600);

    const formBox = await page.locator('.landing-form').boundingBox();
    const topicBoxes = await page.locator('.bubble-node').evaluateAll((nodes) => nodes.map((node) => {
      const box = node.getBoundingClientRect();
      return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
    }));
    for (const box of topicBoxes) {
      const clearsForm = box.right < formBox.x - 12 ||
        box.left > formBox.x + formBox.width + 12 ||
        box.bottom < formBox.y - 12 ||
        box.top > formBox.y + formBox.height + 12;
      expect(clearsForm).toBe(true);
    }
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
