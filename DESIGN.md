# Design System: 金羊毛 Argo — Swiss Gallery (Teal & Mint Gray)

## 1. Visual Theme & Atmosphere

An elegant, typographic-first editorial interface inspired by modern Swiss design and premium art galleries. The density sits at **6** — structured, spacious, and highly legible. Variance at **7** — clean card borders, delicate divider lines, and a high-contrast accent color scheme. Motion at **5** — smooth, premium, hardware-accelerated transforms using spring physics. The atmosphere is quiet, minimal, and sophisticated: featuring a mint cool-gray canvas, pure white card fills, and striking **Deep Teal (`#005D53`)** accents.

## 2. Color Palette & Roles

### Light Mode (Default Mode)
- **Mint Gray** (`#EEF5F2`) — Canvas background.
- **Gallery White** (`#FFFFFF`) — Card fill, sidebar, and tray containers.
- **Deep Forest Ink** (`#081A17`) — Primary text and headers.
- **Sage Copy** (`#3F4E4A`) — Body summaries, secondary descriptions.
- **Cool Border** (`#CBDCD6`) — Solid panel borders and divider lines.
- **Recessed Mint** (`#E8F0ED`) — Inactive tags, search inputs, code blocks.
- **Deep Teal** (`#005D53`) — Primary accent. CTAs, active highlights, scores, and active states.
- **Bright Teal** (`#0D9488`) — Hover highlights, bright focuses.
- **Teal Wash** (`#E6F2EE`) — Light wash for active nav items.
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
- No warm ivory/yellowish canvas backgrounds.
- No heavy dark mode gradients.
- No emerald-green accent jumps in dark mode — maintain teal hue continuity.

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
- Never use orange or blue focus rings — always teal-family.

### Verdict Badges
- Use semantic color coding consistently: green = verified, red = rejected, amber = pending.
- Badge borders match text color for reinforcement.
