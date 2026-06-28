import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: "./",
  plugins: [react()],
  resolve: {
    alias: {
      events: "events",
      fs: path.resolve(__dirname, "src/node-stubs/fs.js"),
      os: path.resolve(__dirname, "src/node-stubs/os.js")
    }
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8765"
    }
  }
});
