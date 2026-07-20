import { chromium } from 'playwright';

async function analyzePricingCTA() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
  });

  const page = await context.newPage();

  try {
    console.error('Navigating to pricing page...');
    await page.goto('http://localhost:3000/pricing', {
      waitUntil: 'networkidle',
      timeout: 30000,
    });

    // Wait for page to fully load
    await page.waitForTimeout(3000);

    // Take full page screenshot first
    await page.screenshot({
      path: 'pricing-full-page.png',
      fullPage: true,
    });
    console.error('Full pricing page screenshot saved as pricing-full-page.png');

    // Look for CTA section at the bottom
    console.error('Analyzing CTA section...');

    // Common selectors for CTA sections
    const ctaSelectors = [
      '[data-testid*="cta"]',
      '.cta',
      'section:last-of-type',
      'footer',
      '[class*="cta"]',
      '[class*="call-to-action"]',
      '[class*="bottom"]',
      'div:has(button):last-of-type',
    ];

    let ctaSection = null;
    let _ctaSectionSelector = null;

    // Try to find CTA section
    for (const selector of ctaSelectors) {
      try {
        const element = await page.$(selector);
        if (element) {
          // Check if this section contains buttons
          const buttons = await element.$$('button, a[role="button"], .button, [class*="btn"]');
          if (buttons.length >= 2) {
            ctaSection = element;
            _ctaSectionSelector = selector;
            console.error(`Found CTA section with selector: ${selector}`);
            break;
          }
        }
      } catch {
        // Continue trying other selectors
      }
    }

    // If no specific CTA section found, look for buttons at the bottom of the page
    if (!ctaSection) {
      console.error('No specific CTA section found, looking for buttons at bottom of page...');

      // Scroll to bottom
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(1000);

      // Find all buttons on the page
      const allButtons = await page.$$('button, a[role="button"], .button, [class*="btn"]');
      console.error(`Found ${allButtons.length} total buttons on the page`);

      if (allButtons.length >= 2) {
        // Take the last few buttons as likely CTA buttons
        const lastButtons = allButtons.slice(-2);

        // Get their positions to find the bottom-most ones
        const buttonPositions = [];
        for (let i = 0; i < lastButtons.length; i++) {
          const button = lastButtons[i];
          const box = await button.boundingBox();
          if (box) {
            buttonPositions.push({ button, box, index: i });
          }
        }

        // Sort by Y position (bottom to top)
        buttonPositions.sort((a, b) => b.box.y - a.box.y);

        if (buttonPositions.length >= 2) {
          const bottomButtons = buttonPositions.slice(0, 2);

          // Analyze the bottom buttons
          console.error('\nAnalyzing bottom CTA buttons:');

          for (let i = 0; i < bottomButtons.length; i++) {
            const { button, box } = bottomButtons[i];

            // Get button text
            const text = await button.textContent();

            // Get button styles
            const styles = await button.evaluate((el) => {
              const computed = window.getComputedStyle(el);
              return {
                width: computed.width,
                height: computed.height,
                backgroundColor: computed.backgroundColor,
                color: computed.color,
                fontSize: computed.fontSize,
                padding: computed.padding,
                margin: computed.margin,
                borderRadius: computed.borderRadius,
                border: computed.border,
              };
            });

            console.error(`\nButton ${i + 1}:`);
            console.error(`  Text: "${text}"`);
            console.error(`  Position: x=${box.x}, y=${box.y}`);
            console.error(`  Size: ${box.width}x${box.height}`);
            console.error(`  Styles:`, styles);

            // Highlight and screenshot individual button
            await button.scrollIntoViewIfNeeded();
            await button.highlight();

            await page.screenshot({
              path: `cta-button-${i + 1}.png`,
              clip: {
                x: Math.max(0, box.x - 20),
                y: Math.max(0, box.y - 20),
                width: Math.min(1920, box.width + 40),
                height: Math.min(1080, box.height + 40),
              },
            });
            console.error(`  Screenshot saved as cta-button-${i + 1}.png`);
          }

          // Compare button sizes
          if (bottomButtons.length >= 2) {
            const button1 = bottomButtons[0];
            const button2 = bottomButtons[1];

            console.error('\nButton Size Comparison:');
            console.error(`Button 1: ${button1.box.width}x${button1.box.height}`);
            console.error(`Button 2: ${button2.box.width}x${button2.box.height}`);

            if (
              button1.box.width === button2.box.width &&
              button1.box.height === button2.box.height
            ) {
              console.error('✓ Buttons are the SAME SIZE');
            } else {
              console.error('✗ Buttons are DIFFERENT SIZES');
              console.error(
                `  Width difference: ${Math.abs(button1.box.width - button2.box.width)}px`
              );
              console.error(
                `  Height difference: ${Math.abs(button1.box.height - button2.box.height)}px`
              );
            }
          }
        }
      }
    }

    // Take a screenshot focused on the bottom section
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(1000);

    // Get the viewport height and take a screenshot of the bottom portion
    const viewportHeight = 1080;
    const documentHeight = await page.evaluate(() => document.body.scrollHeight);

    await page.screenshot({
      path: 'pricing-bottom-cta.png',
      clip: {
        x: 0,
        y: Math.max(0, documentHeight - viewportHeight),
        width: 1920,
        height: Math.min(viewportHeight, documentHeight),
      },
    });
    console.error('Bottom CTA section screenshot saved as pricing-bottom-cta.png');

    // Also look for any buttons with specific text patterns
    console.error('\nLooking for buttons with common CTA text...');
    const ctaTextPatterns = [
      'get started',
      'start free',
      'try now',
      'sign up',
      'contact',
      'buy now',
      'purchase',
      'subscribe',
      'upgrade',
      'learn more',
    ];

    for (const pattern of ctaTextPatterns) {
      try {
        const buttons = await page.$$(`button:has-text("${pattern}"), a:has-text("${pattern}")`);
        if (buttons.length > 0) {
          console.error(`Found ${buttons.length} button(s) with text containing "${pattern}"`);

          for (let i = 0; i < buttons.length; i++) {
            const button = buttons[i];
            const text = await button.textContent();
            const box = await button.boundingBox();
            console.error(
              `  Button ${i + 1}: "${text}" at position ${box?.x},${box?.y} size ${box?.width}x${box?.height}`
            );
          }
        }
      } catch {
        // Pattern not found, continue
      }
    }
  } catch (error) {
    console.error('Error during pricing page analysis:', error);

    // Take screenshot of current state even if there was an error
    try {
      await page.screenshot({
        path: 'pricing-error-screenshot.png',
        fullPage: true,
      });
      console.error('Error state screenshot saved as pricing-error-screenshot.png');

      // Get page title and some content for debugging
      const pageTitle = await page.title();
      const pageUrl = page.url();
      console.error(`Page title: ${pageTitle}`);
      console.error(`Page URL: ${pageUrl}`);

      // Check if page loaded properly
      const bodyText = await page.textContent('body');
      console.error(`Page content preview: ${bodyText?.substring(0, 200)}...`);
    } catch (screenshotError) {
      console.error('Failed to take error screenshot:', screenshotError);
    }
  } finally {
    await browser.close();
  }
}

console.error('Starting pricing page CTA analysis...');
analyzePricingCTA().catch(console.error);
