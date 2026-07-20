import { chromium } from 'playwright';

async function takeScreenshots() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();

  try {
    console.error('Navigating to homepage...');
    await page.goto('http://localhost:3002', { waitUntil: 'networkidle' });

    // Take screenshot of homepage
    await page.screenshot({
      path: 'homepage-screenshot.png',
      fullPage: true,
    });
    console.error('Homepage screenshot saved as homepage-screenshot.png');

    // Wait a bit for any dynamic content
    await page.waitForTimeout(2000);

    // Try to find and click analysis/analyze link
    console.error('Looking for analysis page link...');

    // Look for common analysis page links
    const analysisSelectors = [
      'a[href*="analysis"]',
      'a[href*="analyze"]',
      'text=Analysis',
      'text=Analyze',
      '[data-testid*="analysis"]',
      '[data-testid*="analyze"]',
    ];

    let analysisLink = null;
    for (const selector of analysisSelectors) {
      try {
        analysisLink = await page.waitForSelector(selector, { timeout: 1000 });
        if (analysisLink) {
          console.error(`Found analysis link with selector: ${selector}`);
          break;
        }
      } catch {
        // Continue trying other selectors
      }
    }

    if (analysisLink) {
      await analysisLink.click();
      await page.waitForLoadState('networkidle');

      // Take screenshot of analysis page
      await page.screenshot({
        path: 'analysis-screenshot.png',
        fullPage: true,
      });
      console.error('Analysis page screenshot saved as analysis-screenshot.png');
    } else {
      console.error('No analysis page link found. Taking screenshot of current page content.');

      // Let's see what's actually on the page
      const pageTitle = await page.title();
      const pageContent = await page.textContent('body');
      console.error(`Page title: ${pageTitle}`);
      console.error(`Page content preview: ${pageContent.substring(0, 200)}...`);

      // Try to navigate directly to analysis page
      console.error('Trying direct navigation to analysis page...');
      try {
        await page.goto('http://localhost:3002/analysis', { waitUntil: 'networkidle' });
        await page.screenshot({
          path: 'analysis-direct-screenshot.png',
          fullPage: true,
        });
        console.error('Direct analysis page screenshot saved as analysis-direct-screenshot.png');
      } catch {
        console.error('Direct analysis page navigation failed:', e.message);
      }

      // Try other common analysis routes
      const analysisRoutes = ['/analyze', '/dashboard', '/repo-analysis'];
      for (const route of analysisRoutes) {
        try {
          console.error(`Trying route: ${route}`);
          await page.goto(`http://localhost:3002${route}`, { waitUntil: 'networkidle' });
          await page.screenshot({
            path: `${route.replace('/', '')}-screenshot.png`,
            fullPage: true,
          });
          console.error(`Screenshot saved for route ${route}`);
          break;
        } catch {
          console.error(`Route ${route} failed:`, e.message);
        }
      }
    }
  } catch (error) {
    console.error('Error during navigation:', error);

    // Take screenshot of current state even if there was an error
    try {
      await page.screenshot({
        path: 'error-screenshot.png',
        fullPage: true,
      });
      console.error('Error state screenshot saved as error-screenshot.png');
    } catch (screenshotError) {
      console.error('Failed to take error screenshot:', screenshotError);
    }
  } finally {
    await browser.close();
  }
}

takeScreenshots().catch(console.error);
