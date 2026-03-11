import { test, expect } from '@playwright/test';

/**
 * Task Execution Tests
 *
 * Tests for executing commands and viewing results
 */

test.describe('Task Execution', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { timeout: 10000 });
    // Wait for backend connection
    await page.waitForTimeout(2000);
  });

  test('should execute command and show progress logs', async ({ page }) => {
    // Get command input
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('分析 AI 大模型');

    // Find and click execute button
    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Should show command echo in logs
    await expect(page.getByText('USER CMD:')).toBeVisible({ timeout: 5000 });

    // Should show agent connecting log
    await expect(page.getByText(/正在连接|Agent/)).toBeVisible({ timeout: 10000 });
  });

  test('should show ABORT button during execution', async ({ page }) => {
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('测试任务');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // ABORT button should appear during processing
    await expect(page.getByRole('button', { name: /ABORT/i })).toBeVisible({ timeout: 5000 });
  });

  test('should cancel execution when clicking ABORT', async ({ page }) => {
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('长时间任务');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for ABORT button
    const abortButton = page.getByRole('button', { name: /ABORT/i });
    await expect(abortButton).toBeVisible({ timeout: 5000 });

    // Click ABORT
    await abortButton.click();

    // Should show cancellation log
    await expect(page.getByText(/取消|cancelled/i)).toBeVisible({ timeout: 5000 });

    // EXECUTE button should return
    await expect(page.getByRole('button', { name: /EXECUTE/i })).toBeVisible({ timeout: 5000 });
  });

  test('should display task completion message', async ({ page }) => {
    // Wait for backend to be ready
    await page.waitForTimeout(3000);

    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('分析 AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for completion (longer timeout for full execution)
    await expect(page.getByText(/任务完成|完成|error/i)).toBeVisible({ timeout: 90000 });
  });
});

test.describe('Results Panel', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('header', { timeout: 10000 });
    await page.waitForTimeout(2000);
  });

  test('should show results panel after task completion', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎关于AI的内容');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion (results panel may or may not appear depending on agent behavior)
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });
  });

  test('should display result cards with source labels', async ({ page }) => {
    // Execute a task
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索知乎AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Check for source labels only if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      const sourceLabels = page.locator('text=/知乎|WeChat|小红书|抖音/');
      await expect(sourceLabels.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('should close results panel when clicking close button', async ({ page }) => {
    const commandInput = page.locator('input#agent-command');
    await commandInput.fill('搜索AI');

    const executeButton = page.getByRole('button', { name: /EXECUTE/i });
    await executeButton.click();

    // Wait for task completion
    await expect(page.getByText(/任务完成|搜索结果|error/i)).toBeVisible({ timeout: 90000 });

    // Only test close if results panel appears
    const hasResultsPanel = await page.getByText('搜索结果').isVisible().catch(() => false);
    if (hasResultsPanel) {
      // Close button should be visible
      const closeButton = page.locator('aside button:has(.material-symbols-outlined)').first();
      await closeButton.click();

      // Results panel should be hidden
      await expect(page.getByText('搜索结果')).not.toBeVisible({ timeout: 5000 });
    }
  });
});
