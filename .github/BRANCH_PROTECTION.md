# Branch Protection Configuration

This document outlines the branch protection rules to be applied to the repository for maximum security and code quality.

## Main Branch Protection Rules

### Required Settings for `main` branch:

1. **Require pull request reviews before merging**
   - ✅ Required number of reviewers: 1
   - ✅ Dismiss stale PR approvals when new commits are pushed
   - ✅ Require review from code owners (when CODEOWNERS file is added)

2. **Require status checks to pass before merging**
   - ✅ Require branches to be up to date before merging
   - ✅ Required status checks:
     - `Security & Quality`
     - `Test Suite (3.9)`
     - `Test Suite (3.10)` 
     - `Test Suite (3.11)`
     - `Test Suite (3.12)`
     - `Analysis Validation`
     - `Performance & Cost Check`
     - `Build Package`

3. **Require conversation resolution before merging**
   - ✅ All conversations must be resolved

4. **Require signed commits**
   - ⚠️ Optional but recommended for maximum security

5. **Require linear history**
   - ✅ Force squash merging to maintain clean history

6. **Restrictions**
   - ✅ Restrict pushes that create files larger than 100MB
   - ✅ Include administrators (even admins must follow rules)

## Develop Branch Protection Rules

### Required Settings for `develop` branch:

1. **Require pull request reviews before merging**
   - ✅ Required number of reviewers: 1

2. **Require status checks to pass before merging**
   - ✅ Required status checks:
     - `Security & Quality`
     - `Test Suite (3.9)`
     - `Analysis Validation`

## Rulebook for Developers

### Creating Feature Branches
```bash
# Always branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/descriptive-name

# Work on feature
git add .
git commit -m "feat: descriptive commit message"
git push -u origin feature/descriptive-name
```

### Pull Request Process
1. **Create PR** from `feature/branch` to `develop`
2. **Fill out PR template** (description, testing, breaking changes)
3. **Wait for CI/CD** to pass all checks
4. **Request review** from team member
5. **Address feedback** and resolve conversations
6. **Merge** when approved and all checks pass

### Merging to Main
1. **Create PR** from `develop` to `main`
2. **Comprehensive testing** (includes API integration tests)
3. **Review by senior developer** (when team grows)
4. **Deployment readiness check**
5. **Merge** creates production release

### Emergency Hotfixes
```bash
# For critical issues in production
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# Make minimal fix
git add .
git commit -m "hotfix: fix critical security vulnerability"
git push -u origin hotfix/critical-security-fix

# Create PR directly to main with expedited review
```

## Commit Message Convention

### Format
```
type(scope): description

body (optional)

footer (optional)
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `security`: Security improvements
- `perf`: Performance improvements

### Examples
```
feat(analyzer): add cost-optimized AI analysis engine
fix(fetcher): handle GitHub API rate limit gracefully
docs(readme): update installation instructions
security(validation): add input sanitization for URLs
```

## Code Review Checklist

### For Reviewers
- [ ] Code follows project style guidelines
- [ ] Tests cover new functionality
- [ ] No hardcoded secrets or API keys
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Documentation updated if needed
- [ ] Breaking changes clearly documented

### For Authors
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] No merge conflicts
- [ ] Commit messages follow convention
- [ ] PR description is clear and complete
- [ ] Screenshots/examples provided if applicable

## Implementation Instructions

To apply these rules to the GitHub repository:

1. **Go to Repository Settings > Branches**
2. **Add rule for `main` branch** with settings above
3. **Add rule for `develop` branch** with settings above
4. **Test with a dummy PR** to ensure rules work
5. **Document any deviations** from this standard

## Benefits of This Approach

✅ **Quality Assurance**: Every change is reviewed and tested
✅ **Security**: No direct pushes to main, all changes audited
✅ **Reliability**: Comprehensive CI/CD catches issues early
✅ **Collaboration**: Clear process for team development
✅ **Audit Trail**: Complete history of changes and approvals
✅ **Rollback Safety**: Can always revert to last known good state