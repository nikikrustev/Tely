// OWNER: B (Nikolay). Stub created by A in Stage 0.
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Both lanes' folders by glob: a new tests/a/*.test.ts or tests/b/*.test.ts runs in CI with no config edit.
    include: ['tests/**/*.test.ts'],
    environment: 'node',
  },
});
