import { test, expect } from '@playwright/test';

test.describe('landing portrait reveal', () => {
  test('portrait comes forward from the name and leaves the layout fixed', async ({ page }) => {
    await page.goto('/');

    const name = page.locator('.name-trigger');
    const portrait = page.locator('.name-portrait');
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
    await expect(portrait).toHaveCSS('opacity', '1');
    await expect(portrait).toHaveCSS('border-width', '0px');
    await expect.poll(() => layerOpacity(portrait, '::before')).toBe('0.24');
    await expect(portrait.locator('img')).toHaveCSS('opacity', '0');

    await name.hover();
    await expect(portrait).toHaveCSS('opacity', '1');
    await expect.poll(() => layerOpacity(portrait, '::before')).toBe('0');
    await expect(portrait.locator('img')).toHaveCSS('opacity', '1');
    expect(await portrait.evaluate((node) => getComputedStyle(node).boxShadow))
      .toContain('rgba(216, 224, 236, 0.72)');
    await expect(portrait.locator('img')).toHaveJSProperty('complete', true);
    expect(await layoutBox(ways)).toEqual(waysBefore);

    await page.mouse.move(0, 0);
    await expect.poll(() => layerOpacity(portrait, '::before')).toBe('0.24');
    await expect(portrait.locator('img')).toHaveCSS('opacity', '0');
  });

  test('hovering the resting portrait brings it forward', async ({ page }) => {
    await page.goto('/');

    const portrait = page.locator('.name-portrait');
    await portrait.hover();
    await expect(portrait).toHaveCSS('opacity', '1');
    await expect(portrait).toHaveCSS('z-index', '5');
  });

  test('keyboard focus also reveals the portrait', async ({ page }) => {
    await page.goto('/');

    await page.locator('.name-trigger').focus();
    await expect(page.locator('.name-portrait')).toHaveCSS('opacity', '1');
  });
});
