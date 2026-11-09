import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import starlight from '@astrojs/starlight';
import starlightLlmsTxt from 'starlight-llms-txt';
import sitemap from '@astrojs/sitemap';
import { guides } from './scripts/sync-docs.mjs';

export default defineConfig({
  site: 'https://docs.megabonkmod.party',
  output: 'static',
  vite: { plugins: [tailwindcss()] },
  markdown: { shikiConfig: { theme: 'github-dark' } },
  integrations: [sitemap({ filter: (page) => {
    const path = new URL(page).pathname;
    return path === '/home/' || path.startsWith('/docs/');
  } }), starlight({
    title: 'Megabonk Level Editor',
    description: 'Player guides and level-building references for the unofficial Megabonk Level Editor.',
    components: {
      PageTitle: './src/components/WikiPageTitle.astro',
      SiteTitle: './src/components/WikiSiteTitle.astro',
    },
    customCss: ['./src/styles/wiki.css'],
    social: [{ icon: 'github', label: 'Source repository', href: 'https://github.com/pythoninthegrass/megabonk_mods' }],
    plugins: [starlightLlmsTxt({
      projectName: 'Megabonk Level Editor wiki',
      details: guides.map((slug) => `- [${slug.replaceAll('-', ' ')}](https://docs.megabonkmod.party/docs/${slug}.md)`).join('\n'),
    })],
    sidebar: [
      { label: 'Wiki home', slug: 'home' },
      { label: 'Start playing', items: ['docs/player-guide', 'docs/starter-level', 'docs/music'] },
      { label: 'Warehouse', items: ['docs/thps-warehouse', 'docs/thps-warehouse-layout', 'docs/thps-warehouse-pieces'] },
      { label: 'Packages & compatibility', items: [
        'docs/thunderstore', { label: 'Legacy player installer', slug: 'docs/player-installer' },
      ] },
      { label: 'Showcase', link: 'https://megabonkmod.party/' },
    ],
  })],
});
