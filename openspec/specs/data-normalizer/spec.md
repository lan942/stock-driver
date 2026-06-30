# data-normalizer Specification

## Purpose
TBD - created by archiving change stock-crawler-base. Update Purpose after archive.
## Requirements
### Requirement: Normalize price units

The normalizer SHALL convert all price values to yuan (元).

#### Scenario: Price in yuan
- **WHEN** the input price is already in yuan (e.g., 1850.50)
- **THEN** the output SHALL be 1850.50

#### Scenario: Price in wan yuan
- **WHEN** the input price is marked as in wan yuan (e.g., 18.505)
- **THEN** the output SHALL be 18505.0 (multiplied by 1000)

### Requirement: Normalize volume units

The normalizer SHALL convert all volume values to shares (股).

#### Scenario: Volume in shares
- **WHEN** the input volume is already in shares (e.g., 1000000)
- **THEN** the output SHALL be 1000000

#### Scenario: Volume in手的 (hand)
- **WHEN** the input volume is in 手 (1手=100股)
- **THEN** the output SHALL be multiplied by 100

### Requirement: Normalize turnover rate

The normalizer SHALL convert turnover rate to percentage format (0-100).

#### Scenario: Turnover rate as percentage string
- **WHEN** the input is "5.25%" or 5.25
- **THEN** the output SHALL be 5.25

#### Scenario: Turnover rate as decimal
- **WHEN** the input is 0.0525 (representing 5.25%)
- **THEN** the output SHALL be 5.25 (multiplied by 100)

### Requirement: Normalize change percent

The normalizer SHALL convert change percent to standard percentage format.

#### Scenario: Change percent with sign
- **WHEN** the input is "+5.25" or "-3.20"
- **THEN** the output SHALL preserve the sign as 5.25 or -3.20

### Requirement: Validate required fields

The normalizer SHALL validate that all required fields are present and non-null.

#### Scenario: Missing required field
- **WHEN** a required field is missing or None
- **THEN** the normalizer SHALL set that field to None (not raise an error)

### Requirement: Handle unknown units gracefully

The normalizer SHALL log a warning and attempt to use the value as-is when the unit is unknown.

#### Scenario: Unknown unit encountered
- **WHEN** a field value has an unrecognized unit
- **THEN** the normalizer SHALL log a warning and return the value unchanged

