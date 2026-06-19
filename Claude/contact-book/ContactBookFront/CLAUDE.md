# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
npm run dev       # start dev server (http://localhost:5173)
npm run build     # type-check + production build
npm run preview   # serve production build locally
```

No test runner or linter is configured.

TypeScript type-checking only (no emit):
```bash
npx tsc --noEmit
```

## Architecture

**Stack:** React 19, TypeScript (strict), Vite 6, Tailwind CSS v4, React Router v7, Axios.

**Backend proxy:** Vite proxies all `/api` requests to `http://localhost:8080` (the Spring Boot backend). The `VITE_API_BASE_URL` env var overrides the base URL for the Axios client.

**Request flow:**
```
src/api/client.ts        — Axios instance (baseURL from VITE_API_BASE_URL or '')
src/api/contactsApi.ts   — typed CRUD methods (list, get, create, update, remove)
src/types/contact.ts     — Contact, ContactRequest, ProblemDetail interfaces
```

**Routing (React Router v7 `createBrowserRouter`):**
```
/                → redirect to /contacts
/contacts        → ContactsPage   (list + client-side search + inline delete)
/contacts/new    → ContactFormPage (create mode)
/contacts/:id    → ContactDetailPage
/contacts/:id/edit → ContactFormPage (edit mode, :id present → isEdit=true)
```

`Layout.tsx` renders the app shell (header + `<Outlet />`). All routes are children of the root `/` route.

**`ContactFormPage`** serves both create and edit: presence of the `:id` param determines mode. On submit it navigates to `/contacts/:id` (edit) or `/contacts` (create).

**Components** (`src/components/`): `ContactCard`, `ConfirmDialog`, `ErrorMessage`, `LoadingSpinner`, `Layout` — all presentational, no shared state.

**State:** All state is local `useState` per page. No global store.

**TypeScript config** is strict with `noUnusedLocals` and `noUnusedParameters` — unused symbols are compile errors.
