import { chromium } from 'playwright';

async function analyzePricingCTAFocused() {
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

    console.error('Page loaded successfully');
    console.error(`Page title: ${await page.title()}`);
    console.error(`Page URL: ${page.url()}`);

    // Take full page screenshot
    await page.screenshot({
      path: 'pricing-full-analysis.png',
      fullPage: true,
    });
    console.error('Full pricing page screenshot saved');

    // Scroll to bottom to ensure all content is loaded
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);

    // Find all buttons on the page
    console.error('\nFinding all buttons on the page...');
    const allButtons = await page.$$(
      'button, a[role="button"], .button, [class*="btn"], a[class*="button"]'
    );
    console.error(`Found ${allButtons.length} buttons total`);

    // Analyze each button
    const buttonAnalysis = [];

    for (let i = 0; i < allButtons.length; i++) {
      const button = allButtons[i];

      try {
        // Get button properties
        const text = await button.textContent();
        const box = await button.boundingBox();

        if (box && text && text.trim()) {
          // Get computed styles
          const styles = await button.evaluate((el) => {
            const computed = window.getComputedStyle(el);
            return {
              width: computed.width,
              height: computed.height,
              backgroundColor: computed.backgroundColor,
              color: computed.color,
              fontSize: computed.fontSize,
              fontWeight: computed.fontWeight,
              padding: computed.padding,
              margin: computed.margin,
              borderRadius: computed.borderRadius,
              border: computed.border,
              textAlign: computed.textAlign,
              display: computed.display,
            };
          });

          // Get element classes and attributes
          const className = await button.getAttribute('class');
          const href = await button.getAttribute('href');
          const role = await button.getAttribute('role');
          const tagName = await button.evaluate((el) => el.tagName);

          buttonAnalysis.push({
            index: i + 1,
            text: text.trim(),
            position: { x: box.x, y: box.y },
            size: { width: box.width, height: box.height },
            styles,
            attributes: {
              className,
              href,
              role,
              tagName,
            },
          });

          console.error(
            `Button ${i + 1}: "${text.trim()}" (${box.width}x${box.height}) at (${box.x}, ${box.y})`
          );
        }
      } catch (e) {
        console.error(`Error analyzing button ${i + 1}:`, e.message);
      }
    }

    // Sort buttons by Y position to find bottom ones
    buttonAnalysis.sort((a, b) => b.position.y - a.position.y);

    console.error('\n=== BOTTOM CTA BUTTONS ANALYSIS ===');

    // Take the bottom 2-3 buttons as likely CTA buttons
    const bottomButtons = buttonAnalysis.slice(0, Math.min(3, buttonAnalysis.length));

    if (bottomButtons.length >= 2) {
      console.error(`\nAnalyzing the bottom ${bottomButtons.length} buttons:`);

      bottomButtons.forEach((btn, index) => {
        console.error(`\nCTA Button ${index + 1}:`);
        console.error(`  Text: "${btn.text}"`);
        console.error(`  Size: ${btn.size.width}x${btn.size.height}`);
        console.error(`  Position: (${btn.position.x}, ${btn.position.y})`);
        console.error(`  Tag: ${btn.attributes.tagName}`);
        console.error(`  Classes: ${btn.attributes.className || 'none'}`);
        if (btn.attributes.href) {
          console.error(`  Link: ${btn.attributes.href}`);
        }
        console.error(`  Background: ${btn.styles.backgroundColor}`);
        console.error(`  Color: ${btn.styles.color}`);
        console.error(`  Font Size: ${btn.styles.fontSize}`);
        console.error(`  Font Weight: ${btn.styles.fontWeight}`);
        console.error(`  Padding: ${btn.styles.padding}`);
        console.error(`  Border Radius: ${btn.styles.borderRadius}`);
      });

      // Compare sizes of the top 2 bottom buttons
      if (bottomButtons.length >= 2) {
        const btn1 = bottomButtons[0];
        const btn2 = bottomButtons[1];

        console.error('\n=== BUTTON SIZE COMPARISON ===');
        console.error(`Button 1 ("${btn1.text}"): ${btn1.size.width}x${btn1.size.height}`);
        console.error(`Button 2 ("${btn2.text}"): ${btn2.size.width}x${btn2.size.height}`);

        const widthDiff = Math.abs(btn1.size.width - btn2.size.width);
        const heightDiff = Math.abs(btn1.size.height - btn2.size.height);

        if (widthDiff <= 1 && heightDiff <= 1) {
          console.error('✅ RESULT: Buttons are the SAME SIZE (within 1px tolerance)');
        } else {
          console.error('❌ RESULT: Buttons are DIFFERENT SIZES');
          console.error(`   Width difference: ${widthDiff}px`);
          console.error(`   Height difference: ${heightDiff}px`);
        }
      }

      // Take focused screenshot of the bottom area
      console.error('\nTaking focused screenshot of bottom CTA area...');

      // Calculate the area that includes the bottom buttons
      const minY = Math.min(...bottomButtons.map((b) => b.position.y));
      const maxY = Math.max(...bottomButtons.map((b) => b.position.y + b.size.height));
      const minX = Math.min(...bottomButtons.map((b) => b.position.x));
      const maxX = Math.max(...bottomButtons.map((b) => b.position.x + b.size.width));

      // Add some padding
      const padding = 50;
      const clipArea = {
        x: Math.max(0, minX - padding),
        y: Math.max(0, minY - padding),
        width: Math.min(1920, maxX - minX + 2 * padding),
        height: Math.min(1080, maxY - minY + 2 * padding),
      };

      // Scroll to make sure the area is visible
      await page.evaluate((y) => window.scrollTo(0, y), minY - 200);
      await page.waitForTimeout(1000);

      await page.screenshot({
        path: 'pricing-cta-focused.png',
        clip: clipArea,
      });
      console.error('Focused CTA screenshot saved as pricing-cta-focused.png');
    } else {
      console.error('Could not find enough buttons for CTA analysis');
    }

    // Summary
    console.error('\n=== SUMMARY ===');
    console.error(`Total buttons found: ${buttonAnalysis.length}`);
    console.error(`Bottom CTA buttons analyzed: ${bottomButtons.length}`);

    if (bottomButtons.length >= 2) {
      console.error('\nCTA Button Texts:');
      bottomButtons.forEach((btn, index) => {
        console.error(`  ${index + 1}. "${btn.text}"`);
      });
    }
  } catch (error) {
    console.error('Error during analysis:', error);

    // Take a basic screenshot for debugging
    try {
      await page.screenshot({
        path: 'pricing-debug-screenshot.png',
        fullPage: true,
      });
      console.error('Debug screenshot saved');
    } catch (e) {
      console.error('Could not take debug screenshot:', e);
    }
  } finally {
    await browser.close();
  }
}

console.error('Starting focused pricing page CTA analysis...');
analyzePricingCTAFocused().catch(console.error);
