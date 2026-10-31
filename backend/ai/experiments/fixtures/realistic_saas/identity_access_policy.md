# Identity and Access Policy

Document owner: Identity Platform
Version: 3.2
Status: Approved
Effective date: 2026-08-15

## 1. Sign-in and account protection

### 1.1 Credential validation

The identity service accepts an email address and password over the approved authentication endpoint. A successful sign-in creates a new authenticated session and rotates any anonymous session identifier. The public response for an unknown account and an incorrect password is intentionally identical. The audit event records the internal result code, but the response must not reveal whether an email address belongs to an account.

### 1.2 Failed password attempts

Five consecutive password failures for the same account trigger a temporary account lock lasting fifteen minutes. A successful sign-in resets the consecutive-failure counter. A failure from one account must not lock another account, even when both accounts use the same source network. During the lock period, a correct password does not bypass the lock. Support staff may not shorten the lock through the standard user interface.

### 1.3 Multi-factor authentication

Administrators must provide a time-based authenticator code after entering a valid password. If the code is missing, expired, or used previously, sign-in is rejected and no authenticated session is created. A break-glass account follows the same second-factor requirement; emergency access is recorded separately and does not disable multi-factor authentication.

## 2. Session lifetime

### 2.1 Idle timeout

An interactive session expires after thirty minutes without an authenticated user action. Background polling, open browser tabs, and notification delivery do not count as user activity. A user action received after expiry must be rejected and redirected to sign-in; the service must not silently create a replacement session.

### 2.2 Absolute lifetime and renewal

Regardless of activity, an interactive session expires twelve hours after creation. A successful re-authentication creates a new session identifier. The idle timeout and absolute lifetime are separate controls; satisfying one does not extend the other.

## 3. Service identities

Service identities use short-lived credentials and are not subject to interactive idle timeout. They remain subject to credential rotation and audit requirements. A service identity cannot be used to sign in through the interactive browser flow.

## 4. Audit and monitoring

The service records sign-in success, rejection reason, account lock, MFA outcome, session creation, session expiry, and session revocation. Audit records contain an account identifier, event time, request correlation identifier, and outcome. Passwords, authenticator codes, and session secrets must never appear in logs.
