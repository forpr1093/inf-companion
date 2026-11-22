import { defineConfig } from "vitest/config";
import { svelte } from "@sveltejs/vite-plugin-svelte";

export default defineConfig({
  plugins: [svelte()],
  build: { outDir: "../inf_companion/web_dist", emptyOutDir: true },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765",
      "/skin": "http://127.0.0.1:8765",
      "/ws": { target: "ws://127.0.0.1:8765", ws: true },
    },
  },
  test: { include: ["src/**/*.test.ts"], environment: "node" },
});
