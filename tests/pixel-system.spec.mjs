import { test, expect } from '@playwright/test';

test.describe('site-wide pixel system', () => {
  test('homepage keeps the pixel atmosphere behind the existing portrait interaction', async ({ page }) => {
    await page.goto('/index.html');
    await expect(page.locator('.pixel-cluster')).toHaveCount(4);
    await expect(page.locator('.pixel-cell').first()).toBeVisible();

    const name = page.locator('.name-trigger');
    const portraits = page.locator('.name-portrait');
    await name.hover();
    await expect(portraits.first().locator('img')).toHaveCSS('opacity', '1');

    const nameBox = await name.boundingBox();
    const portraitTops = await portraits.evaluateAll((nodes) => nodes.map((node) => (
      node.getBoundingClientRect().top
    )));
    expect(Math.min(...portraitTops)).toBeGreaterThanOrEqual(nameBox.y + nameBox.height);
  });

  test('portfolio uses crisp project surfaces and filtering still works', async ({ page }) => {
    await page.goto('/portfolio.html');
    await expect(page.locator('.pixel-cluster')).toHaveCount(4);
    await expect(page.locator('.card').first()).toHaveCSS('border-radius', '0px');

    await page.locator('[data-filter="dev-tool"]').click();
    await expect(page.locator('.card:not([hidden])')).toHaveCount(4);
    await expect(page.locator('[data-filter="dev-tool"]')).toHaveAttribute('aria-pressed', 'true');
  });

  test('chat defaults to the ambient Cluster style with a clear prompt bar', async ({ page }) => {
    await page.goto('/chat.html');
    await page.waitForSelector('.bubble-node', { timeout: 15_000 });
    await expect(page.locator('body')).toHaveAttribute('data-bubble-style', 'constellation');
    await expect(page.locator('#bubblePreviewSwitcher')).toBeHidden();
    await expect(page.locator('.landing-tagline')).toHaveCount(0);

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

  test('all pages fit a mobile viewport without horizontal overflow', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true,
    });
    const page = await context.newPage();

    for (const path of ['/index.html', '/portfolio.html', '/chat.html']) {
      await page.goto(path);
      if (path.endsWith('chat.html')) await page.waitForSelector('.bubble-node', { timeout: 15_000 });
      const sizes = await page.evaluate(() => ({
        client: document.documentElement.clientWidth,
        scroll: document.documentElement.scrollWidth,
      }));
      expect(sizes.scroll).toBeLessThanOrEqual(sizes.client);
    }

    await context.close();
  });
});
