---
version: 1
slug: "src-content-docs-docs-index-md"
primary_target: "src/content/docs/docs/index.md"
related_targets: ["src/components/WikiPageTitle.astro", "src/components/WikiSiteTitle.astro", "src/styles/wiki.css"]
---

# Player wiki

Mode: Read. Routes: /docs/ and /docs/<guide>/. Players need installation, level and music guidance; Warehouse builders need reference tables. The repository Markdown remains authoritative.

## Direction contract

THESIS: A familiar Starlight reference wiki, matching the requested reference implementation rather than inventing a new documentation interface.

OWN-WORLD: Preserve standard sidebar, search and page-contents placement. Extend the showcase's pale-blue navigation, vermilion links and Archivo headings; use a standard white reading background and keep the reading column calm in Public Sans. Respect both light and dark themes.

STORY: Start with the player guide, find a level or technical reference, then copy a whole page as Markdown without copying navigation or controls. Legacy loader guidance remains explicitly labeled.

FIRST VIEWPORT: Search in the masthead, grouped navigation at left, title and compact Markdown controls above the reading column, section contents at right. Mobile uses Starlight's native menu and contents disclosures, with copy controls wrapping rather than overflowing.

FORM: User-pinned Starlight structure from the reference repository; no concept round. seed: none (user-pinned).

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Constraints

The showcase and its design system remain unchanged except for a Wiki link. Publish only the eight agreed guides plus the index. No new raster assets. Search is a production-build feature. Markdown links must remain usable without JavaScript; copy failures explain the manual path.
