# AI Prompt Guide for Polly Project

This document serves as a **living guide** for AI-assisted development in the Polly project. It outlines the **scope, lessons learned, best practices, and future roadmap** to ensure efficient and consistent collaboration.

---

## **1. Project Overview**
### **1.1. Project Goals**
Polly is a **decentralized/federated identity provider and polling platform** with the following goals:
- **Decentralized Identity (DID)**: Support for DIDs, DID methods, and DID documents.
- **Verifiable Credentials (VCs)**: Store, verify, and revoke VCs for authentication and authorization.
- **Federated Identity**: Link multiple external identities (e.g., OAuth2, OpenID Connect, SAML) to a single user.
- **Federated Database**: Synchronize data across multiple nodes with conflict resolution.
- **Polling System**: Enable decentralized polling with support for geographical scopes.

### **1.2. Architecture**
Polly follows a **modular architecture** with the following components:
- **Backend**: Django (Python) for API and business logic.
- **Frontend**: Django Templates + HTMX for dynamic interactions.
- **Database**: SQLite (development) / PostgreSQL (production).
- **Identity**: DIDKit for DID/VC operations, custom authentication backends.
- **Federation**: Custom models and signals for data synchronization.

### **1.3. Key Features**
| Feature                     | Description                                                                                     |
|-----------------------------|-------------------------------------------------------------------------------------------------|
| **DID-Based Authentication** | Users can log in using their DID and Verifiable Credentials (VCs).                            |
| **VC Management**           | Users can view, issue, and verify VCs.                                                          |
| **Federated Identity**      | Support for OAuth2, OpenID Connect, and SAML providers.                                         |
| **Federated Database**      | Synchronize data across nodes with versioning and conflict resolution.                         |
| **Polling System**          | Create, vote on, and view polls with geographical scopes.                                       |
| **Theming**                 | Support for light/dark mode and custom themes.                                                 |

---

## **2. Lessons Learned**
### **2.1. Today’s Insights**
1. **DID/VC Integration**:
   - DIDKit is a powerful tool for DID/VC operations but requires careful handling of keys and proofs.
   - Always validate DIDs and VCs before using them in authentication flows.
   - Store private keys securely (e.g., encrypted in the database).

2. **Database Migrations**:
   - Always create and apply migrations when adding or modifying model fields.
   - Test migrations in a staging environment before deploying to production.

3. **Template Organization**:
   - Use a **consistent template hierarchy** (e.g., `partials/`, `registration/`) for reusability.
   - Document template usage in `templates/README.md`.

4. **Authentication Flows**:
   - Ensure all authentication backends (e.g., DID, username/password) are thoroughly tested.
   - Provide clear error messages for failed authentication attempts.

5. **Frontend Debugging**:
   - Use **HTMX dev tools** and **browser console** to debug dynamic interactions.
   - Add `console.log` statements to verify data flow.

### **2.2. Common Pitfalls**
| Pitfall                          | Solution                                                                                       |
|----------------------------------|------------------------------------------------------------------------------------------------|
| **Missing Migrations**           | Always run `makemigrations` and `migrate` after model changes.                                |
| **Template Syntax Errors**       | Use Django’s template debugger and validate syntax before deployment.                        |
| **Authentication Failures**      | Test all authentication backends (DID, username/password) and provide clear error messages.  |
| **DID/VC Verification Failures** | Validate DIDs and VCs before using them in authentication flows.                             |
| **HTMX Request Failures**        | Ensure CSRF tokens are included in HTMX requests and verify network requests in dev tools.   |

---

## **3. Best Practices**
### **3.1. Coding Standards**
1. **Python**:
   - Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code.
   - Use type hints (`typing` module) for better code clarity.
   - Document functions and classes with docstrings.

2. **Django**:
   - Use Django’s built-in features (e.g., `auth`, `messages`, `staticfiles`) where possible.
   - Keep business logic in **views** and **services**, not in templates or models.
   - Use `django-debug-toolbar` for debugging SQL queries and performance.

3. **Frontend**:
   - Use **Tailwind CSS** for styling and **HTMX** for dynamic interactions.
   - Follow **accessibility best practices** (e.g., ARIA labels, semantic HTML).
   - Use **CSS variables** for theming (e.g., `--primary-color`).

4. **DID/VC**:
   - Use **DIDKit** for DID/VC operations (e.g., `generate_did`, `issue_vc`, `verify_vc`).
   - Store private keys securely (e.g., encrypted in the database).
   - Validate DIDs and VCs before using them in authentication flows.

### **3.2. Tools and Workflows**
| Tool               | Purpose                                                                                     |
|--------------------|---------------------------------------------------------------------------------------------|
| **DIDKit**         | DID/VC operations (generation, resolution, signing, verification).                         |
| **HTMX**           | Dynamic frontend interactions without full page reloads.                                   |
| **Tailwind CSS**   | Styling and theming.                                                                        |
| **Django Debug Toolbar** | Debug SQL queries, templates, and performance.                                      |
| **Playwright**     | End-to-end testing for frontend interactions.                                              |
| **Git**            | Version control and collaboration.                                                          |
| **GitHub Actions** | CI/CD for automated testing and deployment.                                                |

### **3.3. Testing Strategy**
1. **Unit Tests**:
   - Test models, forms, and utility functions in isolation.
   - Use Django’s `TestCase` for database-related tests.

2. **Integration Tests**:
   - Test interactions between components (e.g., views and templates).
   - Use `django.test.Client` for HTTP request/response testing.

3. **End-to-End Tests**:
   - Use **Playwright** to test frontend interactions (e.g., voting, authentication).
   - Test all authentication flows (DID, username/password).

4. **Accessibility Tests**:
   - Use tools like [axe](https://www.deque.com/axe/) to validate accessibility.
   - Ensure keyboard navigability and ARIA compliance.

---

## **4. Future Roadmap**
### **4.1. Phase 5: Federated Identity Integration**
1. **DID-Based Authentication**:
   - Test and refine DID/VC login flows.
   - Add support for multiple DID methods (e.g., `did:web`).

2. **Federated Identity Providers**:
   - Integrate OAuth2, OpenID Connect, and SAML providers.
   - Allow users to link external identities to their account.

3. **VC Management UI**:
   - Add a UI for users to view, issue, and verify VCs.
   - Support for revoking VCs.

### **4.2. Phase 6: Federated Database Enhancements**
1. **Real-Time Synchronization**:
   - Use WebSockets or Server-Sent Events (SSE) for real-time updates.
   - Improve conflict resolution for federated data.

2. **Offline Support**:
   - Add support for offline-first functionality with local data storage.
   - Sync data when the user comes back online.

### **4.3. Phase 7: UI/UX Improvements**
1. **Responsive Design**:
   - Ensure the frontend works well on mobile devices.
   - Test across different screen sizes and browsers.

2. **Theming**:
   - Add support for custom themes (e.g., dark mode, high contrast).
   - Allow users to switch themes dynamically.

3. **Accessibility**:
   - Improve ARIA labels, keyboard navigation, and screen reader support.
   - Conduct accessibility audits using tools like axe.

### **4.4. Phase 8: Deployment and Scaling**
1. **Docker**:
   - Create a `Dockerfile` and `docker-compose.yml` for containerized deployment.
   - Support for multiple environments (development, staging, production).

2. **CI/CD**:
   - Set up GitHub Actions or GitLab CI for automated testing and deployment.
   - Automate database migrations and static file collection.

3. **Scaling**:
   - Optimize database queries and caching for performance.
   - Use a production-ready WSGI server (e.g., Gunicorn) and ASGI server (e.g., Daphne).

---

## **5. How to Use This Guide**
### **5.1. For AI-Assisted Development**
1. **Scope Clarity**:
   - Always refer to the **Project Overview** to understand the goals and architecture.
   - Use the **Key Features** section to identify relevant components.

2. **Lessons Learned**:
   - Review the **Lessons Learned** section to avoid common pitfalls.
   - Apply **Best Practices** to ensure code quality and consistency.

3. **Future Roadmap**:
   - Use the **Future Roadmap** to plan and prioritize tasks.
   - Align new features with the project’s long-term vision.

### **5.2. For Human Developers**
1. **Onboarding**:
   - Use this guide to onboard new team members.
   - Provide context on the project’s goals, architecture, and best practices.

2. **Documentation**:
   - Update this guide as the project evolves.
   - Add new lessons learned and best practices.

3. **Collaboration**:
   - Use this guide to align with AI-assisted development efforts.
   - Provide feedback and refinements to improve future iterations.

---

## **6. Resources**
- [Django Documentation](https://docs.djangoproject.com/)
- [DIDKit Documentation](https://github.com/spruceid/didkit)
- [HTMX Documentation](https://htmx.org/docs/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [W3C DID Core Specification](https://www.w3.org/TR/did-core/)
- [W3C Verifiable Credentials Data Model](https://www.w3.org/TR/vc-data-model/)
