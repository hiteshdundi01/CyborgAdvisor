# Contributing to Cyborg Advisor

First off, thanks for taking the time to contribute!

The following is a set of guidelines for contributing to Cyborg Advisor. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Code of Conduct

This project and everyone participating in it is governed by the [Cyborg Advisor Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

- **Use a clear and descriptive title** for the issue to identify the problem.
- **Describe the exact steps to reproduce the problem** in as many details as possible.
- **Provide specific examples to demonstrate the steps**. Include copy/pasteable snippets, which you use in those examples.
- **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
- **Explain which behavior you expected to see instead and why.**

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

- **Use a clear and descriptive title** for the issue to identify the suggestion.
- **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
- **Explain why this enhancement would be useful** to most Cyborg Advisor users.

### Pull Requests

The process described here has several goals:

- Maintain Cyborg Advisor's quality
- Fix problems that are important to users
- Engage the community in working toward the best possible Cyborg Advisor
- Enable a sustainable system for Cyborg Advisor's maintainers to review contributions

Please follow these steps to have your contribution considered by the maintainers:

1.  Follow certain instructions in the [README.md](README.md) to get the development environment running.
2.  Follow the style guides (PEP 8 for Python).
3.  Run the test suite to ensure that nothing is broken (e.g., `pytest`).
4.  After you submit your pull request, verify that all status checks are passing.

## Styleguides

### Python Styleguide

- All Python code should be PEP 8 compliant.
- Use meaningful variable names.
- Type hinting is encouraged for all function signatures.

### Documentation Styleguide

- Use [Markdown](https://daringfireball.net/projects/markdown).
- Reference functions and classes in code blocks.

## Setting Up the Development Environment

1.  Clone the repository.
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Run tests:
    ```bash
    pytest
    ```
