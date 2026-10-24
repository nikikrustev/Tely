// OWNER: B (Nikolay; A since the 24 Oct handover). Stub created by A in Stage 0.
import { readFile } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { defineConfig, type Plugin } from 'vitest/config';

const TYPES: Record<string, string> = {
  '.jsonl': 'application/x-ndjson', '.json': 'application/json', '.mp3': 'audio/mpeg', '.vtt': 'text/vtt',
};

/** Dev server only (D21): /replay/v1/local/<stem>/... serves web/.local/<stem>/..., the git-ignored listening-test
 *  commentary (?names=<stem>). Never part of a build, so it can never be deployed. */
function localTestBundles(): Plugin {
  const root = resolve(__dirname, '.local');
  return {
    name: 'local-test-bundles',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/replay/v1/local', (req, res, next) => {
        const file = resolve(root, decodeURIComponent((req.url ?? '').split('?')[0] ?? '').replace(/^\/+/, ''));
        if (!file.startsWith(root + sep)) { res.statusCode = 403; res.end(); return; }
        readFile(file).then((body) => {
          res.setHeader('Content-Type', TYPES[extname(file)] ?? 'application/octet-stream');
          res.end(body);
        }).catch(() => next());
      });
    },
  };
}

export default defineConfig({
  plugins: [localTestBundles()],
  test: {
    // Both lanes' folders by glob: a new tests/a/*.test.ts or tests/b/*.test.ts runs in CI with no config edit.
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
});
