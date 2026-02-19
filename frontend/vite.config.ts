import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');

  // Sempre prioriza backend local deste projeto.
  const LOCAL_API = 'http://localhost:8000';
  const proxyTarget = env.RAG_SERVER_URL || LOCAL_API;

    // Frontend URL: em dev SEMPRE vazio (usa URLs relativas + proxy do Vite)
    // Em build de produção, pode definir RAG_PUBLIC_URL se o API estiver em domínio diferente
    const frontendRagUrl = mode === 'development' ? '' : (env.RAG_PUBLIC_URL || env.RAG_SERVER_URL || '');
    
    return {
      server: {
        port: 3000,
        host: '0.0.0.0',
        proxy: {
          '/api': {
            target: proxyTarget,
            changeOrigin: true,
            secure: true,
            timeout: 600000, // 10min — uploads grandes passam pelo proxy
          },
        },
      },
      plugins: [react()],
      define: {
        'process.env.SUPABASE_URL': JSON.stringify(env.SUPABASE_URL || ''),
        'process.env.SUPABASE_ANON_KEY': JSON.stringify(env.SUPABASE_ANON_KEY || ''),
        'process.env.RAG_SERVER_URL': JSON.stringify(frontendRagUrl),
        'process.env.RAG_API_KEY': JSON.stringify(env.RAG_API_KEY || ''),
        'process.env.RAG_ADMIN_KEY': JSON.stringify(env.RAG_ADMIN_KEY || ''),
        'process.env.MP_PUBLIC_KEY': JSON.stringify(env.MP_PUBLIC_KEY || env.MERCADO_PAGO_PUBLIC_KEY || ''),
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      }
    };
});
