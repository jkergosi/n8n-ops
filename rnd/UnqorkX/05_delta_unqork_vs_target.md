# Delta Matrix — Unqork vs Target

## Status: BLOCKED — Awaiting Required Input

**Date:** 2026-01-08

---

## Required Input Missing

Per the specification in `feature_05_delta.md`, this step requires:

| Required File | Status |
|---------------|--------|
| `recon/04_prd_unqork.md` | Available |
| `recon/target_product_feature_list.md` | **MISSING** |

---

## Action Required

Please provide `recon/target_product_feature_list.md` containing the target product's feature list.

### Expected Format

The target product feature list should include a structured enumeration of capabilities/features, ideally in a format such as:

```markdown
# Target Product Feature List

## Feature Category 1
| Feature | Status | Description |
|---------|--------|-------------|
| Feature Name | Yes / Planned / No | Brief description |

## Feature Category 2
...
```

Or alternatively:

```markdown
# Target Product Feature List

- [ ] Feature 1 (Planned)
- [x] Feature 2 (Yes)
- Feature 3: Description (Status)
```

### Recommended Categories

Based on the Unqork PRD structure, consider including:

1. **Development Capabilities**
   - No-code/low-code development
   - Visual UI builder
   - Workflow builder
   - Reusable modules/components

2. **Data & Integration**
   - API creation
   - External integrations
   - Data storage/models
   - Webhooks

3. **Security & Compliance**
   - Authentication (SSO, SAML, OIDC)
   - RBAC
   - Certifications (SOC 2, ISO 27001, FedRAMP, HIPAA)
   - Encryption

4. **Collaboration & DevOps**
   - Team workspaces
   - Version control (branch/merge)
   - Environment promotion
   - Testing tools

5. **AI/Extensibility**
   - AI model integration
   - Custom components
   - Embedded UI

6. **Industry-Specific**
   - Financial services features
   - Insurance features
   - Government compliance
   - Healthcare features

---

## Next Steps

Once `recon/target_product_feature_list.md` is provided:

1. This file will be updated with the complete comparison matrix
2. Each capability from the Unqork PRD will be mapped against target product features
3. Classifications (Parity / Unqork Advantage / Target Advantage / Unique) will be assigned
4. Strategic gap analysis summary will be generated

---

## Prepared Comparison Structure

The final delta matrix will follow this format:

### 1. Comparison Table

| Capability / Requirement | Unqork (Evidence) | Target Product | Notes | Classification |
|--------------------------|-------------------|----------------|-------|----------------|
| *Populated after input received* | | | | |

### 2. Summary

- Strategic gaps and overlaps will be documented here (3-10 bullets)

---

*This document will be completed when the required `target_product_feature_list.md` input is provided.*
