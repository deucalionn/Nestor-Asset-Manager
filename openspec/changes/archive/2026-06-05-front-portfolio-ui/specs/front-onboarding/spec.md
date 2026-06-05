## ADDED Requirements

### Requirement: Unsetup user sees onboarding only

The front MUST redirect users without a profile to the onboarding flow. A profile exists when `GET /profile` returns 200.

#### Scenario: First visit with empty database

- **WHEN** the user opens the app and `GET /profile` returns 404
- **THEN** the user is routed to `/onboarding`
- **AND** dashboard routes are not accessible

#### Scenario: Returning user with profile

- **WHEN** `GET /profile` returns 200
- **THEN** the user is routed to `/dashboard` (or intended app route)
- **AND** onboarding is not shown

### Requirement: Three-step onboarding wizard

Onboarding MUST be a 3-step wizard with forward and backward navigation before final submission.

| Step | Content |
|------|---------|
| 1 | First name, date of birth (18+ validation mirrored from API) |
| 2 | Investment strategy (CONSERVATIVE, BALANCED, GROWTH, AGGRESSIVE) |
| 3 | Goals (free text) and review of all entered fields |

#### Scenario: Navigate forward with validation

- **WHEN** the user completes step 1 with valid fields and clicks Next
- **THEN** step 2 is displayed
- **AND** step 1 values are preserved

#### Scenario: Navigate backward

- **WHEN** the user is on step 2 or 3 and clicks Back
- **THEN** the previous step is shown with previously entered values intact

#### Scenario: Final submission

- **WHEN** the user confirms on step 3
- **THEN** the front calls `POST /setup` with the combined `UserCreate` payload
- **AND** on 201 redirects to `/dashboard`
- **AND** displays API validation errors inline on failure (e.g. age under 18)

#### Scenario: Setup already exists

- **WHEN** `POST /setup` returns 409 (profile already created)
- **THEN** the user is redirected to `/dashboard`
