import { test, expect } from '@playwright/test';

/**
 * InsightSentinel E2E Tests
 *
 * Test scenarios for the main application functionality
 */

test.describe('InsightSentinel App', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app
    await page.goto('/');
    // Wait for the app to load
    await page.waitForSelector('header', { timeout: 10000 });
  });

  test.describe('Page Load & Layout', () => {
    test('should display header with title', async ({ page }) => {
      // Check header exists
      const header = page.locator('header');
      await expect(header).toBeVisible();

      // Check title - it's split into INSIGHT and SENTINEL
      await expect(page.getByRole('heading', { name: /INSIGHT.*SENTINEL/i })).toBeVisible();
    });

    test('should display log panel on the left', async ({ page }) => {
      // Log panel should be visible - look for Live Reasoning text
      const logPanel = page.getByText('Live Reasoning');
      await expect(logPanel).toBeVisible();

      // Should have initial system logs
      await expect(page.getByText(/InsightSentinel.*启动完成/)).toBeVisible();
    });

    test('should display command bar at the bottom', async ({ page }) => {
      // Command input should be visible - use the actual placeholder
      const commandInput = page.locator('input#agent-command');
      await expect(commandInput).toBeVisible();
    });

    test('should display network map area', async ({ page }) => {
      // NetworkMap placeholder or actual content
      const networkArea = page.getByText('执行任务后显示实体关系图');
      await expect(networkArea).toBeVisible();
    });

    test('should display stats grid with platform cards', async ({ page }) => {
      // Check for platform labels in stats grid
      await expect(page.getByText('WeChat').first()).toBeVisible();
      await expect(page.getByText('Zhihu').first()).toBeVisible();
    });

    test('should show SYSTEM ONLINE status', async ({ page }) => {
      await expect(page.getByText('SYSTEM ONLINE')).toBeVisible();
    });
  });

  test.describe('Connection Status', () => {
    test('should show connection status indicator', async ({ page }) => {
      // Wait for connection check
      await page.waitForTimeout(2000);

      // Should show either "Backend Connected" or "Demo Mode"
      const statusText = page.locator('text=/Backend Connected|Demo Mode|Checking/');
      await expect(statusText).toBeVisible();
    });

    test('should display connection log message', async ({ page }) => {
      // Wait for connection check to complete
      await page.waitForTimeout(3000);

      // Should see connection status log (use .first() as multiple logs may match)
      const connectedLog = page.getByText(/后端服务|演示模式/).first();
      await expect(connectedLog).toBeVisible();
    });
  });

  test.describe('Command Input', () => {
    test('should allow typing in command bar', async ({ page }) => {
      const commandInput = page.locator('input#agent-command');

      // Type a command
      await commandInput.fill('分析 DeepSeek 最新动态');

      // Verify the text was entered
      await expect(commandInput).toHaveValue('分析 DeepSeek 最新动态');
    });

    test('should have quick action buttons', async ({ page }) => {
      // Check for quick action buttons - actual labels are in English
      const actions = page.locator('button:has-text("Analyze"), button:has-text("Map"), button:has-text("Risk")');
      const count = await actions.count();
      expect(count).toBeGreaterThan(0);
    });

    test('should execute command when clicking quick action', async ({ page }) => {
      // Click a quick action button
      const quickAction = page.getByRole('button', { name: /Analyze Sentiment/i });
      await quickAction.click();

      // Should trigger execution - check for USER CMD in logs
      await expect(page.getByText('USER CMD:')).toBeVisible({ timeout: 5000 });
    });

    test('should show EXECUTE button', async ({ page }) => {
      // Fill in some text first
      const commandInput = page.locator('input#agent-command');
      await commandInput.fill('test');

      // Execute button should be visible
      const executeButton = page.getByRole('button', { name: /EXECUTE/i });
      await expect(executeButton).toBeVisible();
    });

    test('should show ABORT button during processing', async ({ page }) => {
      // Fill and submit a command
      const commandInput = page.locator('input#agent-command');
      await commandInput.fill('测试命令');

      const executeButton = page.getByRole('button', { name: /EXECUTE/i });
      await executeButton.click();

      // ABORT button should appear (increase timeout for slower connections)
      await expect(page.getByRole('button', { name: /ABORT/i })).toBeVisible({ timeout: 10000 });
    });
  });
});
