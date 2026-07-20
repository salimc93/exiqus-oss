# Frontend Development Tooling

## Overview

Our frontend uses a comprehensive set of tools to maintain code quality, consistency, and type safety.

## Tools & Configuration

### 1. **TypeScript**

- Strict type checking enabled
- Run: `npm run typecheck`

### 2. **ESLint**

- Next.js recommended rules
- Custom rules for imports, React hooks, and code style
- Run: `npm run lint` or `npm run lint:fix`

### 3. **Prettier**

- Consistent code formatting
- Tailwind CSS class sorting
- Run: `npm run format` or `npm run format:check`

### 4. **VSCode Integration**

- Auto-format on save
- ESLint auto-fix on save
- Tailwind CSS IntelliSense

## NPM Scripts

```bash
# Development
npm run dev          # Start dev server with Turbopack

# Code Quality
npm run lint         # Run ESLint
npm run lint:fix     # Run ESLint with auto-fix
npm run format       # Format code with Prettier
npm run format:check # Check if code is formatted
npm run typecheck    # TypeScript type checking
npm run check-all    # Run all checks (types, lint, format)

# Build
npm run build        # Production build
npm run start        # Start production server
```

## Pre-commit Hooks

When we add Husky, it will run:

1. ESLint on staged files
2. Prettier on staged files
3. TypeScript type checking

## CI/CD Integration

The GitHub Actions workflow runs:

1. TypeScript type checking
2. ESLint
3. Prettier format check
4. Next.js production build

## Best Practices

### Import Order

Imports are automatically sorted in this order:

1. Built-in modules
2. External dependencies
3. Internal modules (@/)
4. Parent/sibling imports
5. Index imports

### Code Style

- Single quotes for strings
- Semicolons required
- 2-space indentation
- Max line width: 100 characters
- Trailing commas in ES5

### TypeScript

- Avoid `any` types
- Use proper return types
- Prefix unused variables with `_`

### React/Next.js

- Functional components only
- Use hooks properly
- No need to import React (Next.js handles it)

## Tailwind CSS

- Classes are automatically sorted by Prettier
- Use `cn()` or `clsx()` for conditional classes
- VSCode provides IntelliSense for custom classes

## Troubleshooting

### ESLint not working?

```bash
npm run lint -- --debug
```

### Prettier conflicts?

Check `.prettierrc.json` and ensure VSCode is using the project's Prettier

### TypeScript errors?

```bash
npm run typecheck -- --listFiles
```
