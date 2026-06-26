import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The Vite dev server (5173) talks to the Prism backend (8200) via VITE_API_BASE (see src/api.ts).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, host: "127.0.0.1" },
});
