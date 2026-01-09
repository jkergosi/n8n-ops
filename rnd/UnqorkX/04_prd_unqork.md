# PRD (Derived): Unqork

## 1. Problem Statement (as implied by documented positioning)

Unqork addresses the challenges enterprises face with traditional software development:

- **Technical Debt Accumulation**: Organizations struggle with "the cost and burden of legacy code management" that diverts resources from innovation to maintenance ([Source](https://unqork.com/technical-debt-reduction/))

- **Slow Time-to-Market**: Traditional development in regulated industries is slow and resource-intensive. The platform promises to "accelerate time-to-market 3X" ([Source](https://unqork.com/industry/financial-services/))

- **Legacy System Burden**: Enterprises need to "rapidly refactor legacy processes and applications without having to rip-and-replace your entire tech stack" ([Source](https://unqork.com/enterprise-ai-solutions/))

- **Developer Scarcity**: Organizations face limited development capacity; the platform aims to "expand development capacity by empowering non-technical business users with an intuitive, drag-and-drop visual designer" ([Source](https://unqork.com/technical-debt-reduction/))

- **Security and Compliance Risk**: Code-based development introduces vulnerabilities. Unqork positions itself as enabling applications that "grow more secure over time" with "100x fewer bugs" ([Source](https://unqork.com/guided-tour/), [Source](https://unqork.com/industry/government/))

- **Integration Complexity**: Enterprises must connect multiple systems, requiring "seamless integration of 800+ external systems" ([Source](https://unqork.com/product-overview/))

---

## 2. Target Users & Use Cases

### Target Users (explicitly documented)

**Primary Users:**
- **Creators**: Users who build applications on the platform ([Source](https://docs.unqork.io/docs/creator-management))
- **Non-technical Business Users**: Empowered via "intuitive, drag-and-drop visual designer" ([Source](https://unqork.com/technical-debt-reduction/))
- **IT Teams**: Working in "business/IT collaboration" to unlock innovation ([Source](https://unqork.com/industry/financial-services/))

**End Users:**
- **Express Users**: End users who interact with built applications ([Source](https://docs.unqork.io/docs/express-users))

### Target Industries (explicitly documented)
- **Financial Services**: Wealth management, asset management, banking, capital markets, digital assets ([Source](https://unqork.com/industry/financial-services/))
- **Insurance**: Property & casualty, life & annuities, group retirement, group benefits, reinsurance ([Source](https://unqork.com/industry/insurance/))
- **Government**: Citizen services, compliance, legacy modernization ([Source](https://unqork.com/industry/government/))
- **Healthcare**: Patient experience, process automation, case management ([Source](https://unqork.com/industry/healthcare/))

### Documented Use Cases

1. **Legacy Application Modernization**: "Rapidly refactor legacy processes and applications" including migration from mainframe, Java, and Access systems ([Source](https://unqork.com/legacy-application-modernization/))

2. **Policy Lifecycle Digitization**: "Rapidly launch new products. Streamline new business and underwriting processes" for insurance ([Source](https://unqork.com/industry/insurance/))

3. **KYC/AML and Compliance Workflows**: Build "integrated KYC/AML and NAV oversight processes" for regulatory compliance ([Source](https://unqork.com/industry/financial-services/))

4. **Case Management**: Pre-built components for case handling workflows with "drag-and-drop UI, and seamless upgrades" ([Source](https://unqork.com/application-development/))

5. **AI Document Processing**: AI-powered document management for "streamlined onboarding" reducing times "up to 80%" ([Source](https://unqork.com/enterprise-ai-solutions/))

6. **Claims and Fraud Automation**: Automates fraud identification, case routing, and data analysis ([Source](https://unqork.com/enterprise-ai-solutions/))

7. **Underwriting Acceleration**: "Streamline the entire underwriting workflow" with 5x time-to-value acceleration ([Source](https://unqork.com/marketplace-solution))

8. **Patient Experience Delivery**: "Deliver personalized, modern, and secure patient experiences" ([Source](https://unqork.com/industry/healthcare/))

9. **Constituent & Case Request Management**: "Automate legacy and paper processes rapidly; provide immediate visibility with automated business rules" ([Source](https://unqork.com/industry/government/))

---

## 3. Functional Requirements

### FR-01: No-Code Application Development
The platform shall enable users to build enterprise applications "without writing a single line of code" through a visual development environment. ([Source](https://unqork.com/industry/financial-services/))

### FR-02: Drag-and-Drop UI Construction
The system shall provide a drag-and-drop interface to "access a diverse range of high-performance components from inputs to charts" for building user interfaces. ([Source](https://unqork.com/application-development/))

### FR-03: Visual Workflow Builder
The platform shall provide a "visual drag-and-drop tool" for building complex workflows spanning "orchestration, routing, rules, and dynamic flows." ([Source](https://unqork.com/product-overview/))

### FR-04: Data Workflow Operations
The system shall support data transformation operations including Array, Object, Table, Gateway, IO, and Value/String operators. ([Source](https://docs.unqork.io/docs/data-workflow))

### FR-05: Reusable Module Development
The platform shall enable creators to "build once and reuse modules anywhere across all Unqork applications." ([Source](https://unqork.com/application-development/))

### FR-06: Data-Centric Development
The system shall enable users to "create and configure API endpoints, store submission data in collections, and establish relationships between data models." ([Source](https://unqork.com/product-overview/))

### FR-07: Application Accelerators
The platform shall provide "ready-to-use use cases (e.g. dashboards, portals, & workflows) with customizable pre-built components." ([Source](https://unqork.com/product-overview/))

### FR-08: Integration Gateway
The system shall provide connectivity to "800+ external systems" through pre-built integration templates. ([Source](https://unqork.com/product-overview/))

### FR-09: Visual API Creation
The platform shall enable users to "create APIs, gateways, and microservices visually and seamlessly reuse them across applications." ([Source](https://unqork.com/enterprise-application-integrations/))

### FR-10: On-Premises Integration
The system shall support on-premises system connectivity through dedicated agents. ([Source](https://docs.unqork.io/docs/on-prem-agents))

### FR-11: Role-Based Access Control
The platform shall provide RBAC that centrally manages access "across organization, role, group, environment, workspace, app, and component levels." ([Source](https://unqork.com/product-overview/))

### FR-12: SSO Authentication
The system shall support single sign-on via SAML and OIDC protocols. ([Source](https://docs.unqork.io/docs/saml-configuration), [Source](https://docs.unqork.io/docs/oidc-configuration))

### FR-13: Identity Provider Integration
The platform shall integrate with identity providers including Microsoft Entra, Okta, and Auth0. ([Source](https://docs.unqork.io/docs/microsoft-entra))

### FR-14: Team Collaboration Workspaces
The system shall provide shared workspaces where "creators can easily collaborate with their teammates, understand their roles, and manage centralized project resources and documentation." ([Source](https://unqork.com/application-development/))

### FR-15: Commenting and Notifications
The platform shall support adding "comments and tag collaborators at the workspace, app, or module levels" with "automated notifications." ([Source](https://unqork.com/application-development/))

### FR-16: Application Versioning (Branch & Merge)
The system shall enable parallel development with "simplified editing, testing, deployment, and rollback capabilities." ([Source](https://unqork.com/product-overview/))

### FR-17: Environment Promotion
The platform shall support deploying applications across environments through a promotions mechanism. ([Source](https://docs.unqork.io/docs/promotions))

### FR-18: Application Performance Monitoring
The system shall provide "real-time trace and span telemetry" for detecting and resolving issues across modules and workflows. ([Source](https://unqork.com/product-overview/))

### FR-19: Testing Tool
The platform shall include built-in testing capabilities. ([Source](https://docs.unqork.io/docs/testing-tool))

### FR-20: Dashboards and Logs
The system shall provide App, Module, and Workspace dashboards along with application logging. ([Source](https://docs.unqork.io/docs/app-dashboard), [Source](https://docs.unqork.io/docs/logs))

### FR-21: GenAI Connector
The platform shall "simplify the integration of GenAI into applications" through a dedicated connector. ([Source](https://unqork.com/enterprise-ai-solutions/))

### FR-22: AI Model Integration
The system shall support integration with AI models including Google Gemini and OpenAI ChatGPT. ([Source](https://unqork.com/enterprise-ai-solutions/))

### FR-23: Embedded UI / Composite Apps
The platform shall enable users to "create composite apps by configuring and reusing standard components that can be securely embedded." ([Source](https://unqork.com/application-development/))

### FR-24: Custom Components
The system shall allow extending the platform with custom-built components. ([Source](https://docs.unqork.io/docs/custom-components))

### FR-25: Custom Operations and Events
The platform shall support creating custom business operations and defining custom event handlers. ([Source](https://docs.unqork.io/docs/custom-operations), [Source](https://docs.unqork.io/docs/custom-events))

### FR-26: BYO Framework
The system shall support "Bring Your Own" framework for custom development scenarios. ([Source](https://docs.unqork.io/docs/byo-framework))

### FR-27: Webhook Support
The platform shall provide event-driven integration capabilities through webhooks. ([Source](https://docs.unqork.io/docs/webhooks))

### FR-28: Bulk Data Operations
The system shall support import, export, update, and delete operations at scale with job tracking. ([Source](https://docs.unqork.io/docs/bulk-import))

### FR-29: Case Management Components
The platform shall provide pre-built case management components with "drag-and-drop UI, and seamless upgrades for accelerated deployment." ([Source](https://unqork.com/application-development/))

### FR-30: Document Signature Integration
The system shall integrate with DocuSign for document signature workflows. ([Source](https://docs.unqork.io/docs/docusign-integration))

### FR-31: Communication Integrations
The platform shall integrate with SendGrid (email) and Twilio (SMS/voice) for communication capabilities. ([Source](https://docs.unqork.io/docs/sendgrid-integration), [Source](https://docs.unqork.io/docs/twilio-integration))

### FR-32: CRM Integration
The system shall integrate with Salesforce for CRM functionality. ([Source](https://docs.unqork.io/docs/salesforce-integration))

---

## 4. Non-Functional Requirements

### NFR-01: Security Certifications
The platform shall maintain FedRAMP, ISO 27001, and SOC 2 Type II certifications. ([Source](https://unqork.com/product-overview/))

### NFR-02: SOC 2 Type II Compliance
The system shall undergo "annual SOC 2 Type II examinations" conducted per AICPA standards AT-C Section 205. ([Source](https://unqork.com/security-compliance/))

### NFR-03: ISO 27001 Certification
The platform shall maintain ISO/IEC 27001:2013 certification. ([Source](https://unqork.com/security-compliance/))

### NFR-04: FedRAMP Authorization
The system shall be authorized in the FedRAMP Marketplace with FIPS validated cryptography, PIV/CAC authentication support, DNSSEC implementation, and zero-trust architecture. ([Source](https://unqork.com/security-compliance/))

### NFR-05: HIPAA Compliance
The platform shall be designed to manage electronic protected health information (ePHI) per HIPAA requirements. ([Source](https://unqork.com/security-compliance/))

### NFR-06: GDPR Compliance
The system shall enable organizations to comply with GDPR by operating as a Data Processor. ([Source](https://unqork.com/security-compliance/))

### NFR-07: Encryption at Rest
All data shall be encrypted at rest using AES256 encryption via MongoDB Atlas. ([Source](https://unqork.com/security-compliance/))

### NFR-08: Encryption in Transit
All communication shall use TLS 1.2 HTTPS encryption. ([Source](https://unqork.com/security-compliance/))

### NFR-09: Single-Tenant Architecture
Each customer instance shall be isolated - "only your products, rules, and customers live inside of your instance." ([Source](https://unqork.com/security-compliance/))

### NFR-10: Environment Separation
Customers shall receive "multiple non-production environments in separate VPCs from production." ([Source](https://unqork.com/security-compliance/))

### NFR-11: Service Availability
The platform shall provide "near-100% service availability levels." ([Source](https://unqork.com/security-compliance/))

### NFR-12: Incident Response
The system shall implement SIEM-based monitoring with IDS/IPS and web application firewalls. ([Source](https://unqork.com/security-compliance/))

### NFR-13: Penetration Testing
The platform shall undergo annual penetration assessments including independent network/application testing. ([Source](https://unqork.com/security-compliance/))

### NFR-14: Vulnerability Management
The system shall perform daily static scans and weekly dynamic application security tests. ([Source](https://unqork.com/security-compliance/))

### NFR-15: Government Compliance Standards
For government use cases, the platform shall provide "out-of-the-box compliance" with M23-22, UX Executive Order, and USWDS standards. ([Source](https://unqork.com/industry/government/))

---

## 5. Data & Integration Requirements

### Data Storage
- **Storage Backend**: All data stored within MongoDB Atlas ([Source](https://unqork.com/security-compliance/))
- **Collections**: Data storage mechanism for submission data ([Source](https://docs.unqork.io/docs/collections))
- **Data Models**: Structures for establishing relationships between data entities ([Source](https://docs.unqork.io/docs/data-models))
- **Data Schemas**: Schema definitions for data validation ([Source](https://docs.unqork.io/docs/data-schemas))

### Data Governance
- **WORM/System of Record**: Immutable data storage preventing alterations ([Source](https://unqork.com/security-compliance/))
- **Data Lineage**: Audit trails tracking data origin and movement ([Source](https://unqork.com/security-compliance/))
- **Data Versioning**: Archive iterations with persistent storage ([Source](https://unqork.com/security-compliance/))
- **Granular Retention**: Customizable data persistence policies ([Source](https://unqork.com/security-compliance/))

### Integration Methods
| Method | Description | Source |
|--------|-------------|--------|
| Integration Gateway | Connect 700-800+ external systems | [Source](https://unqork.com/product-overview/) |
| Pre-built Templates | Quick integration templates for enterprise systems | [Source](https://unqork.com/enterprise-application-integrations/) |
| Visual API Creation | Create APIs, gateways, microservices visually | [Source](https://unqork.com/enterprise-application-integrations/) |
| On-Prem Agents | Connect to on-premises systems | [Source](https://docs.unqork.io/docs/on-prem-agents) |
| Webhooks | Event-driven integrations | [Source](https://docs.unqork.io/docs/webhooks) |
| Platform API | Programmatic access via Unqork API | [Source](https://docs.unqork.io/docs/unqork-api) |

### Named Integrations
| Category | Integrations | Source |
|----------|--------------|--------|
| Identity Providers | Microsoft Entra, Okta, Auth0 | [Source](https://docs.unqork.io/docs/microsoft-entra) |
| Authentication | SAML SSO, OIDC SSO | [Source](https://docs.unqork.io/docs/saml-configuration) |
| Document | DocuSign | [Source](https://docs.unqork.io/docs/docusign-integration) |
| Communication | SendGrid (email), Twilio (SMS/voice) | [Source](https://docs.unqork.io/docs/sendgrid-integration) |
| CRM | Salesforce | [Source](https://docs.unqork.io/docs/salesforce-integration) |
| Financial | Codat | [Source](https://docs.unqork.io/docs/codat-integration) |
| AI Models | Google Gemini, OpenAI ChatGPT, Amazon Bedrock | [Source](https://unqork.com/enterprise-ai-solutions/) |

### Extensibility
| Capability | Description | Source |
|------------|-------------|--------|
| Custom Components | Create platform-extending components | [Source](https://docs.unqork.io/docs/custom-components) |
| Custom Operations | Build custom business operations | [Source](https://docs.unqork.io/docs/custom-operations) |
| Custom Events | Define custom event handlers | [Source](https://docs.unqork.io/docs/custom-events) |
| BYO Framework | Bring your own development framework | [Source](https://docs.unqork.io/docs/byo-framework) |
| Module Extensions | Extend module functionality | [Source](https://docs.unqork.io/docs/module-extensions) |
| Embedded UI | Embed applications into external systems | [Source](https://docs.unqork.io/docs/embedded-ui) |

---

## 6. Constraints & Limitations

### Architecture Constraints
| Constraint | Description | Source |
|------------|-------------|--------|
| Single-Tenant Only | All customer instances are isolated single-tenant | [Source](https://unqork.com/security-compliance/) |
| US Data Processing | Data processed and controlled within the United States only | [Source](https://unqork.com/security-compliance/) |
| MongoDB Backend | All data stored within MongoDB Atlas | [Source](https://unqork.com/security-compliance/) |

### Security/Compliance Constraints
| Constraint | Description | Source |
|------------|-------------|--------|
| Customer Security Responsibility | Customers responsible for enabling security features and creating controls where required | [Source](https://unqork.com/security-compliance/) |
| GDPR Data Processor Role | Unqork operates as Data Processor (not Data Controller) | [Source](https://unqork.com/security-compliance/) |
| FedRAMP FIPS Cryptography | FedRAMP deployment requires FIPS validated cryptography suites | [Source](https://unqork.com/security-compliance/) |
| FedRAMP PIV/CAC | FedRAMP requires PIV/CAC authentication for US Government customers | [Source](https://unqork.com/security-compliance/) |

### Operational Constraints
| Constraint | Description | Source |
|------------|-------------|--------|
| Service Availability | "Near-100% service availability levels" (not guaranteed 100%) | [Source](https://unqork.com/security-compliance/) |
| Customer-Defined Retention | Customers must define data storage duration and purge schedules | [Source](https://unqork.com/security-compliance/) |
| Annual IR Testing | Incident response testing conducted at least annually | [Source](https://unqork.com/security-compliance/) |

### Business Constraints
| Constraint | Description | Source |
|------------|-------------|--------|
| No User-Based Licensing | Platform uses non-user-based licensing model | [Source](https://unqork.com/industry/government/) |
| Open Standards | Platform maintains open standards/open source (no proprietary code lock-in) | [Source](https://unqork.com/industry/government/) |

### Adoption Constraints
| Constraint | Description | Source |
|------------|-------------|--------|
| Organizational Change Required | Modernization requires commitment to shift from maintenance-focused to innovation-focused operations | [Source](https://unqork.com/legacy-application-modernization/) |
| Industry Focus | Platform most effective for highly regulated industries (financial services, insurance, government, healthcare) | [Source](https://unqork.com/legacy-application-modernization/) |

---

## 7. Open Questions / Unknowns

The following areas are NOT DOCUMENTED in the available sources and represent unknowns for competitive analysis:

### Technical Specifications (Unknown)
- **API Rate Limits**: Specific throttling values or quotas not documented
- **Concurrent User Limits**: Capacity thresholds per application or instance not specified
- **Application/Module Size Limits**: Maximum size constraints not documented
- **Storage Capacity Limits**: Per customer or per application storage quotas unknown
- **Latency SLAs**: Performance guarantees beyond "near-100% availability" not specified

### Platform Details (Unknown)
- **Browser/OS Compatibility**: Detailed browser support requirements not publicly accessible
- **Full Integration List**: Complete enumeration of 700-800+ connectors not available
- **On-Premises Deployment**: Only cloud deployment documented; no on-prem option evidenced
- **Offline Capabilities**: No documentation on offline functionality
- **Local Development Environment**: No local development tooling documented

### Commercial/Licensing (Unknown)
- **Pricing Model**: No pricing information documented
- **Feature Tiers**: No tiered feature restrictions documented
- **Support SLAs**: No specific support response time commitments documented

### Technical Architecture (Unknown)
- **Internal Service Architecture**: Microservices details not documented
- **CDN/Edge Deployment**: No edge computing documentation
- **Container/Orchestration Details**: No Kubernetes/container specifications
- **Internal Event Architecture**: Message bus/queue system details not available

### Internationalization (Unknown)
- **Multi-Language Support**: No i18n documentation
- **Regional Data Residency Options**: Only US data processing documented
- **Timezone Handling**: Not documented

### Development (Unknown)
- **CI/CD Pipeline Integration Details**: Beyond general "CI/CD" mention
- **Source Control Integration**: Beyond branch/merge within platform
- **Automated Testing Framework Details**: Beyond "Testing Tool" mention

---

*This PRD is derived from documented sources. All requirements trace to evidence in:*
- `recon/03_reverse_docs_unqork.md`
- `recon/02_capabilities_unqork.md`
- `recon/01_source_map_unqork.md`

*Items in Section 7 (Open Questions) represent gaps in publicly available documentation and should not be assumed or inferred.*
