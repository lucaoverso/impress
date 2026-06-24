---
name: Suíte Escolar
colors:
  surface: '#f7faf8'
  surface-dim: '#d8dbd9'
  surface-bright: '#f7faf8'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f1f4f3'
  surface-container: '#eceeed'
  surface-container-high: '#e6e9e7'
  surface-container-highest: '#e0e3e1'
  on-surface: '#191c1c'
  on-surface-variant: '#3f4947'
  inverse-surface: '#2d3130'
  inverse-on-surface: '#eff1f0'
  outline: '#6f7977'
  outline-variant: '#bec9c6'
  surface-tint: '#1a6962'
  primary: '#00433d'
  on-primary: '#ffffff'
  primary-container: '#005c55'
  on-primary-container: '#8ad2c8'
  inverse-primary: '#8cd4ca'
  secondary: '#4f6072'
  on-secondary: '#ffffff'
  secondary-container: '#d2e4fa'
  on-secondary-container: '#556678'
  tertiary: '#622a11'
  on-tertiary: '#ffffff'
  tertiary-container: '#7f4025'
  on-tertiary-container: '#ffb395'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#a7f0e6'
  primary-fixed-dim: '#8cd4ca'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#00504a'
  secondary-fixed: '#d2e4fa'
  secondary-fixed-dim: '#b7c8dd'
  on-secondary-fixed: '#0b1d2c'
  on-secondary-fixed-variant: '#37485a'
  tertiary-fixed: '#ffdbce'
  tertiary-fixed-dim: '#ffb598'
  on-tertiary-fixed: '#370e00'
  on-tertiary-fixed-variant: '#72361b'
  background: '#f7faf8'
  on-background: '#191c1c'
  surface-variant: '#e0e3e1'
  primary-strong: '#0b5b55'
  primary-soft: '#d6f2ef'
  success: '#16a34a'
  danger: '#dc2626'
  border-soft: '#d8e1ec'
typography:
  display-lg:
    fontFamily: Nunito Sans
    fontSize: 34px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Nunito Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Nunito Sans
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Nunito Sans
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 22px
  body-md:
    fontFamily: Nunito Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-sm:
    fontFamily: Nunito Sans
    fontSize: 14px
    fontWeight: '700'
    lineHeight: 18px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  xs: 4px
  sm: 8px
  md: 12px
  lg: 16px
  xl: 24px
  xxl: 32px
  gutter: 16px
  margin: 24px
---

## Brand & Style
The brand personality is **trustworthy, organized, and academic**. It targets school administrators and teachers who require a tool that feels professional yet approachable and efficient. 

The design style is **Corporate Modern**, utilizing a structured layout inspired by Material Design 3. It emphasizes clarity through a clean, systematic interface, soft tonal layering, and high legibility. The emotional response should be one of "calm productivity"—reducing the cognitive load of complex administrative tasks through a soothing teal-based palette and generous whitespace.

## Colors
The color palette centers on a **Deep Teal Primary**, conveying stability and focus. 
- **Primary:** Used for main actions, active states, and brand identifiers.
- **Secondary:** A muted blue-grey for supporting information and secondary navigation elements.
- **Background:** A warm, off-white/bone neutral (`#f2efe9`) that reduces eye strain compared to pure white.
- **Semantic Colors:** Green (`success`) for availability, Red (`danger`) for alerts/errors, and Light Teal (`primary-soft`) for subtle backgrounds and hover states.
- **Neutral Surfaces:** The system uses a range of "Surface Containers" (Low to Highest) to create subtle depth without relying on heavy shadows.

## Typography
The system uses **Nunito Sans** across all roles to maintain a friendly yet professional tone. 
- **Headlines:** Use tight letter-spacing and bold weights to establish clear information hierarchy.
- **Display sizes:** Scale down by approximately 15-20% on mobile devices to maintain screen real estate.
- **Labels:** Always semi-bold or bold to distinguish between actionable metadata and general body text.
- **Body Text:** Standardized at 16px for optimal readability in data-rich environments.

## Layout & Spacing
The layout follows a **Fixed Grid Strategy** for desktop, centering a 1024px maximum width canvas. On mobile, the system transitions to a fluid model with 16px side margins.

- **Navigation:** A fixed 256px left-hand sidebar on desktop, which collapses into a hamburger menu on mobile.
- **Grid:** Content uses a "Bento Box" approach where items are grouped into distinct white cards with 16px gutters between them.
- **Rhythm:** An 8px base unit is used for all internal component spacing and external margins to ensure mathematical consistency.

## Elevation & Depth
Depth is achieved primarily through **Tonal Layering** and **Subtle Ambient Shadows**.

- **Level 0 (Background):** The warm neutral base.
- **Level 1 (Cards/Sidebar):** Pure white surfaces with a thin `border-soft` (1px) and a `shadow-sm` for definition.
- **Level 2 (Active/Hover):** When an item is focused or hovered, it utilizes `shadow-md` to appear "lifted" toward the user.
- **Outlines:** Used extensively in form fields and button containers to provide structure without excessive shadow use, keeping the UI light and airy.

## Shapes
The system uses a **Soft Geometry** approach.
- **Standard Elements:** Buttons and input fields use a 0.25rem (4px) or 0.5rem (8px) radius.
- **Containers:** Content cards and larger sections use a 0.75rem (12px) radius to feel more approachable.
- **Icons/Avatars:** Circular shapes are reserved for user profiles and specific notification badges to contrast with the otherwise rectilinear layout.

## Components
- **Buttons:** Primary buttons are solid Teal with White text and a slight shadow. Secondary buttons are transparent with a Teal border or subtle `primary-soft` background.
- **Inputs:** Soft-grey backgrounds with 1px borders that transition to Teal on focus.
- **Cards (Bento Style):** White backgrounds, 12px corner radius, 1px light border. Content inside cards should be separated by thin dividers or clear vertical spacing.
- **Stepper:** Use a horizontal line with circular indicators. Completed steps are solid Teal with a checkmark; active steps have a thicker border; inactive steps are muted grey.
- **Chips/Badges:** Use `surface-container-low` with rounded-full corners for metadata (e.g., "Adaptador HDMI").
- **Navigation:** Active sidebar items use a "Tonal Fill" (light teal) to indicate current location clearly.