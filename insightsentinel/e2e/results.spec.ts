import { test, expect } from '@playwright/test';

/**
 * Results Panel & Link Navigation Tests
 *
 * Tests for search results display and link functionality
 * Note: These tests are conditional - they only fully run when the agent produces search results
 */

test.describe('Result Card Links', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { timeout: 10000 });
    await page.waitForTimeout(2000);
  });

  test('should show "原文" or "无链接" on result cards', async ({ page }) => {
    // Execute a task to get results
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only check for buttons if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      const linkButton = page.locator('button:has-text("原文"), span:has-text("无链接")');
      await expect(linkButton.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('should open link in new tab when clicking 原文 button', async ({ page, context }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Find a result card with a link
      const linkButton = page.locator('button:has-text("原文")').first();
      const hasLinkButton = await linkButton.isVisible().catch(() => false);

      if (hasLinkButton) {
        // Listen for new page
        const pagePromise = context.waitForEvent('page');

        // Click the link button
        await linkButton.click();

        // Verify new tab opens
        const newPage = await pagePromise;
        expect(newPage.url()).not.toBe('about:blank');
        await newPage.close();
      } else {
        // If no link buttons, check for "无链接" indicator
        const noLinkIndicator = page.locator('span:has-text("无链接")');
        await expect(noLinkIndicator.first()).toBeVisible();
      }
    }
  });

  test('should expand result detail when clicking card', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Click on a result card (look for cards with cursor-pointer class)
      const resultCard = page.locator('.cursor-pointer').first();
      await resultCard.click();

      // Should show detail view with "返回列表" button
      await expect(page.getByText('返回列表')).toBeVisible({ timeout: 5000 });
    }
  });

  test('should show "查看原文" or "暂无链接" in detail view', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Click on a result card
      const resultCard = page.locator('.cursor-pointer').first();
      await resultCard.click();

      // Should show "查看原文" or "暂无链接"
      const linkOrNoLink = page.locator('text=/查看原文|暂无链接/');
      await expect(linkOrNoLink).toBeVisible({ timeout: 5000 });
    }
  });

  test('should return to list when clicking "返回列表"', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Click on a result card
      const resultCard = page.locator('.cursor-pointer').first();
      await resultCard.click();

      // Wait for detail view
      await expect(page.getByText('返回列表')).toBeVisible();

      // Click "返回列表"
      await page.getByText('返回列表').click();

      // Should be back to list view (shows "共 X 条结果")
      await expect(page.getByText(/共.*条结果/)).toBeVisible();
    }
  });
});

test.describe('Results Filtering', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { timeout: 10000 });
    await page.waitForTimeout(2000);
  });

  test('should have source filter dropdown', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Check for source filter dropdown
      const sourceFilter = page.locator('aside select').first();
      await expect(sourceFilter).toBeVisible();
    }
  });

  test('should have sentiment filter dropdown', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Should have two filter dropdowns
      const filters = page.locator('aside select');
      expect(await filters.count()).toBeGreaterThanOrEqual(2);
    }
  });
});
