Header

**File**: `\_nav.html` — Tailwind CDN + class-based dark mode

| Element | Tag | Tailwind Classes | Notes |
| - | - | - | - |
| Container | `\<nav\>` | `bg-white shadow-sm border-b dark:bg-gray-800` | Full-width, 1px bottom border |
| Inner wrapper | `\<div\>` | `max-w-7xl mx-auto px-4 py-3 flex items-center justify-between` | Centered, horizontal flex |
| Brand | `\<span\>` | `font-bold text-lg text-indigo-600 dark:text-indigo-400` | Text "Poly" (no logo image) |
| Nav links | `\<a\>` | `text-sm text-gray-600 hover:text-indigo-600 dark:text-gray-300 dark:hover:text-indigo-400` | Gap `gap-4` |
| DID badge | `\<span\>` | `text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded-full font-medium dark:bg-purple-900 dark:text-purple-200` | Truncated DID pill |
| Mesh badge | `\<span\>` | `text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded-full font-medium hidden dark:bg-green-900 dark:text-green-200` | Hidden until bridge detected |
| CTA button | `\<a\>` | `text-sm font-bold text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-md hover:bg-indigo-100 border border-indigo-200 dark:bg-indigo-900 dark:text-indigo-200 dark:border-indigo-700 dark:hover:bg-indigo-800` | "Return to Social Feed" |
| Logout | `\<button\>` | `text-sm text-red-500 hover:text-red-700 bg-transparent border-none cursor-pointer dark:text-red-400 dark:hover:text-red-300` | No padding |
| Login | `\<a\>` | `text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300` | When unauthenticated |


**Mesh badge JS**: On DOMContentLoaded, `fetch("http://127.0.0.1:9001/")` with 300ms timeout — if OK, remove `hidden`.


## Footer

**File**: `footer.html`

| Element | Classes | Notes |
| - | - | - |
| `\<footer\>` | `bg-white dark:bg-gray-800 shadow-inner mt-8` | Inset shadow on top |
| Inner wrapper | `max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8 flex justify-between items-center` | Same max-w as header |
| Left group | `flex items-center gap-3` | Logo + copyright |
| Poly logo | `\<img id="footer-poly-logo" class="h-24" data-light data-dark\>` | Swaps `src` on dark mode |
| Copyright | `\<p\>` | `text-sm text-gray-500 dark:text-gray-400` |
| Right logo | `\<img id="footer-logo" class="h-24"\>` | "Created in DeKalb" |


**Dark mode image swap**: Both `\#footer-poly-logo` and `\#footer-logo` use `data-light`/`data-dark` attributes. An IIFE sets `src` on load. The theme toggle in `base.html` also updates them on click.


## Global Dark Mode

**Base.html** (lines 17–23): Flash-prevention script runs before render:

```
if (localStorage.getItem('color-theme') === 'dark' ||  
    (!('color-theme' in localStorage) &&  
     window.matchMedia('(prefers-color-scheme: dark)').matches)) \{  
    document.documentElement.classList.add('dark');  
\}
```

**CSS Variables**: `:root` for light, `html.dark` for dark — `--bg-color`, `--text-color`, `--primary-color`, `--bg-secondary`, `--border-color`, etc.

**Tailwind overrides** (lines 64–88): `html.dark .bg-white \{ background-color: var(--bg-secondary) !important; \}` etc. to force standard Tailwind classes to respect the CSS variable system.

**Theme toggle button** (anywhere in page): `id="theme-toggle"` — onclick toggles `dark` class on `\<html\>`, updates localStorage, swaps logo `src` for both `\#footer-poly-logo` and `\#footer-logo`.

