# Exiqus Design System

A modern, sophisticated design language for evidence-based developer assessment

## Core Principles

1. **Clarity over decoration** - Every element should have a purpose
2. **Sophisticated simplicity** - Clean but not boring
3. **Performance-focused** - Fast interactions, smooth animations
4. **Evidence-based** - Let data speak without embellishment

## Color Palette

### Background Colors

```css
--bg-primary: #0a0a0a; /* Main background - near black */
--bg-secondary: #111111; /* Card backgrounds */
--bg-tertiary: #1a1a1a; /* Hover states */
--bg-accent: #0d0d0d; /* Subtle contrast */
```

### Text Colors

```css
--text-primary: #fafafa; /* Primary text */
--text-secondary: #a8a8a8; /* Secondary text */
--text-tertiary: #6e6e6e; /* Muted text */
--text-accent: #e5e5e5; /* Emphasis */
```

### Brand Colors

```css
--brand-purple: #8b5cf6; /* Primary brand */
--brand-blue: #3b82f6; /* Secondary brand */
--brand-gradient: linear-gradient(to right, #8b5cf6, #3b82f6);
```

### Semantic Colors

```css
--success: #10b981; /* Green */
--warning: #f59e0b; /* Amber */
--error: #ef4444; /* Red */
--info: #3b82f6; /* Blue */
```

### Subtle Accents

```css
--border-subtle: rgba(255, 255, 255, 0.06);
--border-default: rgba(255, 255, 255, 0.09);
--border-strong: rgba(255, 255, 255, 0.12);
```

## Typography

### Font Stack

```css
font-family:
  'Inter var',
  -apple-system,
  BlinkMacSystemFont,
  'Segoe UI',
  Roboto,
  sans-serif;
```

### Type Scale

```css
--text-xs: 0.75rem; /* 12px */
--text-sm: 0.875rem; /* 14px */
--text-base: 1rem; /* 16px */
--text-lg: 1.125rem; /* 18px */
--text-xl: 1.25rem; /* 20px */
--text-2xl: 1.5rem; /* 24px */
--text-3xl: 1.875rem; /* 30px */
--text-4xl: 2.25rem; /* 36px */
```

### Font Weights

```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

## Spacing System

```css
--space-1: 0.25rem; /* 4px */
--space-2: 0.5rem; /* 8px */
--space-3: 0.75rem; /* 12px */
--space-4: 1rem; /* 16px */
--space-5: 1.25rem; /* 20px */
--space-6: 1.5rem; /* 24px */
--space-8: 2rem; /* 32px */
--space-10: 2.5rem; /* 40px */
--space-12: 3rem; /* 48px */
--space-16: 4rem; /* 64px */
```

## Component Patterns

### Cards

```tsx
// Minimal card with subtle border
<div className="bg-[#111111] border border-white/[0.06] rounded-lg p-6 hover:border-white/[0.09] transition-all duration-200">
  {/* Content */}
</div>

// Interactive card with hover state
<div className="group bg-[#111111] border border-white/[0.06] rounded-lg p-6 hover:bg-[#1A1A1A] hover:border-white/[0.12] transition-all duration-200 cursor-pointer">
  {/* Content */}
</div>
```

### Buttons

```tsx
// Primary button
<button className="bg-gradient-to-r from-purple-600 to-blue-600 text-white px-4 py-2 rounded-md font-medium hover:opacity-90 transition-opacity">
  Action
</button>

// Secondary button
<button className="bg-white/[0.06] hover:bg-white/[0.09] text-white px-4 py-2 rounded-md font-medium border border-white/[0.09] transition-all">
  Secondary
</button>

// Ghost button
<button className="text-gray-400 hover:text-white px-4 py-2 rounded-md font-medium transition-colors">
  Ghost
</button>
```

### Badges

```tsx
// Status badges
<span className="inline-flex items-center rounded-md border border-green-500/20 bg-green-500/10 px-2 py-1 text-xs font-medium text-green-400">
  Active
</span>
```

### Navigation

```tsx
// Tab navigation (Linear style)
<div className="flex items-center gap-1 rounded-lg bg-white/[0.03] p-1">
  <button className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-400 transition-colors hover:text-white data-[active=true]:bg-white/[0.06] data-[active=true]:text-white">
    Tab 1
  </button>
</div>
```

## Animation Guidelines

```css
/* Micro-interactions */
--transition-fast: 150ms ease;
--transition-base: 200ms ease;
--transition-slow: 300ms ease;

/* Hover states should be subtle */
opacity: 0.9;
transform: translateY(-1px);

/* Focus states should be clear but not jarring */
outline: 2px solid var(--brand-purple);
outline-offset: 2px;
```

## Layout Principles

1. **Maximum content width**: 1280px
2. **Card spacing**: 24px (gap-6)
3. **Section spacing**: 48px (gap-12)
4. **Edge padding**: 24px on mobile, 48px on desktop

## Icon Usage

- Use Lucide React icons
- Consistent 20px size for UI icons
- 16px for inline/small icons
- 24px for feature/hero icons

## Best Practices

1. **Avoid pure white** - Use #FAFAFA for better readability
2. **Subtle is better** - Prefer opacity changes over color changes
3. **Consistent radii** - Use rounded-md (6px) for most elements
4. **Depth through opacity** - Use white/[0.XX] for layering
5. **Motion with purpose** - Animate only to guide attention

## Example Component Structure

```tsx
// Page layout
<div className="min-h-screen bg-[#0A0A0A] text-white">
  <div className="max-w-7xl mx-auto px-6 lg:px-12 py-12">
    {/* Page content */}
  </div>
</div>

// Section
<section className="space-y-6">
  <div className="space-y-2">
    <h2 className="text-2xl font-semibold">Section Title</h2>
    <p className="text-gray-400">Section description</p>
  </div>
  {/* Section content */}
</section>

// Feature card
<div className="group relative overflow-hidden bg-[#111111] border border-white/[0.06] rounded-lg p-6 hover:border-white/[0.12] transition-all duration-200">
  <div className="absolute inset-0 bg-gradient-to-br from-purple-600/5 to-blue-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
  <div className="relative">
    {/* Card content */}
  </div>
</div>
```

## Tailwind Config Additions

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        gray: {
          950: '#0A0A0A',
          925: '#111111',
          900: '#1A1A1A',
        },
      },
      animation: {
        'fade-in': 'fadeIn 200ms ease',
        'slide-up': 'slideUp 300ms ease',
      },
    },
  },
};
```
