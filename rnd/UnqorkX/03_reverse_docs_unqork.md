# Unqork — Reverse-Engineered Product Documentation

## 1. Product Overview

### What It Is (As Documented)
Unqork is a **Regenerative Application Development Platform** that enables organizations to build enterprise applications without writing code. The platform features a "single, standardized platform, instead of hundreds of coding languages across a multitude of run-time engines" called the **Regenerative Engine**. ([Source](https://unqork.com/product-overview/))

The platform operates through **UDesigner**, an intuitive IDE that enables teams to "rapidly co-create, launch, and manage enterprise applications" with features including wayfinding, configurable module builders, and powerful search capabilities. ([Source](https://unqork.com/product-overview/))

### Who It Is For / Typical Use Cases
**Target Industries (explicitly documented):**
- **Financial Services**: Wealth management, asset management, banking, capital markets, digital assets ([Source](https://unqork.com/industry/financial-services/))
- **Insurance**: Property & casualty, life & annuities, group retirement, group benefits, reinsurance ([Source](https://unqork.com/industry/insurance/))
- **Government**: Citizen services, compliance, legacy modernization ([Source](https://unqork.com/industry/government/))
- **Healthcare**: Patient experience, process automation, case management ([Source](https://unqork.com/industry/healthcare/))

**Typical Use Cases:**
- Legacy application modernization ([Source](https://unqork.com/legacy-application-modernization/))
- Policy lifecycle digitization and claims management ([Source](https://unqork.com/industry/insurance/))
- KYC/AML and compliance workflows ([Source](https://unqork.com/industry/financial-services/))
- Case management and workflow automation ([Source](https://unqork.com/application-development/))
- AI-powered document processing and underwriting ([Source](https://unqork.com/enterprise-ai-solutions/))

### High-Level Value Propositions (Marketing)
*Note: The following are marketing claims from unqork.com:*
- "Accelerate time-to-market 3X" ([Source](https://unqork.com/industry/financial-services/))
- "3x faster from idea to production" through code abstraction with CI/CD ([Source](https://unqork.com/industry/government/))
- "65% Lower Lifecycle Costs" through no user-based licensing model ([Source](https://unqork.com/industry/government/))
- "10x Developer Productivity" ([Source](https://unqork.com/industry/government/))
- "100x Fewer Bugs" with instantaneous rollback capability ([Source](https://unqork.com/industry/government/))
- Reduce document processing onboarding times "up to 80%" ([Source](https://unqork.com/enterprise-ai-solutions/))

---

## 2. Core Concepts & Mental Model

The following key concepts are documented in the source materials:

- **Regenerative Engine**: The core runtime that provides "a single, standardized platform" replacing multiple coding languages and runtime engines ([Source](https://unqork.com/product-overview/))

- **UDesigner (IDE)**: The primary development interface with wayfinding, configurable module builders, and search capabilities ([Source](https://unqork.com/product-overview/))

- **Module**: A building block of applications; modules can be built once and reused across all Unqork applications ([Source](https://unqork.com/application-development/))

- **Module Builder**: Tool for constructing application modules ([Source](https://docs.unqork.io/docs/module-builder))

- **Workflow Builder**: Visual drag-and-drop tool for building complex workflows spanning orchestration, routing, rules, and dynamic flows ([Source](https://unqork.com/product-overview/))

- **Data Workflow**: System for data operations with specialized operators (Array, Object, Table, Gateway, IO, Value/String) ([Source](https://docs.unqork.io/docs/data-workflow))

- **Workspace**: A shared development environment where creators collaborate, manage roles, and organize project resources ([Source](https://unqork.com/application-development/))

- **Collections**: Data storage mechanism for submission data ([Source](https://docs.unqork.io/docs/collections))

- **Data Models**: Structures for establishing relationships between data entities ([Source](https://docs.unqork.io/docs/data-models))

- **Components**: UI building blocks ranging from inputs to charts, assembled via drag-and-drop ([Source](https://unqork.com/application-development/))

- **Application Accelerators**: Ready-to-use templates including dashboards, portals, and workflows with customizable pre-built components ([Source](https://unqork.com/product-overview/))

- **Integration Gateway**: Platform for connecting 700-800+ external systems via pre-built templates ([Source](https://unqork.com/product-overview/))

- **Creators**: Users who build applications on the platform ([Source](https://docs.unqork.io/docs/creator-management))

- **Express Users**: End users who interact with built applications ([Source](https://docs.unqork.io/docs/express-users))

- **RBAC (Role-Based Access Control)**: Access management across organization, role, group, environment, workspace, app, and component levels ([Source](https://unqork.com/product-overview/))

- **Promotions**: Mechanism for deploying applications across environments ([Source](https://docs.unqork.io/docs/promotions))

- **Branch & Merge**: Parallel development capability for editing, testing, deployment, and rollback ([Source](https://unqork.com/product-overview/))

---

## 3. Architecture Model (Conceptual)

### Documented Subsystems/Components

Based on source materials, Unqork's architecture includes:

**Development Layer:**
- **UDesigner IDE**: Primary interface for application development ([Source](https://unqork.com/product-overview/))
- **Module Builder**: For constructing application modules ([Source](https://docs.unqork.io/docs/module-builder))
- **Workflow Builder**: For orchestration, routing, rules, and dynamic flows ([Source](https://docs.unqork.io/docs/workflow-builder))
- **Data Workflow**: For data transformation operations ([Source](https://docs.unqork.io/docs/data-workflow))

**Runtime Layer:**
- **Regenerative Engine**: The core execution platform ([Source](https://unqork.com/product-overview/))

**Data Layer:**
- **Collections**: Data storage mechanism ([Source](https://docs.unqork.io/docs/collections))
- **Data Models/Schemas**: For structuring data relationships ([Source](https://docs.unqork.io/docs/data-models))
- **MongoDB Atlas**: Backend data storage (documented constraint) ([Source](https://unqork.com/security-compliance/))

**Integration Layer:**
- **Integration Gateway**: For external system connectivity ([Source](https://docs.unqork.io/docs/integration-gateway))
- **On-Prem Agents**: For on-premises system integration ([Source](https://docs.unqork.io/docs/on-prem-agents))
- **Webhooks**: Event-driven integration mechanism ([Source](https://docs.unqork.io/docs/webhooks))

**Security Layer:**
- **SSO (SAML/OIDC)**: Authentication ([Source](https://docs.unqork.io/docs/saml-configuration))
- **RBAC**: Authorization across all levels ([Source](https://docs.unqork.io/docs/rbac))
- **Encryption**: AES256 at rest, TLS 1.2 in transit ([Source](https://unqork.com/security-compliance/))

**Administration/Governance:**
- **Workspace Management**: Multi-application and user management ([Source](https://docs.unqork.io/docs/workspace-navigation))
- **Application Versioning**: Branch, merge, and promotions ([Source](https://docs.unqork.io/docs/application-versioning))

### Architecture Details NOT DOCUMENTED
- Internal service communication patterns
- Specific microservices architecture details
- Database sharding/replication topology
- CDN or edge deployment configurations
- Container orchestration details
- Internal event bus or messaging architecture

---

## 4. Feature Breakdown

### 4.1 Application Building

| Feature | Description | Source |
|---------|-------------|--------|
| Drag-and-Drop UI | Access diverse range of high-performance components from inputs to charts | [Source](https://unqork.com/application-development/) |
| Module Builder | Tool for constructing application modules with templates and transforms | [Source](https://docs.unqork.io/docs/module-builder) |
| Reusable Modules | Build once and reuse modules anywhere across all Unqork applications | [Source](https://unqork.com/application-development/) |
| Composite Apps (Embedded UI) | Configure and reuse standard components that can be securely embedded | [Source](https://unqork.com/application-development/) |
| Custom Components | Extend platform with custom-built components | [Source](https://docs.unqork.io/docs/custom-components) |
| BYO Framework | Bring Your Own framework for custom development | [Source](https://docs.unqork.io/docs/byo-framework) |
| Application Accelerators | Ready-to-use dashboards, portals, and workflows with customizable components | [Source](https://unqork.com/product-overview/) |

### 4.2 Data Management

| Feature | Description | Source |
|---------|-------------|--------|
| Data-Centric Development | Create API endpoints, store submission data, establish data model relationships | [Source](https://unqork.com/product-overview/) |
| Collections | Data storage for submissions | [Source](https://docs.unqork.io/docs/collections) |
| Data Models | Structure definitions for data entities | [Source](https://docs.unqork.io/docs/data-models) |
| Data Schemas | Schema definitions for data validation | [Source](https://docs.unqork.io/docs/data-schemas) |
| Data Model Governance | Ensure data quality and security in applications | [Source](https://unqork.com/application-lifecycle-management/) |
| CRUD Operations | Create, read, update, delete operations | [Source](https://docs.unqork.io/docs/crud-operations) |
| Bulk Operations | Import, export, update, delete at scale with job tracking | [Source](https://docs.unqork.io/docs/bulk-import) |
| WORM/System of Record | Immutable data storage preventing alterations | [Source](https://unqork.com/security-compliance/) |
| Data Lineage | Audit trails tracking data origin and movement | [Source](https://unqork.com/security-compliance/) |
| Data Versioning | Archive iterations with persistent storage | [Source](https://unqork.com/security-compliance/) |
| Granular Retention | Customizable data persistence policies | [Source](https://unqork.com/security-compliance/) |

### 4.3 Workflow & Logic

| Feature | Description | Source |
|---------|-------------|--------|
| Workflow Builder | Visual drag-and-drop tool for complex workflows | [Source](https://unqork.com/product-overview/) |
| Workflows and Logic | Library of events and operations for complex business logic | [Source](https://unqork.com/application-development/) |
| Data Workflow | Data transformation with Array, Object, Table, Gateway, IO, Value/String operators | [Source](https://docs.unqork.io/docs/data-workflow) |
| Workflow Templates | Pre-built workflow patterns | [Source](https://docs.unqork.io/docs/workflow-templates) |
| Case Management | Pre-built components for case handling workflows | [Source](https://unqork.com/application-development/) |
| Process Automation | Digitize legacy manual processes | [Source](https://unqork.com/legacy-application-modernization/) |
| Custom Operations | Create custom business operations | [Source](https://docs.unqork.io/docs/custom-operations) |
| Custom Events | Define custom event handlers | [Source](https://docs.unqork.io/docs/custom-events) |

### 4.4 UI Components

**Primary Fields:**
- Text Field, Email Field, Number Field, Date Field, Dropdown, Checkbox, Radio Button ([Source](https://docs.unqork.io/docs/text-field))

**Secondary Fields:**
- Address Field, Phone Field, Signature Field, Protected Fields ([Source](https://docs.unqork.io/docs/address-field))

**Display & Layout:**
- Grid Systems, Panels, Navigation, HTML Elements ([Source](https://docs.unqork.io/docs/grid-systems))

**Data Display:**
- Tables, Data Grids, ViewGrids, Matrices, Repeaters ([Source](https://docs.unqork.io/docs/tables))

**Charts & Visualizations:**
- KPI Component, Vega Components, Charts, Maps ([Source](https://docs.unqork.io/docs/kpi-component))

### 4.5 Governance & Administration

| Feature | Description | Source |
|---------|-------------|--------|
| RBAC | Role-based access control across all levels | [Source](https://unqork.com/product-overview/) |
| Creator Management | Manage platform builders | [Source](https://docs.unqork.io/docs/creator-management) |
| Express Users | Manage end users | [Source](https://docs.unqork.io/docs/express-users) |
| Workspace Management | Manage multiple applications and granular user access at scale | [Source](https://unqork.com/application-lifecycle-management/) |
| Team Workspaces | Collaborate, understand roles, manage centralized resources | [Source](https://unqork.com/application-development/) |
| Commenting & Notifications | Add comments and tag collaborators with automated notifications | [Source](https://unqork.com/application-development/) |

### 4.6 Testing & Monitoring

| Feature | Description | Source |
|---------|-------------|--------|
| Testing Tool | Built-in testing capabilities | [Source](https://docs.unqork.io/docs/testing-tool) |
| Application Performance Monitoring | Real-time trace and span telemetry across modules and workflows | [Source](https://unqork.com/product-overview/) |
| Dashboards | App, Module, and Workspace dashboards | [Source](https://docs.unqork.io/docs/app-dashboard) |
| Logs | Application logging | [Source](https://docs.unqork.io/docs/logs) |
| Metrics | Performance metrics | [Source](https://docs.unqork.io/docs/metrics) |
| Alerts | Alerting system | [Source](https://docs.unqork.io/docs/alerts) |
| Configuration Analysis | Configuration review tooling | [Source](https://docs.unqork.io/docs/configuration-analysis) |

### 4.7 AI Capabilities

| Feature | Description | Source |
|---------|-------------|--------|
| GenAI Connector | Simplify integration of GenAI into applications | [Source](https://unqork.com/enterprise-ai-solutions/) |
| AI Model Support | Integration with Google Gemini and OpenAI ChatGPT | [Source](https://unqork.com/enterprise-ai-solutions/) |
| Rapid AI Application Development | Create enterprise-ready AI-powered applications without code | [Source](https://unqork.com/enterprise-ai-solutions/) |
| AI Document Management | AI-powered document processing for streamlined onboarding | [Source](https://unqork.com/enterprise-ai-solutions/) |
| AI Underwriting Workbench | Streamline underwriting workflow (Marketplace) | [Source](https://unqork.com/marketplace-solution) |
| GenAI Conversion | Enables migration to any destination platform | [Source](https://unqork.com/industry/government/) |

---

## 5. Data, Integrations, and Extensibility

### Integration Capabilities

**Integration Gateway:**
- Connects 700-800+ external systems into applications ([Source](https://unqork.com/enterprise-application-integrations/))
- Pre-built integration templates for quick connectivity ([Source](https://unqork.com/enterprise-application-integrations/))
- Visual API creation for APIs, gateways, and microservices ([Source](https://unqork.com/enterprise-application-integrations/))
- Advanced mapping with drag-and-drop interface ([Source](https://unqork.com/enterprise-application-integrations/))
- On-prem agents for on-premises system connectivity ([Source](https://docs.unqork.io/docs/on-prem-agents))

### Documented Named Integrations

| Integration | Category | Source |
|-------------|----------|--------|
| SAML SSO | Authentication | [Source](https://docs.unqork.io/docs/saml-configuration) |
| OIDC SSO | Authentication | [Source](https://docs.unqork.io/docs/oidc-configuration) |
| Microsoft Entra | Identity Provider | [Source](https://docs.unqork.io/docs/microsoft-entra) |
| Okta | Identity Provider | [Source](https://docs.unqork.io/docs/okta-integration) |
| Auth0 | Identity Provider | [Source](https://docs.unqork.io/docs/auth0-integration) |
| DocuSign | Document Signatures | [Source](https://docs.unqork.io/docs/docusign-integration) |
| SendGrid | Email | [Source](https://docs.unqork.io/docs/sendgrid-integration) |
| Twilio | SMS/Voice | [Source](https://docs.unqork.io/docs/twilio-integration) |
| Salesforce | CRM | [Source](https://docs.unqork.io/docs/salesforce-integration) |
| Codat | Financial Data | [Source](https://docs.unqork.io/docs/codat-integration) |
| Google Gemini | AI Models | [Source](https://unqork.com/enterprise-ai-solutions/) |
| OpenAI ChatGPT | AI Models | [Source](https://unqork.com/enterprise-ai-solutions/) |
| Amazon Bedrock | AI/Legacy Migration | [Source](https://unqork.com/legacy-application-modernization/) |

### Partner Integrations (via Marketplace)

| Partner | Solution | Source |
|---------|----------|--------|
| Glia | Digital customer support (video, voice, chat, CoBrowsing) | [Source](https://unqork.com/partners-overview/) |
| Convr | AI-powered underwriting | [Source](https://unqork.com/partners-overview/) |
| Coherent | Digital platforms for insurance | [Source](https://unqork.com/partners-overview/) |
| Microsoft Azure | Cloud services | [Source](https://unqork.com/partners-overview/) |
| Google Cloud | Cloud migration/modernization | [Source](https://unqork.com/partners-overview/) |
| EY | Add Insurance Now, Global Resource Tracker | [Source](https://unqork.com/marketplace-solution) |
| Quantiphi + Google | AiUP/Dociphi document processing | [Source](https://unqork.com/marketplace-solution) |
| Slalom + AWS | Lightflow banking customer experience | [Source](https://unqork.com/marketplace-solution) |

### Extensibility Points

| Capability | Description | Source |
|------------|-------------|--------|
| Custom Components | Create platform-extending components | [Source](https://docs.unqork.io/docs/custom-components) |
| Custom Operations | Build custom business operations | [Source](https://docs.unqork.io/docs/custom-operations) |
| Custom Events | Define custom event handlers | [Source](https://docs.unqork.io/docs/custom-events) |
| BYO Framework | Bring your own development framework | [Source](https://docs.unqork.io/docs/byo-framework) |
| Embedded UI | Embed applications into external systems | [Source](https://docs.unqork.io/docs/embedded-ui) |
| Module Extensions | Extend module functionality | [Source](https://docs.unqork.io/docs/module-extensions) |
| API (Unqork API) | Platform API for programmatic access | [Source](https://docs.unqork.io/docs/unqork-api) |
| Webhooks | Event-driven external integrations | [Source](https://docs.unqork.io/docs/webhooks) |
| Open Source Specification | "Feature-rich, secure, and open ecosystem built on standardized web technologies" | [Source](https://unqork.com/technical-debt-reduction/) |

---

## 6. Security, Compliance, and Governance

### Certifications & Compliance

| Certification | Details | Source |
|---------------|---------|--------|
| SOC 2 Type II | Annual examinations per AICPA AT-C Section 205 | [Source](https://unqork.com/security-compliance/) |
| ISO 27001 | ISO/IEC 27001:2013 certified | [Source](https://unqork.com/security-compliance/) |
| FedRAMP | Live in FedRAMP Marketplace | [Source](https://unqork.com/security-compliance/) |
| HIPAA | Designed to manage ePHI | [Source](https://unqork.com/security-compliance/) |
| GDPR | Operates as Data Processor enabling compliance | [Source](https://unqork.com/security-compliance/) |

### Security Features

| Feature | Implementation | Source |
|---------|----------------|--------|
| Encryption at Rest | AES256 via MongoDB Atlas | [Source](https://unqork.com/security-compliance/) |
| Encryption in Transit | TLS 1.2 HTTPS | [Source](https://unqork.com/security-compliance/) |
| Single-Tenant Architecture | Each customer instance is isolated | [Source](https://unqork.com/security-compliance/) |
| RBAC | Access control across organization, role, group, environment, workspace, app, component | [Source](https://unqork.com/product-overview/) |
| SSO | SAML and OIDC configuration | [Source](https://docs.unqork.io/docs/saml-configuration) |
| GPG Encryption | Available for data encryption | [Source](https://docs.unqork.io/docs/gpg-encryption) |
| HMAC | Hash-based message authentication | [Source](https://docs.unqork.io/docs/hmac) |
| MTLS | Mutual TLS for secure connections | [Source](https://docs.unqork.io/docs/mtls) |
| Certificate Management | Certificate lifecycle management | [Source](https://docs.unqork.io/docs/certificates) |

### Security Operations

| Capability | Frequency/Details | Source |
|------------|-------------------|--------|
| Incident Response | SIEM-based monitoring with IDS/IPS and WAF | [Source](https://unqork.com/security-compliance/) |
| Penetration Testing | Annual, including independent network/application testing | [Source](https://unqork.com/security-compliance/) |
| Vulnerability Management | Daily static scans, weekly dynamic application security tests | [Source](https://unqork.com/security-compliance/) |
| Incident Response Testing | At least annually | [Source](https://unqork.com/security-compliance/) |

### FedRAMP Specific

| Requirement | Implementation | Source |
|-------------|----------------|--------|
| FIPS Cryptography | FIPS validated cryptography suites | [Source](https://unqork.com/security-compliance/) |
| PIV/CAC Authentication | Support for US Government customers | [Source](https://unqork.com/security-compliance/) |
| DNSSEC | Implemented | [Source](https://unqork.com/security-compliance/) |
| Zero-Trust Architecture | Implemented | [Source](https://unqork.com/security-compliance/) |

### Governance Capabilities

| Feature | Description | Source |
|---------|-------------|--------|
| Data Lineage | Audit trails tracking data origin and movement | [Source](https://unqork.com/security-compliance/) |
| WORM/System of Record | Immutable data storage | [Source](https://unqork.com/security-compliance/) |
| Data Versioning | Archive iterations with persistent storage | [Source](https://unqork.com/security-compliance/) |
| Granular Retention | Customizable data persistence policies | [Source](https://unqork.com/security-compliance/) |
| Workspace RBAC | Workspace-level access control | [Source](https://docs.unqork.io/docs/workspace-rbac) |

---

## 7. SDLC / Deployment / Environment Management

### Application Versioning

| Feature | Description | Source |
|---------|-------------|--------|
| Branching | Create development branches for parallel work | [Source](https://docs.unqork.io/docs/branching) |
| Merging | Combine branch changes | [Source](https://docs.unqork.io/docs/merging) |
| Branch & Merge | Simplified editing, testing, deployment, and rollback capabilities | [Source](https://unqork.com/product-overview/) |
| Dependencies | Manage application dependencies | [Source](https://docs.unqork.io/docs/dependencies) |
| Promotions | Deploy applications across environments | [Source](https://docs.unqork.io/docs/promotions) |

### Release Management

| Feature | Description | Source |
|---------|-------------|--------|
| Release Management | Ensure high quality applications and deploy at scale | [Source](https://unqork.com/application-lifecycle-management/) |
| SDLC Management | Manage applications efficiently across entire SDLC | [Source](https://unqork.com/application-lifecycle-management/) |
| Instantaneous Rollback | Rollback capability (mentioned in context of bug reduction) | [Source](https://unqork.com/industry/government/) |

### Environment Management

| Feature | Description | Source |
|---------|-------------|--------|
| Environment Separation | Multiple non-production environments in separate VPCs from production | [Source](https://unqork.com/security-compliance/) |
| Cross-Runtime Support | Support for cross-runtime deployments | [Source](https://docs.unqork.io/docs/cross-runtime-support) |

### Platform Updates

| Feature | Description | Source |
|---------|-------------|--------|
| UDLC Release Notes | Unqork Development Lifecycle release information | [Source](https://docs.unqork.io/docs/udlc-release-notes) |
| Release Calendar | Published release schedules (2025, 2026) | [Source](https://docs.unqork.io/docs/unqork-release-calendar-2025) |
| Release Versioning | Version series (720x through 730x documented) | [Source](https://docs.unqork.io/docs/unqork-730x-release-notes) |

---

## 8. Known Constraints / Limitations

The following constraints are explicitly documented:

### Security/Architecture Constraints

| Constraint | Description | Source |
|------------|-------------|--------|
| Customer Security Responsibility | Customers responsible for enabling security features and creating security controls where required | [Source](https://unqork.com/security-compliance/) |
| Data Storage | All data securely stored within MongoDB Atlas | [Source](https://unqork.com/security-compliance/) |
| Single-Tenant Only | All instances are single-tenant by default | [Source](https://unqork.com/security-compliance/) |
| US Data Processing | Data processed and controlled within the United States only | [Source](https://unqork.com/security-compliance/) |
| GDPR Data Processor Role | Unqork operates as Data Processor, not Data Controller | [Source](https://unqork.com/security-compliance/) |

### Compliance Requirements

| Constraint | Description | Source |
|------------|-------------|--------|
| FedRAMP FIPS Cryptography | FedRAMP deployment requires FIPS validated cryptography suites | [Source](https://unqork.com/security-compliance/) |
| FedRAMP PIV/CAC | FedRAMP requires PIV/CAC authentication for US Government customers | [Source](https://unqork.com/security-compliance/) |

### Operational Constraints

| Constraint | Description | Source |
|------------|-------------|--------|
| Service Availability | "Near-100% service availability levels" (not guaranteed 100%) | [Source](https://unqork.com/security-compliance/) |
| Customer-Defined Retention | Customers define data storage duration and purge schedules | [Source](https://unqork.com/security-compliance/) |
| Annual IR Testing | Incident response testing conducted at least annually | [Source](https://unqork.com/security-compliance/) |

### Business/Licensing Constraints

| Constraint | Description | Source |
|------------|-------------|--------|
| No User-Based Licensing | Platform uses no user-based licensing model | [Source](https://unqork.com/industry/government/) |
| Open Standards Requirement | Platform maintains open standards/open source (no proprietary code lock-in) | [Source](https://unqork.com/industry/government/) |

### Adoption Constraints

| Constraint | Description | Source |
|------------|-------------|--------|
| Organizational Change | Modernization requires organizational commitment to shift from maintenance-focused to innovation-focused operations | [Source](https://unqork.com/legacy-application-modernization/) |
| Industry Focus | Platform most effective for highly regulated industries (financial services, insurance, government, healthcare) | [Source](https://unqork.com/legacy-application-modernization/) |

---

## 9. "NOT DOCUMENTED" Appendix

The following areas are typically relevant for enterprise application platforms but are NOT evidenced in the sources:

### Technical Specifications
- **API Rate Limits**: Specific throttling values or quotas
- **Concurrent User Limits**: Capacity thresholds per application or instance
- **Application/Module Size Limits**: Maximum size constraints
- **Storage Capacity Limits**: Per customer or per application storage quotas
- **Latency SLAs**: Performance guarantees beyond "near-100% availability"

### Platform Details
- **Browser/OS Compatibility**: Source map references docs.unqork.io/docs/browser-support but detailed content not accessible
- **Specific Third-Party Integrations**: Full list of 700-800+ connectors not enumerated
- **On-Premises Deployment**: Only cloud deployment documented; no on-prem option evidenced
- **Offline Capabilities**: No documentation on offline functionality

### Commercial/Licensing
- **Pricing Tiers**: No pricing information documented
- **Feature Limitations by Tier**: No tiered feature restrictions documented
- **Support SLAs**: No specific support response time commitments

### Technical Architecture
- **Internal Service Architecture**: Microservices details not documented
- **Database Configuration Options**: Beyond MongoDB Atlas usage
- **CDN/Edge Deployment**: No edge computing documentation
- **Container/Orchestration Details**: No Kubernetes/container specifications
- **Internal Event Architecture**: Message bus/queue system details

### Component Specifications
- **Component-Level Technical Specs**: docs.unqork.io requires authentication; detailed component specifications not publicly accessible

### Development
- **Local Development Environment**: No local development tooling documented
- **CI/CD Pipeline Integration Details**: Beyond general "CI/CD" mention
- **Source Control Integration**: Beyond branch/merge within platform
- **Automated Testing Framework Details**: Beyond "Testing Tool" mention

### Internationalization
- **Multi-Language Support**: No i18n documentation
- **Regional Data Residency Options**: Only US data processing documented
- **Timezone Handling**: Not documented

---

*Document generated from extracted data in:*
- `recon/01_source_map_unqork.md`
- `recon/02_capabilities_unqork.md`

*All claims are sourced directly from documented evidence. Items marked "NOT DOCUMENTED" have no supporting evidence in the source materials.*
