---
name: claude-ecom
description: "D2C ecommerce business review toolkit. Analyzes order transaction data (CSV) across time periods (30d/90d/365d), produces KPI trees with health signals, structured findings, and concrete action plans. Triggers: 'ecommerce review', 'store review', 'store health', 'revenue analysis', 'customer analysis', 'product analysis', 'business review'. Requires CSV with: Order ID, Order date, Customer ID, Revenue, Quantity, SKU/Product ID."
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - Write
sync: no
---

# claude-ecom — Ecommerce Business Review Toolkit

D2C ecommerce analytics system. Analyzes order transaction CSV data and produces structured business reviews with KPI trees, health signals, and action plans.

**Source:** https://github.com/takechanman1228/claude-ecom (MIT License)

## Quick Reference

| Command | What it does | Output |
|---------|-------------|--------|
| `/claude-ecom review` | Full business review (auto-selects periods from data) | REVIEW.md |
| `/claude-ecom review 30d` | Focused on last 30 days | REVIEW_30D.md |
| `/claude-ecom review 90d` | Focused on last 90 days | REVIEW_90D.md |
| `/claude-ecom review 365d` | Focused on last 365 days | REVIEW_365D.md |
| `/claude-ecom review [question]` | Answers a specific question from data | Inline response |

## Data Input

**Required CSV columns:**
- Order ID, Order date, Customer ID (or email)
- Revenue (after discounts, before tax/shipping)
- Quantity, SKU/Product ID
- Discount amount (if available)

## Response Modes

### Mode 1: Full Review (default)
Triggered when: no natural-language question in user's input.
Output: REVIEW.md with full 6-part structure.

### Mode 2: Focused Query
Triggered when: user includes a natural-language question.
Output: inline conversational response.

Examples:
- "how was last month?" → monthly trend analysis
- "how's retention looking?" → customer metrics focus
- "how was Q4?" → quarterly breakdown

## Analysis Framework

### KPI Tree (per period)

```
Revenue $X (vs prior period: +X%)
|-- 🟢 New Customer Revenue $X (X% of total)
|   |-- New Customers: X (+X%)
|   |-- New Customer AOV: $X (+X%)
|-- 🟡 Existing Customer Revenue $X (X% of total)
    |-- Returning Customers: X (+X%)
    |-- Returning AOV: $X (+X%)
    |-- Repeat Purchase Rate: X% (365d only)
```

🟢 healthy / 🟡 watch / 🔴 problem

### Health Check Categories
- **Revenue:** MoM growth, AOV trend, discount rate
- **Customer:** New vs returning mix, churn signals, concentration
- **Product:** Multi-item order rate, SKU performance, seasonal patterns

### Report Structure (REVIEW.md)
1. **Executive Summary** — narrative blockquote + scoreboard table
2. **30d Pulse** — KPI tree + max 1 finding
3. **90d Momentum** — KPI tree + drivers + max 2 findings
4. **365d Structure** — KPI tree + drivers + max 3 findings
5. **Action Plan** — max 5 items by time horizon + guardrails
6. **Data Notes** — revenue definition, period, order count

### Action Plan Format
```
Immediate (from 30d signals): [action + why + when + success metric]
This Month (from 90d findings): [action + why + when + success metric]
This Quarter (from 365d insights): [action + why + when + success metric]

Guardrails: [2-3 metrics that must not deteriorate]
```

## Finding Quality Standard

Each finding: **What is → Why it matters → What to do**

- **What is:** 1 sentence, quantitative fact
- **Why it matters:** Data-backed tension with contrast ("however", "despite")
- **What to do:** Direction only, 1 sentence (no vague verbs: "consider", "explore")

## Period Interaction Rules

- Confirm or contradict across periods — don't let them exist in isolation
- If 90d shows a break, check 30d for continuation
- Never repeat a finding across periods — state once at structural level
- Executive Summary synthesizes, not summarizes sequentially
