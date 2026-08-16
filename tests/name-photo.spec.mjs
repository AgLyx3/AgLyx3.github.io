import { test, expect } from '@playwright/test';

test.describe('landing portrait reveal', () => {
  test('portrait comes forward from the name and leaves the layout fixed', async ({ page }) => {
    await page.goto('/');

    const name = page.locator('.name-trigger');
    const portraits = page.locator('.name-portrait');
    const portrait = portraits.first();
    const secondaryPortrait = portraits.last();
    const ways = page.locator('.ways');
    const layerOpacity = (element, layer) => element.evaluate(
      (node, pseudo) => getComputedStyle(node, pseudo).opacity,
      layer,
    );
    const layoutBox = (element) => element.evaluate((node) => ({
      top: node.offsetTop,
      left: node.offsetLeft,
      width: node.offsetWidth,
      height: node.offsetHeight,
    }));
    const waysBefore = await layoutBox(ways);

    await expect(name).toBeVisible();
    await expect(portraits).toHaveCount(2);
    await expect(portrait).toHaveCSS('opacity', '1');
    await expect(portrait).toHaveCSS('border-width', '0px');
    await expect.poll(() => layerOpacity(portrait, '::before')).toBe('0.24');
    await expect.poll(() => layerOpacity(secondaryPortrait, '::before')).toBe('0.28');
    await expect(portrait.locator('img')).toHaveCSS('opacity', '0');

    await name.hover();
    await expect(portrait).toHaveCSS('opacity', '1');
    await expect.poll(() => layerOpacity(portrait, '::before')).toBe('0');
    await expect.poll(() => layerOpacity(secondaryPortrait, '::before')).toBe('0');
    await expect(portrait.locator('img')).toHaveCSS('opacity', '1');
    expect(await portrait.evaluate((node) => getComputedStyle(node).boxShadow))
      .toContain('rgba(216, 224, 236, 0.72)');
    await expect(portrait.locator('img')).toHaveJSProperty('complete', true);
    await expect(portraits.nth(1).locator('img')).toHaveJSProperty('complete', true);
    expect(await layoutBox(ways)).toEqual(waysBefore);

    const waysBox = await ways.boundingBox();
    const portraitBoxes = await portraits.evaluateAll((nodes) => nodes.map((node) => {
      const box = node.getBoundingClientRect();
      return { right: box.right };
    }));
    expect(Math.max(...portraitBoxes.map((box) => box.right))).toBeLessThan(waysBox.x);

    await page.mouse.move(0, 0);
    await expect.poll(() => layerOpacity(portrait, '::before')).toBe('0.24');
    await expect(portrait.locator('img')).toHaveCSS('opacity', '0');
  });

  test('hovering the resting portrait brings it forward', async ({ page }) => {
    await page.goto('/');

    const portrait = page.locator('.name-portrait').last();
    await portrait.hover();
    await expect(portrait).toHaveCSS('opacity', '1');
    await expect(portrait).toHaveCSS('z-index', '6');
  });

  test('keyboard focus also reveals the portrait', async ({ page }) => {
    await page.goto('/');

    await page.locator('.name-trigger').focus();
    await expect(page.locator('.name-portrait').first()).toHaveCSS('opacity', '1');
  });

  test('mobile taps toggle the portrait and blank space dismisses it', async ({ browser }) => {
    const context = await browser.newContext({
      viewport: { width: 390, height: 844 },
      hasTouch: true,
      isMobile: true,
    });
    const page = await context.newPage();
    await page.goto('/');

    const reveal = page.locator('.name-reveal');
    const trigger = page.locator('.name-trigger');
    const portraits = page.locator('.name-portrait');
    const portrait = portraits.last();

    await trigger.tap();
    await expect(reveal).toHaveClass(/is-revealed/);
    await expect(portrait.locator('img')).toHaveCSS('opacity', '1');

    const waysBox = await page.locator('.ways').boundingBox();
    const taglineBox = await page.locator('.tagline').boundingBox();
    const portraitBoxes = await portraits.evaluateAll((nodes) => nodes.map((node) => {
      const box = node.getBoundingClientRect();
      return { bottom: box.bottom };
    }));
    expect(Math.max(...portraitBoxes.map((box) => box.bottom))).toBeLessThan(waysBox.y);
    expect(Math.max(...portraitBoxes.map((box) => box.bottom))).toBeLessThan(taglineBox.y);

    await portrait.tap();
    await expect(reveal).not.toHaveClass(/is-revealed/);
    await expect(portrait.locator('img')).toHaveCSS('opacity', '0');

    await trigger.tap();
    await expect(reveal).toHaveClass(/is-revealed/);
    await page.locator('body').tap({ position: { x: 8, y: 8 } });
    await expect(reveal).not.toHaveClass(/is-revealed/);

    await context.close();
  });
});
