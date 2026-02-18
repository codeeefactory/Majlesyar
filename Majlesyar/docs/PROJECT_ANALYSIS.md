# Project Analysis

## 1) Frontend Framework

This repository uses **React** (not Vue), built with **Vite + TypeScript**.

## 2) Tech Stack and Build Tooling

- Runtime/UI:
  - React 18
  - React Router v6
  - Tailwind CSS
  - shadcn/ui + Radix UI primitives
  - Sonner (toasts)
- Build tooling:
  - Vite 5 (`@vitejs/plugin-react-swc`)
  - TypeScript
  - ESLint
- SEO/meta:
  - `react-helmet-async`
- Current data source:
  - `src/lib/api.ts` + `src/lib/storage.ts` (localStorage-backed mock API)
  - static defaults from `src/data/mockData.ts`

## 3) Route Map

Defined in `src/App.tsx`:

- `/` -> `src/pages/HomePage.tsx`
- `/shop` -> `src/pages/ShopPage.tsx`
- `/product/:id` -> `src/pages/ProductPage.tsx`
- `/events/:slug` -> `src/pages/EventPage.tsx`
- `/builder` -> `src/pages/BuilderPage.tsx`
- `/cart` -> `src/pages/CartPage.tsx`
- `/checkout` -> `src/pages/CheckoutPage.tsx`
- `/order/:id` -> `src/pages/OrderPage.tsx`
- `/track` -> `src/pages/TrackOrderPage.tsx`
- `/contact` -> `src/pages/ContactPage.tsx`
- `/about` -> `src/pages/AboutPage.tsx`
- `/admin/login` -> `src/pages/admin/AdminLoginPage.tsx`
- `/admin/orders` -> `src/pages/admin/AdminOrdersPage.tsx`
- `/admin/orders/:id` -> `src/pages/admin/AdminOrdersPage.tsx` (same page component)
- `*` -> `src/pages/NotFound.tsx`

## 4) State Management / Contexts / Stores

- `SettingsContext` (`src/contexts/SettingsContext.tsx`)
  - Loads settings via `getSettings()` from `src/lib/api.ts`
  - Provides `settings`, `loading`, `refreshSettings`
- `CartContext` (`src/contexts/CartContext.tsx`)
  - Manages in-memory cart state and persists it to localStorage
  - Exposes totals and minimum quantity checks
  - Currently hard-codes `minQuantityRequired = 40`
- `AdminAuthContext` (`src/contexts/AdminAuthContext.tsx`)
  - Uses `adminLogin`, `adminLogout`, `isAdminLoggedIn` from `src/lib/api.ts`
  - Current auth is localStorage-based mock auth (`admin/admin123`)
- Local storage abstraction:
  - `src/lib/storage.ts` wraps `localStorage` with schema versioning and prefixed keys

## 5) Current API Layer Usage

Current API module: `src/lib/api.ts`

- Simulates async network delay
- Reads/writes localStorage through `storage` helper
- Falls back to mock defaults from `src/data/mockData.ts`
- Contains product/category/builder/settings/order/admin-auth functions
- Order tracking and admin order updates are entirely client-side

Where it is used:

- Products/categories: `ShopPage`, `ProductPage`, `EventPage`
- Builder config: `BuilderPage`
- Settings: `SettingsContext`, then used by `CheckoutPage`
- Orders: `CheckoutPage`, `OrderPage`, `TrackOrderPage`, `AdminOrdersPage`
- Admin auth: `AdminAuthContext`, `AdminLoginPage`, `AdminOrdersPage`

Non-API static data still used directly:

- `HomePage` uses static `products` from `mockData.ts`
- `eventTypes` and `allProvinces` come from `mockData.ts`

## 6) Inferred Domain Model

Inferred from `src/data/mockData.ts` and usage:

- Category:
  - `id`, `name`, `slug`, `icon`
- Product:
  - `id`, `name`, `description`, `price | null`, `categoryIds[]`, `eventTypes[]`, `contents[]`, `image`, `featured`, `available`
- BuilderItem:
  - `id`, `name`, `group` (`packaging|fruit|drink|snack|addon`), `price`, `required`, `image?`
- Settings:
  - `minOrderQty`, `leadTimeHours`, `allowedProvinces[]`, `deliveryWindows[]`, `paymentMethods[]`
- Order:
  - `id` (public code), `items[]`, `customer`, `delivery`, `paymentMethod`, `status`, `total`, `createdAt`, `notes[]`
- OrderItem:
  - `productId`, `name`, `quantity`, `price`, `isCustomPack?`, `customConfig?`

## 7) Gaps / Risks and Integration Plan

Current gaps:

- No real backend persistence; data is browser-local only.
- Admin auth is insecure mock logic.
- Order statuses can be mutated client-side.
- Multi-client consistency does not exist.
- Home page uses static product list and bypasses API module.
- Admin order detail route (`/admin/orders/:id`) is not implemented as detail UI.

Risks during integration:

- Frontend expects camelCase objects; DRF defaults to snake_case.
- Existing UI assumes function signatures in `src/lib/api.ts`.
- Checkout validation uses settings and province constraints that must match server rules.
- Date handling includes Jalali picker but stores Gregorian strings.

Integration plan:

- Add a Django backend (`backend/`) with DRF, JWT, CORS, drf-spectacular, and Unfold admin.
- Implement domain apps: `catalog`, `site_settings`, `orders`.
- Seed DB from current `mockData.ts` values via `backend/seed/initial_data.json` + management command.
- Keep frontend API function names, but replace internals with HTTP calls.
- Add `src/lib/http.ts` for base URL, JSON headers, JWT handling, and standardized errors.
- Move admin auth to JWT token endpoints and protect admin API routes with `is_staff`.
- Replace order creation/tracking and settings/product reads with backend endpoints.
- Keep UI/UX unchanged except necessary integration behavior (e.g., status simulation hidden unless dev + admin token).
