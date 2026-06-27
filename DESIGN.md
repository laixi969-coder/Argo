# Design System: 金羊毛 Argo — Swiss Gallery (Klein Blue & Cool Gray)

## 1. Visual Theme & Atmosphere

An elegant, typographic-first editorial interface inspired by modern Swiss design and premium art galleries. The density sits at **6** — structured, spacious, and highly legible. Variance at **7** — clean card borders, delicate divider lines, and a high-contrast accent color scheme. Motion at **5** — smooth, premium, hardware-accelerated transforms using spring physics. The atmosphere is quiet, minimal, and sophisticated: featuring a cement cool-gray canvas, pure white card fills, and striking **International Klein Blue (`#002FA7`)** accents.

## 2. Color Palette & Roles

### Light Mode (Default Mode)
- **Cement Gray** (`#E9ECEF`) — Canvas background.
- **Gallery White** (`#FFFFFF`) — Card fill, sidebar, and tray containers.
- **Deep Slate Ink** (`#0B0F19`) — Primary text and headers.
- **Slate Copy** (`#4B5563`) — Body summaries, secondary descriptions.
- **Cool Border** (`#CBD5E1`) — Solid panel borders and divider lines.
- **Recessed Light** (`#F1F5F9`) — Inactive tags and search inputs.
- **International Klein Blue** (`#002FA7`) — Primary accent. CTAs, active highlights, scores, and active states.
- **Saturated Blue** (`#1D4ED8`) — Hover highlights, bright blue focuses.
- **Klein Wash** (`#EEF2FF`) — Saturated light blue wash for active nav items.
- **Verdict Green** (`#065F46` on `#D1FAE5`) — Verified opportunity badges.
- **Verdict Red** (`#991B1B` on `#FEE2E2`) — Rejected/false-opportunity badges.
- **Verdict Amber** (`#92400E` on `#FEF3C7`) — Pending/unverified badges.

### Dark Mode (Swiss Midnight variant)
- **Midnight Canvas** (`#0B0F19`) — Deep blue-grey background canvas.
- **Midnight Card** (`#1A1F2E`) — Dark cards and panels.
- **Crisp Off-White** (`#F1F5F9`) — Primary text and headers.
- **Muted Silver** (`#94A3B8`) — Secondary copy.
- **Dark Border** (`#262D3D`) — Slate borders.
- **Vivid Klein Blue** (`#2D60FF`) — Accent highlight.
- **Glowing Blue** (`#60A5FA`) — Hover highlight.
- **Midnight Wash** (`#1B2234`) — Background wash for active nav items.

**Hard Bans:**
- No complex gradients or neon glow effects on cards.
- No warm ivory/yellowish canvas backgrounds.
- No heavy dark mode gradients.

## 3. Typography Rules

- **Display & Headings:** Sans-serif stack `"SF Pro SC", system-ui, sans-serif` — heavy weights (`font-weight: 800`), track-tight (`letter-spacing: -0.5px`).
- **Body & Metadata:** Clean sans-serif stack — `"SF Pro SC", system-ui, sans-serif` — `15px / 1.65` line-height for maximum editorial readability.
- Monospace stack (`var(--font-mono)`) is reserved for raw codes, lists, indicators, and scores to keep an elegant contrast.

## 4. Component Stylings

### Buttons
- **Primary CTA (`.cta`):** International Klein Blue fill (`#002FA7`), white text, rounded corners (`border-radius: 4px`). Active state `translateY(1px)`.
- **Secondary / Ghost (`.savebtn`):** `1px solid var(--line)` border, transparent fill. Active toggle state: Klein Wash background + Klein Blue text.

### Cards (`article`)
- Flat card containers with `border-radius: 4px` and `1px solid var(--line)`.
- Hover: Soft gallery-style lift (`box-shadow: 0 8px 20px rgba(0, 47, 167, 0.04)`), and border changes to International Klein Blue (`#002FA7`).
