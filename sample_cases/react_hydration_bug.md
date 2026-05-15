# React Hydration Mismatch

## Case Details
Language/framework: React, Next.js
Environment: Production browser, server-rendered app

## Actual Behavior
Users see a hydration warning on reload. Some page sections briefly flicker and then show different timestamps.

## Expected Behavior
The server-rendered page and client-rendered page should match after reload.

## Logs
Warning: Text content did not match. Server: "10:41 AM" Client: "10:42 AM"
Hydration failed because the initial UI does not match what was rendered on the server.

## Code Snippet
```tsx
export function Header() {
  return (
    <header>
      <span>Last updated: {new Date().toLocaleTimeString()}</span>
    </header>
  );
}
```

## Environment Details
Next.js 14, React 18, SSR enabled.
