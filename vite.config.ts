import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  // @ts-ignore: process.cwd() is available in the node environment but might be missing from the types
  const env = loadEnv(mode, (process as any).cwd(), '');
  return {
    plugins: [react()],
    base: '/SolarView/', // IMPORTANT: Matches your GitHub Repo name
    define: {
      'process.env.API_KEY': JSON.stringify(env.API_KEY)
    }
  };
});