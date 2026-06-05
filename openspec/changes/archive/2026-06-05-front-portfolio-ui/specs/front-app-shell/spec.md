## ADDED Requirements

### Requirement: Authenticated app layout with sidebar

After onboarding, app pages MUST use a persistent layout with a left sidebar and main content area.

#### Scenario: Sidebar navigation items

- **WHEN** the user views any post-onboarding page
- **THEN** a sidebar displays at least two items: Dashboard and Chat
- **AND** Dashboard links to `/dashboard`
- **AND** Chat is visually disabled with a "Coming soon" indicator (not navigable to a functional chat)

#### Scenario: Active route highlight

- **WHEN** the user is on `/dashboard`
- **THEN** the Dashboard nav item is highlighted using accent color `#68B3AE`

### Requirement: Visual design system

The UI MUST follow a minimal, Stripe-inspired aesthetic with the NAM palette.

#### Scenario: Color palette

- **WHEN** rendering app chrome and primary actions
- **THEN** background is white (`#FFFFFF`)
- **AND** primary accent is `#68B3AE` (buttons, active nav, links)
- **AND** text uses high-contrast dark gray on white

#### Scenario: Layout spacing

- **WHEN** displaying dashboard content
- **THEN** content uses generous padding, subtle borders between sections, and card-style grouping
- **AND** avoids heavy shadows or cluttered dense tables

### Requirement: Route structure

The front MUST expose these routes in v1:

| Route | Purpose |
|-------|---------|
| `/onboarding` | First-run wizard |
| `/dashboard` | Portfolio home |
| `/` | Redirect to `/dashboard` or `/onboarding` based on profile |

#### Scenario: Root redirect

- **WHEN** the user visits `/`
- **THEN** they are redirected based on profile existence (same logic as onboarding guard)
