---
name: Kinetic Utility
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1b1b1b'
  on-surface-variant: '#414755'
  inverse-surface: '#303030'
  inverse-on-surface: '#f1f1f1'
  outline: '#727786'
  outline-variant: '#c1c6d7'
  surface-tint: '#0059c7'
  primary: '#0057c2'
  on-primary: '#ffffff'
  primary-container: '#006ef2'
  on-primary-container: '#fefcff'
  inverse-primary: '#afc6ff'
  secondary: '#5d5f5f'
  on-secondary: '#ffffff'
  secondary-container: '#dcdddd'
  on-secondary-container: '#5f6161'
  tertiary: '#9e3d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#c64f00'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d9e2ff'
  primary-fixed-dim: '#afc6ff'
  on-primary-fixed: '#001a43'
  on-primary-fixed-variant: '#004398'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c7'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#454747'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb695'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7c2e00'
  background: '#f9f9f9'
  on-background: '#1b1b1b'
  surface-variant: '#e2e2e2'
  surface-white: '#FFFFFF'
  border-subtle: '#E5E5E5'
  text-muted: '#595959'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
  max-width: 1200px
---

## Brand & Style
This design system is built on a foundation of **Corporate Modernism** with a heavy emphasis on utility and efficiency. The brand personality is clinical, reliable, and high-performance, designed for users who prioritize speed and clarity in data-driven tasks.

The aesthetic utilizes a high-contrast relationship between deep blues and stark whites, balanced by neutral grays to reduce visual fatigue. The style focuses on "functional minimalism"—where every visual element serves a direct purpose in the user's workflow. Layouts are spacious and structured, evoking the feeling of a well-organized workspace.

## Colors
The color palette is anchored by a vibrant **Electric Blue** (#1677FF) used exclusively for primary actions and interactive states. 

- **Primary:** Used for the "Start Analysis" actions, active tab indicators, and progress states.
- **Backgrounds:** A tiered system of `#FFFFFF` for primary cards and `#F5F5F5` for the global canvas to create soft depth without heavy shadows.
- **Typography:** Pure black (#000000) is reserved for high-level headings, while `#595959` is used for body copy and secondary metadata to maintain a clean, airy feel.

## Typography
The system uses **Hanken Grotesk** as the primary typeface—a sharp, contemporary sans-serif that balances Swiss-style neutrality with modern approachability. 

- **Headlines:** Use tight letter-spacing and bold weights to command attention.
- **Body:** Generous line heights ensure readability during long analysis sessions.
- **Labels:** **JetBrains Mono** is introduced for technical data points, IDs, and secondary labels to reinforce the "tooling" and "utility" nature of the application.

## Layout & Spacing
The layout follows a **Fixed Grid** model for desktop and a fluid model for mobile. 

- **Desktop:** 12-column grid with a max-width of 1200px, centered. 
- **Mobile:** Single column with 16px side margins.
- **Rhythm:** An 8px linear scale is used for all spacing. Gutters are fixed at 24px to provide a breathable buffer between data cards.
- **Reflow:** Components stack vertically on mobile, with horizontal tab navigation switching to a scrollable list if items exceed the viewport width.

## Elevation & Depth
This design system eschews heavy shadows in favor of **Tonal Layers** and **Low-contrast Outlines**.

- **Level 0 (Canvas):** `#F5F5F5` background.
- **Level 1 (Cards/Inputs):** `#FFFFFF` surface with a 1px solid border of `#E5E5E5`.
- **Level 2 (Hover/Active):** A very subtle, diffused shadow (0px 4px 12px rgba(0,0,0,0.05)) is applied only when a user interacts with a card or button to indicate lift.
- **Interaction:** Active inputs use a 2px blue ring with 20% opacity to highlight focus without cluttering the UI.

## Shapes
The shape language is consistently **Rounded**, using an 8px (0.5rem) base radius to soften the technical nature of the content. 

- **Inputs & Buttons:** Use the standard 8px radius.
- **Main Layout Cards:** Use `rounded-xl` (1.5rem/24px) to define major content areas.
- **Selection Indicators:** Tab underlines and small badges use a "pill" radius for distinct visual contrast against rectangular containers.

## Components

### Buttons
- **Primary:** Solid `#1677FF` with white text. High-padding (12px 24px) for a "large" feel.
- **Secondary:** Transparent with `#1677FF` border and text.
- **States:** 10% black overlay on hover; 20% black overlay on active/press.

### Input Fields
- **Search/Analysis Bar:** Large height (56px), white background, 1px border. Font size should be 18px to match `body-lg`. Placeholder text in `#8C8C8C`.

### Card-Based Layout
- The "Main Tool" container should be a large, elevated card with 32px of internal padding. It acts as the staging area for all primary interactions.

### Tab Navigation
- Positioned above the main tool card.
- **Style:** Minimalist text-only tabs. The active state is indicated by a 3px thick `#1677FF` horizontal bar positioned at the bottom of the tab, with the text color shifting to black.

### List Items
- Clean, 1px border-bottom separation. Each row should have a subtle hover state using `#F5F5F5`.
- Icons within lists should be monolinear and use the primary blue for emphasis.