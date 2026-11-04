import { expect, test } from '@playwright/test';

test.describe('Projects sidebar library navigation', () => {
  test('keeps All projects reachable by keyboard in the sidebar @scenario:projects-permanent-library-keyboard', async ({
    page,
  }) => {
    await page.goto('/c/new', { timeout: 15000 });
    const sidebar = page.locator('aside').first();
    const section = sidebar.getByRole('button', { name: 'Projects', exact: true });
    await expect(section).toBeVisible({ timeout: 15000 });
    if ((await section.getAttribute('aria-expanded')) !== 'true') {
      await section.click();
    }
    await expect(section).toHaveAttribute('aria-expanded', 'true');

    // The header offers a compact action and the expanded body offers a
    // persistent library row. The latter must not depend on page cursors.
    const library = sidebar.getByRole('button', { name: 'All projects', exact: true }).last();
    await expect(library).toBeVisible();
    await expect(library).not.toHaveAttribute('aria-current', 'page');
    await library.focus();
    await expect(library).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/projects(?:\/|$)/);
  });
});
