# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static Astro showcase at megabonkmod.party with an integrated Starlight wiki at docs.megabonkmod.party/home/. Prefer Markdown and vanilla JavaScript; the showcase uses Alpine.js and Basecoat UI, while the wiki keeps Starlight's documentation controls. Both build into one static image. The community level gallery (`/levels/`, `/l/<code>`, `/levels/upload/`) is static pages that fetch from a separate PocketBase API at runtime with the `pocketbase` JavaScript SDK.

## Users

Megabonk players who want to create, playtest and share custom levels. Developers exploring the console and MCP tools are a secondary audience.

## Product Purpose

Explain what Megabonk Levels adds to the base game and help a visitor begin creating through the maintained repository guides.

The wiki helps players install the mod, try and share levels, and find music, Warehouse and packaging references. Publish the eight selected guides from repository Markdown without duplicating their maintenance. Provide full-text search, per-page Markdown copying and raw Markdown links; keep internal technical docs in the source repository. The legacy player installer must remain clearly distinguished from the current BepInEx route.

## Capabilities and Constraints

The unofficial mod provides an in-game level editor, console and development MCP server. Editing and playing remain in the game; the website is a showcase, not a web editor. The level gallery also hosts small player-made asset packs (at most 30 MiB each): the uploader attests they have the right to share the pack, anyone can report a level or pack for copyright, and a valid report hides it. Downloads are always manual; the mod never fetches a pack itself. The public release is available on [Thunderstore](https://thunderstore.io/c/megabonk/p/pythoninthegrass/Megabonk_Level_Editor/). Levels are supplied separately. The supported player route uses the Windows game build, including through Proton or Wine.

## Evidence on Hand

Repository guides describe the shipped behavior. Bramblecrown Hill is the primary showcase. Its selection illustration is not a gameplay screenshot. Use real game captures for editor, console and gameplay proof. Editor and gameplay videos are explicitly labeled placeholders until recordings are supplied.

## Product Principles

- Demonstrate actual capabilities rather than inventing claims.
- Put creators first without obscuring console and MCP workflows.
- Keep commands copyable and distinguish shell, console and MCP examples.
- Preserve readable content without JavaScript. The one deliberate exception is the level gallery, which lists, uploads and likes levels through a live API and cannot work without scripting; its pages show a `<noscript>` message that links to the manual sharing steps in the player guide.

## Accessibility & Inclusion

Support keyboard navigation, visible focus, reduced motion, readable contrast and mobile layouts.
