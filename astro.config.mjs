import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://paddedzero.github.io',
  base: '/pub-blog',
  integrations: [mdx(), sitemap()],
});
