/**
 * EWasteTradeFlow — Puppeteer PDF microservice.
 *
 * Accepts POST /render with a URL + internal key, navigates headless Chrome
 * to that URL, waits for the page to signal readiness, and returns a PDF.
 *
 * This service runs alongside the FastAPI API on Railway's internal network.
 * It is NOT exposed to the public internet — access is restricted by the
 * PUPPETEER_INTERNAL_KEY shared secret.
 */

import express from 'express';
import rateLimit from 'express-rate-limit';
import puppeteer from 'puppeteer';

const PORT = process.env.PORT || 3001;
const INTERNAL_KEY = process.env.PUPPETEER_INTERNAL_KEY;
const RENDER_TIMEOUT_MS = parseInt(process.env.RENDER_TIMEOUT_MS || '60000', 10);
const MAX_CONCURRENT_RENDERS = parseInt(process.env.MAX_CONCURRENT_RENDERS || '3', 10);

if (!INTERNAL_KEY) {
  console.error('PUPPETEER_INTERNAL_KEY environment variable is required');
  process.exit(1);
}

const app = express();
app.use(express.json({ limit: '1mb' }));

// Rate limit: max 10 render requests per minute (the API enforces its own limits)
const limiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many render requests. Try again in a minute.' },
});
app.use('/render', limiter);

// Track concurrent renders to avoid resource exhaustion
let activeRenders = 0;

// Reuse a single browser instance (much faster than launching per request)
let browser = null;

async function getBrowser() {
  if (!browser || !browser.connected) {
    console.log('Launching Puppeteer browser...');
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',       // Prevents crashes in Docker/Railway
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--single-process',              // Required in some Railway environments
        '--disable-gpu',
      ],
    });
    browser.on('disconnected', () => {
      console.warn('Browser disconnected. Will relaunch on next request.');
      browser = null;
    });
  }
  return browser;
}

/**
 * POST /render
 * Body: { url: string, key: string, format?: 'A4'|'Letter', landscape?: boolean }
 * Returns: PDF binary (application/pdf)
 */
app.post('/render', async (req, res) => {
  const { url, key, format = 'A4', landscape = false } = req.body;

  // Validate internal key
  if (!key || key !== INTERNAL_KEY) {
    return res.status(401).json({ error: 'Invalid internal key' });
  }

  // Validate URL
  if (!url || typeof url !== 'string') {
    return res.status(400).json({ error: 'url is required' });
  }

  // Reject external URLs — only render localhost or the configured frontend URL
  const allowedHosts = [
    'localhost',
    '127.0.0.1',
    process.env.FRONTEND_INTERNAL_URL || '',
  ].filter(Boolean);

  let parsedUrl;
  try {
    parsedUrl = new URL(url);
  } catch {
    return res.status(400).json({ error: 'Invalid URL' });
  }

  const hostAllowed = allowedHosts.some(
    (h) => parsedUrl.hostname === h || parsedUrl.hostname.endsWith(`.${h}`)
  );
  if (!hostAllowed) {
    return res.status(400).json({ error: `URL host '${parsedUrl.hostname}' is not allowed` });
  }

  // Concurrency guard
  if (activeRenders >= MAX_CONCURRENT_RENDERS) {
    return res.status(503).json({
      error: 'Too many concurrent render requests. Try again shortly.',
      retry_after_seconds: 5,
    });
  }

  activeRenders++;
  console.log(`[render] Starting render for ${url} (active: ${activeRenders})`);
  const startTime = Date.now();

  let page = null;
  try {
    const b = await getBrowser();
    page = await b.newPage();

    // Set viewport to A4 dimensions at 96 DPI
    await page.setViewport({ width: 1240, height: 1754, deviceScaleFactor: 1 });

    // Set internal render header so the React app knows it's a Puppeteer render
    await page.setExtraHTTPHeaders({
      'X-Internal-Render': 'true',
    });

    // Navigate to the report view URL
    await page.goto(url, {
      waitUntil: 'networkidle0',
      timeout: RENDER_TIMEOUT_MS,
    });

    // Wait for the React app to signal it's ready for printing.
    // The ReportViewPage sets window.__REPORT_READY = true after all data fetches.
    await page.waitForFunction(
      () => window.__REPORT_READY === true,
      { timeout: RENDER_TIMEOUT_MS }
    );

    // Small buffer for any final layout reflows
    await new Promise((r) => setTimeout(r, 500));

    const pdfBuffer = await page.pdf({
      format,
      landscape,
      printBackground: true,
      margin: { top: '20mm', right: '15mm', bottom: '20mm', left: '15mm' },
      displayHeaderFooter: true,
      footerTemplate: `
        <div style="font-size: 9px; color: #999; width: 100%; text-align: center; padding: 0 15mm;">
          EWasteTradeFlow — ewastetradeflow.com —
          Data: UN Global E-waste Monitor, World Bank, OECD —
          Page <span class="pageNumber"></span> of <span class="totalPages"></span>
        </div>
      `,
      headerTemplate: '<div></div>',
    });

    const elapsed = Date.now() - startTime;
    console.log(`[render] Completed in ${elapsed}ms for ${url}`);

    res.set({
      'Content-Type': 'application/pdf',
      'Content-Length': pdfBuffer.length,
      'X-Render-Time-Ms': elapsed.toString(),
    });
    res.send(pdfBuffer);

  } catch (err) {
    const elapsed = Date.now() - startTime;
    console.error(`[render] Failed after ${elapsed}ms:`, err.message);

    if (!res.headersSent) {
      res.status(500).json({
        error: 'PDF render failed',
        details: process.env.NODE_ENV === 'development' ? err.message : undefined,
      });
    }
  } finally {
    if (page) {
      await page.close().catch(() => {});
    }
    activeRenders--;
  }
});

/** GET /health — used by Railway health checks */
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    active_renders: activeRenders,
    browser_connected: browser?.connected ?? false,
  });
});

// Pre-warm the browser on startup
getBrowser().then(() => {
  console.log('Browser pre-warmed successfully');
}).catch((err) => {
  console.warn('Browser pre-warm failed (will retry on first request):', err.message);
});

app.listen(PORT, () => {
  console.log(`Puppeteer microservice listening on port ${PORT}`);
});
