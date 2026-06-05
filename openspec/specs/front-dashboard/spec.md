## ADDED Requirements

### Requirement: Dashboard displays portfolio positions

The dashboard MUST list the user's current positions from `GET /positions`, enriched with index metadata from `GET /indices`.

#### Scenario: Empty portfolio

- **WHEN** the user has no positions
- **THEN** the dashboard shows an empty state with a call-to-action to add a first holding

#### Scenario: Positions with index names

- **WHEN** positions exist
- **THEN** each row displays index name (joined from indices), ISIN, quantity, average cost (PRU), and cost basis (`quantity × average_cost`)

#### Scenario: Gains and losses placeholder

- **WHEN** displaying performance columns
- **THEN** unrealized gain/loss MAY show `—` until nam-api provides `current_price`
- **AND** a summary card MAY show total cost basis across all positions

### Requirement: User can add an index

The dashboard MUST provide a flow to register a new index via `POST /indices`.

#### Scenario: Create index successfully

- **WHEN** the user submits name and ISIN in the add-index form
- **THEN** `POST /indices` is called
- **AND** the new index appears in index pickers
- **AND** duplicate ISIN (409) shows an inline error

### Requirement: User can open a position via BUY transaction

Opening a position MUST use `POST /transactions` with `type: BUY` (positions are server-calculated, not created directly).

#### Scenario: Buy transaction creates position

- **WHEN** the user selects an index and submits price, quantity, date, and optional fees
- **THEN** `POST /transactions` is called with `type: BUY`
- **AND** the positions list refreshes showing updated quantity and average cost

#### Scenario: Transaction validation error

- **WHEN** the API returns 422 (e.g. insufficient sell — not applicable on first BUY)
- **THEN** the error message is displayed to the user

### Requirement: Dashboard summary header

The dashboard MUST show a welcome header with the user's first name from `GET /profile`.

#### Scenario: Personalized greeting

- **WHEN** the dashboard loads
- **THEN** the user's `firstname` from profile is displayed in the page header
