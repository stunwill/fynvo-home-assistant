# Fynvo v1.9.3

## Mobile Navigation Hotfix

v1.9.3 fixes the mobile/Home Assistant navigation drawer regression visible after v1.9.2.

### Fixed

- Restored the mobile drawer close control to an absolutely positioned control in the top-right of the drawer.
- Removed the close control from the drawer's flex-flow positioning rules, which had stretched and displaced it into the brand/navigation layout.
- Kept the drawer above its backdrop while preserving tap handling, focus management, background scroll locking and responsive drawer widths.
- Added regression coverage to prevent later layering rules from overriding the close control's positioning again.

### Root cause

The later v1.4.3 layering stylesheet grouped `.mobile-nav-close` with normal sidebar content and applied `position: relative`. Because that stylesheet loads after the base mobile navigation stylesheet, it overrode the intended `position: absolute` close-button rule. In the mobile flex-column sidebar this made the close control participate in layout, stretch across the drawer and visually overlap/displace the Fynvo brand area.

No database or backend data migration is required.
