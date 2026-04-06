#!/usr/bin/env node
/**
 * Ultra-lightweight static file server for Telegram Signal Bot dashboard.
 * Serves pre-built Next.js static HTML and assets with minimal memory footprint.
 * Starts instantly (<50ms) so it's ready before the sandbox process killer fires.
 * 
 * Usage: node minimal-server.js [--port 3000]
 */
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = parseInt(process.argv[2] || '3000', 10);
const BASE = '/home/z/my-project';
const INDEX_HTML = path.join(BASE, '.next/server/app/index.html');
const STATIC_DIR = path.join(BASE, '.next/static');
const PUBLIC_DIR = path.join(BASE, 'public');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.json': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
};

// Cache frequently accessed files in memory
const cache = new Map();
function readCached(filePath) {
  if (cache.has(filePath)) return cache.get(filePath);
  try {
    const data = fs.readFileSync(filePath);
    cache.set(filePath, data);
    return data;
  } catch { return null; }
}

const server = http.createServer((req, res) => {
  const urlPath = req.url.split('?')[0];

  // Main page
  if (urlPath === '/' || urlPath === '') {
    const html = readCached(INDEX_HTML);
    if (html) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-cache' });
      return res.end(html);
    }
    res.writeHead(503, { 'Content-Type': 'text/html' });
    return res.end('<h1>Building... please refresh in a few seconds</h1>');
  }

  // Next.js static chunks (JS, CSS, fonts, images)
  if (urlPath.startsWith('/_next/static/')) {
    const relPath = urlPath.slice('/_next/static/'.length);
    const filePath = path.join(STATIC_DIR, relPath);
    const data = readCached(filePath);
    if (data) {
      const ext = path.extname(relPath);
      res.writeHead(200, {
        'Content-Type': MIME[ext] || 'application/octet-stream',
        'Cache-Control': 'public, max-age=31536000, immutable',
      });
      return res.end(data);
    }
    res.writeHead(404);
    return res.end('Not found');
  }

  // Public files (favicon, etc.)
  if (!urlPath.includes('..')) {
    const filePath = path.join(PUBLIC_DIR, urlPath);
    const data = readCached(filePath);
    if (data) {
      const ext = path.extname(urlPath);
      res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
      return res.end(data);
    }
  }

  // API routes — return offline indicator
  if (urlPath.startsWith('/api/')) {
    res.writeHead(503, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ success: false, error: 'Server starting up' }));
  }

  res.writeHead(404);
  res.end('Not found');
});

// Handle server errors gracefully
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`Port ${PORT} already in use, exiting`);
    process.exit(0);
  }
  console.error('Server error:', err.message);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Minimal server listening on :${PORT}`);
  console.log(`Serving: ${INDEX_HTML}`);
});
