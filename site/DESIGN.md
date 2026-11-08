---
name: Megabonk Mod Party — Site
description: A creator-first build table for the unofficial Megabonk mod website.
colors:
  table: "#dfeaf0"
  ink: "#26333a"
  muted-ink: "#52626b"
  paper: "#f8f8f2"
  accent: "#b83c29"
  line: "#b7c9d1"
  primary-foreground: "#ffffff"
  secondary: "#cbdde5"
typography:
  display:
    fontFamily: "Archivo, sans-serif"
    fontSize: "clamp(3.1rem, 6.2vw, 6rem)"
    fontWeight: 800
    lineHeight: 1.06
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Archivo, sans-serif"
    fontSize: "clamp(2.1rem, 3.2vw, 3.25rem)"
    fontWeight: 800
    lineHeight: 1.06
    letterSpacing: "-0.035em"
  title:
    fontFamily: "'Public Sans Variable', sans-serif"
    fontSize: "1.1rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "'Public Sans Variable', sans-serif"
    fontSize: "16px"
    lineHeight: 1.65
  label:
    fontFamily: "'Public Sans Variable', sans-serif"
    fontSize: "0.85rem"
    fontWeight: 650
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "0.86rem"
    lineHeight: 1.9
rounded:
  key: "3px"
  control: "5px"
  command: "6px"
spacing:
  compact: "0.5rem"
  base: "1rem"
  related: "1.5rem"
  group: "2rem"
  wide: "3rem"
  section-gap: "6rem"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.primary-foreground}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 1.15rem"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0 1.15rem"
  comparison-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
  screenshot-plate:
    backgroundColor: "{colors.paper}"
    padding: "9px 9px 0"
  command-block:
    backgroundColor: "#1c282e"
    textColor: "#f3f5ed"
    rounded: "{rounded.command}"
    padding: "0 1.25rem 0.65rem"
---

<!-- markdownlint-disable MD025 -->

# Design System: Megabonk Mod Party — Site

## Overview

**Creative North Star: "Build table"**

The website feels like a level being worked on: a pale blue working surface, graphite lettering, paper-backed captures and vermilion actions. Broad left-aligned display type and physical margin notes frame actual game evidence rather than a conventional software sales pitch.

This system applies to the website, not the in-game mod interface. Creators lead; commands and technical setup remain readable supporting material. `src/styles/global.css`, `src/pages/index.astro` and `src/components/` are the implementation references, relative to the `site/` project root.

**Key Characteristics:**

- Real, independently captioned game captures.
- Flat editorial structure with selective paper depth.
- Confident display lettering and readable technical detail.
- Progressive enhancement with complete static content.

## Colors

### Primary

- **Vermilion** (`accent`): primary actions, headline emphasis, annotations and light-surface focus outlines. Primary buttons use white text (`primary-foreground`).

### Neutral

- **Pale blue working surface** (`table`): the page ground.
- **Graphite** (`ink`): primary text and selected comparison controls.
- **Muted graphite** (`muted-ink`): captions, metadata and supporting copy.
- **Annotation paper** (`paper`): screenshot plates, keyboard keys and the starter-level section.
- **Registration line** (`line`): quiet borders and section divisions.
- **Deeper blue surface** (`secondary`): the closing setup section.

The console section reverses to graphite with pale text, lighter dividers and a peach accent. These are local contrast adaptations, not a replacement site palette.

**The White Action Text Rule.** Primary buttons keep white text on vermilion.

## Typography

Archivo supplies display headings and the wordmark; Public Sans Variable supplies body copy, navigation and controls. Monospace is reserved for commands, configuration, filenames and keys.

The frontmatter records the desktop ramp. Body prose is limited to (70ch), hero explanation to (40ch), console prose to (57ch). At the mobile breakpoint, display becomes `clamp(2.9rem, 11vw, 4.5rem)`, section headings become (2.25rem), and body becomes (0.92rem). Captions and utility labels are smaller than body text; they do not become a competing heading tier.

## Layout

The centered container is `min(1296px, 90%)`. Hero copy uses unequal columns (1.5fr / 1fr); feature sections pair copy and evidence (0.9fr / 1.1fr). Desktop section padding is typically (100–112px). Fine rules organize the three-column capability index without turning it into feature cards.

At (1000px), gaps, annotations and section padding tighten. At (700px), copy/media sections become one column, the navigation wraps to a full-width row, the capability index becomes ruled rows, and section padding becomes (64px). Setup actions expand to the available width; compatibility notes and footer flow vertically. Code scrolls horizontally rather than widening the page.

The hero comparison always retains both images. On desktop, the emphasized image occupies the wide column and the other remains a smaller visible plate. Alpine changes emphasis, not availability. On mobile, both images stack in source order and an accent outline identifies the emphasized view. Without JavaScript, both captioned images remain visible and comparison controls stay hidden.

## Elevation & Depth

Most surfaces are flat, separated by tone and fine borders. Screenshot plates alone use a soft paper shadow (`0 13px 32px -15px #26333a55`). Their entrance settles over (650ms) with `cubic-bezier(0.16, 1, 0.3, 1)`, from a slight vertical offset and rotation. Reduced-motion mode removes animation, transitions and smooth scrolling. No decorative background grid is used.

## Shapes

Media plates and section bands are square-edged. Small control corners and slightly softer command containers follow the frontmatter radii. Borders are fine (1px); keyboard focus uses a clear (3px) accent outline offset by (5px). Icons are inline stroked SVG, not text glyphs.

## Components

- **Buttons:** compact and direct, with a (44px) minimum height, rising to (50px) in setup actions. Primary is vermilion/white; outline is transparent/graphite. Hover darkens via `brightness(0.94)`. Text links retain underlines and turn accent on hover.
- **Comparison controls:** outlined buttons (36px minimum height, 0.75rem text); the pressed state is graphite/paper and exposed through `aria-pressed`.
- **Screenshot plates:** paper backing, small inset, uncropped images (`object-fit: contain`, 1512 / 982 ratio) and independent captions. Mobile reduces the inset to (5px); the smaller desktop plate hides only its secondary caption detail.
- **Command blocks:** dark recessed containers with a ruled heading, scrollable monospace examples and a reserved live-feedback line. Progressively added ghost Copy buttons report success or failure; they disable only while copying.
- **Navigation:** small semibold links with underline on hover; mobile wraps rather than replacing links with a hidden menu. A keyboard-visible skip link precedes it.
- **Video posters:** actual captures with a paper “Video coming soon” status label and explanatory caption, not fake playback controls.
- **Disclosures:** native setup details remain keyboard-operable and accessible without JavaScript; summaries have a (52px) minimum height.

## Do's and Don'ts

### Do

- **Do** keep the website system scoped to `site/`.
- **Do** preserve both comparison images, their captions and the no-JavaScript reading path.
- **Do** use real original starter-level captures and label pending videos honestly.
- **Do** retain white primary-button text, visible keyboard focus and reduced-motion fallbacks.

### Don't

- **Don't** replace the build table with a centered sales hero or equal feature-card grid on this landing page.
- **Don't** crop editor or gameplay proof to make the composition fit.
- **Don't** present placeholder posters as playable videos or imply an available public download.
