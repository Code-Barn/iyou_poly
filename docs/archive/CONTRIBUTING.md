# Contributing to Poly

Thank you for your interest in contributing to Poly! We welcome contributions from everyone, whether you're fixing a bug, adding a feature, improving documentation, or suggesting an idea. This document outlines the guidelines for contributing to the project.

---

## **Code of Conduct**

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it to understand the expectations for behavior in our community.

---

## **How to Contribute**

### **1. Reporting Issues**

If you encounter a bug, have a feature request, or want to suggest an improvement, please open an issue on GitHub. When reporting an issue, include the following details:

- A clear and descriptive title.
- A detailed description of the issue or suggestion.
- Steps to reproduce the issue (if applicable).
- Any relevant logs, screenshots, or error messages.

### **2. Setting Up the Development Environment**

To contribute to Poly, you'll need to set up a local development environment:

1. **Fork the Repository**: Create a fork of the Poly repository on GitHub.
2. **Clone the Repository**: Clone your fork to your local machine.
   ```bash
   git clone https://github.com/your-username/poly.git
   cd poly
   ```
3. **Set Up a Virtual Environment**: Create and activate a virtual environment.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   ```
4. **Install Dependencies**: Install the project dependencies.
   ```bash
   pip install -e .
   ```
5. **Run Migrations**: Apply the database migrations.
   ```bash
   python manage.py migrate
   ```
6. **Run the Development Server**: Start the development server.
   ```bash
   python manage.py runserver
   ```

### **3. Making Changes**

1. **Create a Branch**: Create a new branch for your changes.
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Write Code**: Implement your changes, ensuring they follow the project's coding standards.
3. **Write Tests**: Add unit tests for your changes to ensure they work as expected.
4. **Run Tests**: Run the test suite to verify your changes.
   ```bash
   python manage.py test
   ```
5. **Commit Changes**: Commit your changes with a clear and descriptive commit message.
   ```bash
   git commit -m "Add feature: your feature description"
   ```
6. **Push Changes**: Push your changes to your fork.
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request**: Open a pull request to the `main` branch of the Poly repository. Include a detailed description of your changes and any relevant issue numbers.

---

## **Coding Standards**

- **Python**: Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) for Python code.
- **Django**: Follow Django's [coding style](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/).
- **Documentation**: Write clear and concise docstrings for all functions, classes, and modules.
- **Testing**: Write unit tests for all new features and bug fixes. Ensure all tests pass before submitting a pull request.

---

## **Pull Request Guidelines**

- **Title**: Use a clear and descriptive title for your pull request.
- **Description**: Provide a detailed description of your changes, including the problem you're solving and the solution you've implemented.
- **Linked Issues**: Reference any relevant issues in your pull request description (e.g., "Fixes #123").
- **Tests**: Ensure your pull request includes tests for the changes you've made.
- **Documentation**: Update the documentation to reflect your changes, if applicable.

---

## **Review Process**

All pull requests will be reviewed by the project maintainers. During the review process, you may be asked to make changes to your code or documentation. Please address these requests promptly and update your pull request accordingly.

---

## **Community**

Join our community to discuss ideas, ask questions, and collaborate with other contributors:

- **GitHub Discussions**: [Poly Discussions](https://github.com/your-username/poly/discussions)
- **Chat**: [Poly Community Chat](https://chat.example.com)

---

## **License**

By contributing to Poly, you agree that your contributions will be licensed under the [MIT License](LICENSE).

---

Thank you for contributing to Poly! Your efforts help make this project better for everyone.