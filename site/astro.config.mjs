import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import starlight from '@astrojs/starlight';
import starlightLlmsTxt from 'starlight-llms-txt';
import sitemap from '@astrojs/sitemap';
import { guides } from './scripts/sync-docs.mjs';
import { viewRoute } from './routes.mjs';
import { devSession } from './scripts/dev-api.mjs';
import { makerFromSignInPath, signInPage } from './scripts/dev-seed.mjs';

const shareLinkRewrites = {
  name: 'share-link-rewrites',
  configureServer(server) {
    server.middlewares.use(async (req, res, next) => {
      const { pathname } = new URL(req.url, 'http://dev.local');
      const maker = makerFromSignInPath(pathname);
      if (maker) {
        try {
          const session = await devSession(maker);
          res.setHeader('content-type', 'text/html; charset=utf-8');
          res.end(signInPage(session, `/u/${session.record.id}`));
        } catch (error) {
          res.statusCode = 502;
          res.end(`Dev sign-in failed: ${error.message}`);
        }
        return;
      }
      const target = viewRoute(pathname);
      if (target) req.url = target.replace(/index\.html$/, '');
      next();
    });
  },
};

export default defineConfig({
  site: 'https://docs.megabonkmod.party',
  output: 'static',
  vite: {
    envDir: fileURLToPath(new URL('..', import.meta.url)),
    plugins: [tailwindcss(), shareLinkRewrites],
  },
  markdown: { shikiConfig: { theme: 'github-dark' } },
  integrations: [
    sitemap({
      filter: (page) => {
        const path = new URL(page).pathname;
        return path === '/home/' || guides.some((slug) => path === `/${slug}/`);
      },
    }),
    starlight({
      disable404Route: true,
      title: 'Megabonk Level Editor',
      description:
        'Player guides and level-building references for the unofficial Megabonk Level Editor.',
      components: {
        PageTitle: './src/components/WikiPageTitle.astro',
        SiteTitle: './src/components/WikiSiteTitle.astro',
      },
      customCss: ['./src/styles/wiki.css'],
      social: [{
        icon: 'github',
        label: 'Source repository',
        href: 'https://github.com/pythoninthegrass/megabonk_mods',
      }],
      plugins: [starlightLlmsTxt({
        projectName: 'Megabonk Level Editor wiki',
        details: guides.map((slug) =>
          `- [${slug.replaceAll('-', ' ')}](https://docs.megabonkmod.party/${slug}.md)`
        ).join('\n'),
      })],
      sidebar: [
        { label: 'Wiki home', slug: 'home' },
        {
          label: 'Start playing',
          items: ['player-guide', 'starter-level', 'music'],
        },
        {
          label: 'Warehouse',
          items: [
            'thps-warehouse',
            'thps-warehouse-layout',
            'thps-warehouse-pieces',
          ],
        },
        {
          label: 'Packages & compatibility',
          items: [
            'thunderstore',
            { label: 'Legacy player installer', slug: 'player-installer' },
          ],
        },
        { label: 'Showcase', link: 'https://megabonkmod.party/' },
      ],
    }),
  ],
});
