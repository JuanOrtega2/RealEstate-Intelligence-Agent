# CLAUDE.md - Karpathy Guidelines

## 1. Think Before Coding
- State assumptions explicitly. If uncertain, ASK rather than guess.
- Present multiple interpretations if ambiguity exists.
- Push back if a simpler approach exists.
- Stop when confused. Name what's unclear.

## 2. Simplicity First
- Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- If 200 lines could be 50, rewrite it.
- The test: Would a senior engineer say this is overcomplicated?

## 3. Surgical Changes
- Touch only what you must.
- Match existing style, even if you'd do it differently.
- Remove imports/variables/functions that YOUR changes made unused.
- Don't refactor things that aren't broken.

## 4. Goal-Driven Execution
- Define success criteria clearly.
- For multi-step tasks, state a brief plan:
  1. [Step] → verify: [check]
  2. [Step] → verify: [check]
- Loop until verified.

---
## Project Specifics
- **LLM Provider:** NVIDIA NIM (Build NVIDIA) - OpenAI Compatible API.
- **Backend:** FastAPI (following dev_ia_api_rest patterns).
- **Style:** Clean, documented, test-driven.

---
## ✅ Important Requirements History

| Date | Requirement | Status | Notes |
| :--- | :--- | :--- | :--- |
| 2026-05-05 | **Senior Financial Engine** | ✅ Closed | Cap Rate, Net Yield, and Cash on Cash implemented. |
| 2026-05-05 | **Spanish Taxation** | ✅ Closed | IRPF with 60% reduction and ITP by CCAA. |
| 2026-05-05 | **Interest Rate Shielding** | ✅ Closed | 3% floor to prevent 0% interest hallucinations. |
| 2026-05-05 | **Technical Discretion** | ✅ Active | Prohibition of mentioning internal functions (`analyze_investment_roi`). |
| 2026-05-05 | **Language Lock** | ✅ Active | English response block. |
| 2026-05-05 | **Latency Optimization** | ✅ Closed | Security AI disabled by default to eliminate double latency. |
| 2026-05-05 | **Estimation Consent**| ✅ Closed | New UX Flow: Ask if automatic estimation should be used to reduce friction. |
