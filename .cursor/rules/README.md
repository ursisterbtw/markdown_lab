# SVG Design Rules for High-Quality Graphics

This directory contains comprehensive guidelines for creating professional SVG graphics like the `docs/assets/github-banner.svg`. These rules are designed to help LLMs generate consistent, high-quality visual content.

## Rule Files Overview

### 📐 [svg-fundamentals.mdc](./svg-fundamentals.mdc)

Core SVG technical requirements and best practices:

- Proper SVG structure and namespace
- Background foundation patterns
- Gradient and filter definitions
- Performance optimization
- Semantic organization

### 🎨 [design-principles.mdc](./design-principles.mdc)

Modern design aesthetics and visual hierarchy:

- Dark theme first approach
- Color psychology and brand alignment
- Three-column layout patterns
- Professional design elements
- Quality benchmarks

### 🌈 [color-and-gradients.mdc](./color-and-gradients.mdc)

Comprehensive color system and gradient techniques:

- GitHub dark theme palette
- Semantic color roles
- Advanced gradient patterns
- Color accessibility standards
- Brand-specific color schemes

### ✍️ [typography-and-text.mdc](./typography-and-text.mdc)

Typography scales and text styling:

- Font system architecture
- Heading hierarchy and sizing
- Code and technical text styling
- Multi-line text handling
- Accessibility considerations

### ✨ [animations-and-effects.mdc](./animations-and-effects.mdc)

Motion design and visual effects:

- Purposeful animation principles
- Progress indicators and status animations
- Advanced effects (glow, shadows, particles)
- Performance optimization
- Timeline management

### 📏 [layout-and-composition.mdc](./layout-and-composition.mdc)

Grid systems and compositional structure:

- Standard banner dimensions
- Visual weight distribution
- Element positioning systems
- Responsive considerations
- Common layout patterns

## Quick Reference

### Essential Colors

```css
--bg-primary: #0d1117 /* Dark base */ --blue-accent: #58a6ff
    /* Primary actions */ --green-success: #39d353 /* Success states */
    --rust-orange: #ce422b /* Rust branding */ --text-primary: #c9d1d9
    /* Main text */;
```

### Typography Scale

```css
--hero: 64px font-weight: 700 --header: 22px font-weight: 600 --body: 14px
    font-weight: 400 --small: 12px font-weight: 400;
```

### Layout Grid (1280x640)

```css
--header: 0-200px --content: 200-560px --footer: 560-640px --left: 0-400px
    --center: 400-880px --right: 880-1280px;
```

## Usage Guidelines

1. **Start with fundamentals**: Establish proper SVG structure
2. **Apply design principles**: Ensure modern, professional aesthetics
3. **Implement color system**: Use consistent palette and gradients
4. **Set typography**: Apply proper hierarchy and readability
5. **Add subtle animations**: Enhance with purposeful motion
6. **Optimize layout**: Ensure balanced composition

## Quality Checklist

- [ ] Proper SVG namespace and viewBox
- [ ] Dark theme with professional gradients
- [ ] Consistent color usage from defined palette
- [ ] Readable typography with proper hierarchy
- [ ] Subtle, purposeful animations
- [ ] Balanced three-column layout
- [ ] Accessibility considerations met
- [ ] Performance optimized

These rules are based on analysis of the existing `github-banner.svg` and modern design principles for technical/developer-focused graphics.
