# Design System: 金羊毛 Argo — Petrol & Copper

> 配色取自落地页 hero 视频（高光 3D 流体）：雾蓝灰底 + 深孔雀蓝 + 古铜橙。全站变量见 `src/web.py` 的 `:root`，这里是权威说明，改色先改这两处。

## 1. Visual Theme & Atmosphere

An elegant, typographic-first editorial interface. The density sits at **6** — structured, spacious, and highly legible. Motion at **5** — smooth, premium, hardware-accelerated transforms with spring physics. Atmosphere: quiet and cinematic. The public landing leads with a full-bleed **muted, looping hero video** (the glossy petrol/copper fluid render) inside a rounded dark panel; the rest of the site is a calm **dusty blue-gray** canvas with white cards and **copper** accents.

## 2. Color Palette & Roles

### Light Mode (Default Mode) — maps 1:1 to `:root` in `src/web.py`
- **Dusty Blue-Gray** (`#EAEEF1`, `--bg`) — Canvas background.
- **White** (`#FFFFFF`, `--card`) — Card fill, sidebar, tray containers.
- **Petrol Ink** (`#12303A`, `--ink`) — Primary text and headers.
- **Blue-Gray Copy** (`#465A64`, `--soft`) — Body summaries, secondary descriptions.
- **Cool Border** (`#CDD8DE`, `--line`) — Panel borders and divider lines.
- **Recessed Blue** (`#E3EAEE`, `--rec`) — Inactive tags, search inputs, code blocks.
- **Burnt Copper** (`#B15A2B`, `--gold`) — Primary accent. CTAs, active highlights, scores, active states.
- **Bright Copper** (`#CF6F37`, `--goldbright`) — Hover highlights.
- **Copper Wash** (`#F3E6DC`, `--amber`) — Light wash for active nav items.
- **Hero text:** white headings, copper-amber em (`#E8954E`) / kicker (`#E8B48A`), over a dark scrim — see `.lhero` in `_LAND_CSS`.
- **Verdict Green** (`#065F46` on `#D1FAE5`) — Verified opportunity badges.
- **Verdict Red** (`#991B1B` on `#FEE2E2`) — Rejected/false-opportunity badges.
- **Verdict Amber** (`#92400E` on `#FEF3C7`) — Pending/unverified badges.

### Dark Mode (Forest Midnight variant)
- **Midnight Forest** (`#08120E`) — Deep green-grey background canvas.
- **Dark Forest Card** (`#111F18`) — Dark cards and panels.
- **Crisp Mint White** (`#F0F7F4`) — Primary text and headers.
- **Muted Sage** (`#91A79F`) — Secondary copy.
- **Dark Border** (`#1E3027`) — Forest borders.
- **Vivid Teal** (`#0D9488`) — Accent highlight (same hue as light-mode hover).
- **Bright Teal** (`#34D399`) — Hover highlight.
- **Midnight Wash** (`#132C21`) — Background wash for active nav items.

**Hard Bans:**
- No complex gradients or neon glow effects on cards.
- No warm ivory/yellowish canvas — canvas stays cool dusty blue-gray.
- Accent stays in the **copper** family; don't drift to red, yellow, or teal-green. Verdict badges (green/red/amber) are semantic exceptions and keep their meaning.
- Hero video must stay muted, looping, `playsinline`, with the dark scrim — never autoplay sound.

## 3. Typography Rules

- **Display & Headings:** System sans-serif stack `-apple-system, BlinkMacSystemFont, "SF Pro SC", "PingFang SC", system-ui, sans-serif` — heavy weights (`font-weight: 800`), track-tight (`letter-spacing: -0.5px`).
- **Body & Metadata:** Same stack — `15px / 1.65` line-height for maximum editorial readability.
- Monospace stack (`ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace`) is reserved for raw codes, scores, and indicators to maintain elegant contrast.

## 4. Component Stylings

### Buttons
- **Primary CTA (`.cta`):** Deep Teal fill (`#005D53`), white text, rounded corners (`border-radius: 4px`). Active state `translateY(1px)`.
- **Secondary / Ghost (`.savebtn`):** `1px solid var(--line)` border, transparent fill. Active toggle state: Verdict Green background + green text.

### Cards (`article`)
- Flat card containers with `border-radius: 4px` and `1px solid var(--line)`.
- Hover: Soft gallery-style lift (`box-shadow: 0 8px 20px rgba(0, 93, 83, 0.06)`), and border changes to Deep Teal (`#005D53`).

### Focus States
- All focusable elements: `box-shadow: 0 0 0 3px rgba(0, 93, 83, 0.15)` with `border-color: var(--goldbright)`.
- Focus rings use the copper accent (`--gold`), never teal or red.

### Verdict Badges
- Use semantic color coding consistently: green = verified, red = rejected, amber = pending.
- Badge borders match text color for reinforcement.
