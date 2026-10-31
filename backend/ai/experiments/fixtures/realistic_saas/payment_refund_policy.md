# Payment Settlement and Refund Policy

Document owner: Billing Operations
Version: 2.4
Status: Approved
Effective date: 2026-09-01

## 1. Settlement records

An order is not considered paid when the customer submits checkout. It becomes settled only after the payment provider confirms capture and the billing ledger records the settlement timestamp. Refund eligibility is measured from that settlement timestamp, not from order creation, authorization, invoice issue, or the date a support ticket is opened.

## 2. Customer refund window

### 2.1 Standard request

A customer may request a refund within seven calendar days after settlement. The final eligible instant is 23:59 UTC on the seventh calendar day. A request submitted after that instant is outside the standard refund window even if the invoice was issued later.

| Event | Starts the standard refund clock | Eligible duration |
|---|---|---|
| Provider confirms capture and ledger records settlement | Yes | Seven calendar days |
| Customer submits checkout | No | None |
| Invoice is issued | No | None |
| Support ticket is opened | No | None |

### 2.2 Partial refunds

Billing staff may issue one partial refund for an eligible order when the customer retained part of the service. The total of all successful refunds must not exceed the amount captured. A pending refund does not release the reserved amount until the provider confirms the refund.

### 2.3 Provider disputes

A cardholder dispute opened with the payment provider follows the provider's chargeback process and deadline. It is not a standard customer refund request and must not be treated as evidence that the seven-day refund window has been extended.

## 3. Cancellations and exceptions

Canceling a future subscription stops the next renewal but does not itself refund a settled invoice. A billing manager may approve an exception for duplicate capture or a documented service outage. The exception reason, approver, affected settlement, and amount must be recorded before the refund is sent.

## 4. Reconciliation

The ledger stores order ID, provider transaction ID, captured amount, currency, settlement timestamp, refund amount, refund status, and the associated approval record. Reconciliation compares provider settlement and refund events with the ledger once per day. A mismatch is queued for review and is not automatically converted into a new payment or refund.

| Ledger field | Purpose | Required for reconciliation |
|---|---|---|
| Provider transaction ID | Match the provider event | Yes |
| Settlement timestamp | Establish the refund-window start | Yes |
| Captured amount and currency | Bound the refundable amount | Yes |
| Approval record | Explain an exception refund | When an exception applies |
