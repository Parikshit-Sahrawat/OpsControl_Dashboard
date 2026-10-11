// Build-specific hashes permit the theme bootstrap without unsafe-inline JS.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const [index, output, upstream = 'http://api:8000'] = process.argv.slice(2);
if (!index || !output || !/^http:\/\/[a-zA-Z0-9._-]+:[0-9]{1,5}$/.test(upstream)) {
  throw new Error('Usage: node render-production-nginx.mjs dist/index.html output.conf http://api:8000');
}
const html = readFileSync(index, 'utf8');
const hashes = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)]
  .filter(([, attributes, source]) => !/\bsrc\s*=/i.test(attributes) && source.trim())
  .map(([, , source]) => `'sha256-${createHash('sha256').update(source).digest('base64')}'`);
const template = readFileSync(fileURLToPath(new URL('../../deploy/examples/nginx.production.conf.template', import.meta.url)), 'utf8');
writeFileSync(output, template.replaceAll('__INLINE_SCRIPT_HASHES__', hashes.join(' ')).replaceAll('__API_UPSTREAM__', upstream));
