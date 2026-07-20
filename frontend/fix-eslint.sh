#!/bin/bash

# Fix test-artifacts files by converting console.log to console.error
# These are test utility scripts, so console output is intentional

echo "Fixing test-artifacts files..."

# Fix pricing-cta-focused.js
sed -i "s/console\.log(/console.error(/g" test-artifacts/pricing-cta-focused.js
sed -i "s/const { chromium } = require('playwright');/import { chromium } from 'playwright';/" test-artifacts/pricing-cta-focused.js

# Fix pricing-cta-test.js
sed -i "s/console\.log(/console.error(/g" test-artifacts/pricing-cta-test.js
sed -i "s/const { chromium } = require('playwright');/import { chromium } from 'playwright';/" test-artifacts/pricing-cta-test.js
sed -i "s/} catch (e) {/} catch (_e) {/g" test-artifacts/pricing-cta-test.js

# Fix screenshot-test.js
sed -i "s/console\.log(/console.error(/g" test-artifacts/screenshot-test.js
sed -i "s/const { chromium } = require('playwright');/import { chromium } from 'playwright';/" test-artifacts/screenshot-test.js
sed -i "s/} catch (e) {/} catch (_e) {/g" test-artifacts/screenshot-test.js

echo "Test artifacts fixed!"
