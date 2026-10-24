# auth-pat-and-totp Specification

## Purpose
Personal Access Tokens (PATs) with scoped bearer authorization and TOTP 2FA enrollment with recovery codes.

## Requirements

### Requirement: Personal Access Token Authentication

The system SHALL authenticate API requests using hashed Personal Access Tokens bearing the 'iqo_' prefix.

#### Scenario: Valid PAT grants scoped access

- **WHEN** A request arrives with Authorization: Bearer iqo_... possessing read:catalog scope
- **THEN** The request succeeds and last_used_at is updated.

### Requirement: TOTP Two-Factor Challenge

The system SHALL require a valid 6-digit TOTP code or recovery code during login for enrolled accounts.

#### Scenario: Login challenge requires OTP

- **WHEN** A user with 2FA enabled provides valid username/password
- **THEN** Returns 200 with mfa_required=True prompting for TOTP code.
