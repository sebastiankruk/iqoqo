## Purpose

Define what the sign-in endpoint may reveal about whether an account exists, so that
the guarantee is stated as a requirement rather than living only in a docstring.

The requirement below is written to hold under **every** option still under review in
`design.md` D1. It constrains the observable channel, not the chosen remedy.

## ADDED Requirements

### Requirement: Sign-in Response Does Not Disclose Account Existence

The system SHALL NOT reveal, through the HTTP status code of a sign-in attempt, whether
an account exists for the submitted email address. Specifically, a response to an
attempt with a correct password against a disabled account SHALL carry the same status
code as a response to an attempt against an address with no account at all.

The check that determines whether an account is enabled SHALL be performed **after**
the password has been verified, so that the timing of the response does not disclose
account existence either.

#### Scenario: Unknown address and disabled account are indistinguishable by status

- **WHEN** a sign-in attempt is made twice with the same correct password, once against an address with no account and once against an account whose password is correct but which is disabled
- **THEN** both responses carry the same HTTP status code

#### Scenario: A wrong password is not distinguished from a disabled account

- **WHEN** a sign-in attempt is made with a wrong password against an address that has an account
- **THEN** the response carries the same HTTP status code as the two cases above

#### Scenario: Account-enablement is checked after the password, not before

- **WHEN** the timing of a sign-in attempt against an address with no account is compared against the timing of an attempt against an account with a wrong password
- **THEN** the two are not distinguishable within the tolerance asserted by the authentication timing test, because a password verification is performed on both paths

#### Scenario: A disabled account still cannot obtain a token

- **WHEN** a sign-in attempt is made with the correct password against a disabled account
- **THEN** no token is issued and no authenticated session is established
