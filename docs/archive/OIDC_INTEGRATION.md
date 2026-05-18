# OpenID Connect (OIDC) Integration Guide

## Overview

Poly supports **OpenID Connect (OIDC)** for seamless integration with external identity providers like **Google, GitHub, GitLab, Microsoft, and more**. OIDC is an identity layer built on top of the OAuth 2.0 protocol, allowing users to authenticate using their existing accounts from trusted providers.

This guide provides a comprehensive overview of how to integrate OIDC into Poly, including setup instructions, configuration options, and best practices.

---

## Key Features

- **Multi-Provider Support**: Integrate with any OIDC-compliant provider.
- **Auto-Provisioning**: Automatically create user accounts for new OIDC logins.
- **Hybrid Authentication**: Combine OIDC with DID and traditional username/password authentication.
- **Customizable Pipeline**: Extend the authentication pipeline to suit your needs.
- **Secure**: Built-in security features like token validation and CSRF protection.

---

## Prerequisites

Before integrating OIDC, ensure you have the following:

1. **Python 3.13+** and **Django 6.0+** installed.
2. **`python-social-auth`** installed:
   ```bash
   pip install social-auth-app-django
   ```
3. A **registered application** with your OIDC provider (e.g., Google, GitHub, GitLab).
4. **Callback/Redirect URIs** configured in your OIDC provider's dashboard.

---

## Setup

### 1. Install `python-social-auth`

Poly uses the [`python-social-auth`](https://python-social-auth.readthedocs.io/) library to integrate with OIDC providers. Install it using pip:

```bash
pip install social-auth-app-django
```

### 2. Add `social_django` to `INSTALLED_APPS`

Add `social_django` to your `INSTALLED_APPS` in `settings.py`:

```python
# settings.py
INSTALLED_APPS = [
    ...
    'social_django',
    ...
]
```

### 3. Configure Authentication Backends

Add the OIDC backends to `AUTHENTICATION_BACKENDS` in `settings.py`:

```python
# settings.py
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Traditional username/password
    'social_core.backends.google.GoogleOAuth2',    # Google OIDC
    'social_core.backends.github.GithubOAuth2',    # GitHub OIDC
    'apps.accounts.backends.HybridAuthBackend',    # Hybrid backend (DID + OIDC + password)
]
```

### 4. Configure OIDC Providers

Add the credentials for your OIDC providers in `settings.py`. Example configurations for **Google** and **GitHub** are shown below:

#### Google OAuth2

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services > Credentials**.
4. Click **Create Credentials > OAuth Client ID**.
5. Select **Web Application** as the application type.
6. Add the following **Authorized Redirect URIs**:
   ```
   http://localhost:8000/complete/google-oauth2/
   ```
7. Copy the **Client ID** and **Client Secret** into `settings.py`:

```python
# settings.py
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = 'your-google-oauth2-key'
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = 'your-google-oauth2-secret'
```

#### GitHub OAuth2

1. Go to [GitHub Developer Settings](https://github.com/settings/developers).
2. Click **New OAuth App**.
3. Enter the following details:
   - **Application Name**: Poly
   - **Homepage URL**: `http://localhost:8000/`
   - **Authorization Callback URL**:
     ```
     http://localhost:8000/complete/github/
     ```
4. Copy the **Client ID** and **Client Secret** into `settings.py`:

```python
# settings.py
SOCIAL_AUTH_GITHUB_KEY = 'your-github-key'
SOCIAL_AUTH_GITHUB_SECRET = 'your-github-secret'
```

### 5. Configure the Authentication Pipeline

The authentication pipeline defines the steps taken during the OIDC authentication process. Poly uses the default pipeline with some customizations. Add the following to `settings.py`:

```python
# settings.py
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)
```

#### Customizing the Pipeline

You can extend the pipeline to add custom logic, such as:

- **Auto-provisioning user profiles**.
- **Linking OIDC accounts to existing users**.
- **Storing additional user data**.

Example of a custom pipeline step:

```python
# apps/accounts/pipeline.py
def save_profile(backend, user, response, *args, **kwargs):
    """Save additional user data from OIDC provider."""
    if backend.name == 'google-oauth2':
        user.email = response.get('email')
        user.first_name = response.get('given_name')
        user.last_name = response.get('family_name')
        user.save()
```

Add the custom step to the pipeline in `settings.py`:

```python
# settings.py
SOCIAL_AUTH_PIPELINE = (
    ...
    'apps.accounts.pipeline.save_profile',
    ...
)
```

### 6. Add OIDC URLs

Add the OIDC URLs to your `urls.py`:

```python
# config/urls.py
from django.urls import path, include

urlpatterns = [
    ...
    path('auth/', include('social_django.urls', namespace='social')),
    ...
]
```

### 7. Update the Login Template

Add OIDC login buttons to your login template (`templates/accounts/login.html`):

```html
<!-- templates/accounts/login.html -->
<div class="space-y-2">
    <a href="{% url 'social:begin' 'google-oauth2' %}"
       class="block w-full text-center bg-red-600 text-white p-2 rounded">
        Login with Google
    </a>
    <a href="{% url 'social:begin' 'github' %}"
       class="block w-full text-center bg-gray-800 text-white p-2 rounded">
        Login with GitHub
    </a>
</div>
```

---

## Advanced Configuration

### 1. Adding a Custom OIDC Provider

To add a custom OIDC provider (e.g., GitLab, Microsoft), follow these steps:

1. **Install the provider's backend** (if not already available in `python-social-auth`):
   ```bash
   pip install social-auth-app-django
   ```

2. **Add the provider's backend** to `AUTHENTICATION_BACKENDS` in `settings.py`:
   ```python
   AUTHENTICATION_BACKENDS = [
       ...
       'social_core.backends.gitlab.GitLabOAuth2',
       'social_core.backends.microsoft.MicrosoftOAuth2',
   ]
   ```

3. **Configure the provider's credentials** in `settings.py`:
   ```python
   # GitLab
   SOCIAL_AUTH_GITLAB_KEY = 'your-gitlab-key'
   SOCIAL_AUTH_GITLAB_SECRET = 'your-gitlab-secret'

   # Microsoft
   SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = 'your-microsoft-key'
   SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = 'your-microsoft-secret'
   ```

4. **Add the provider's login button** to your login template:
   ```html
   <a href="{% url 'social:begin' 'gitlab' %}"
      class="block w-full text-center bg-orange-600 text-white p-2 rounded">
       Login with GitLab
   </a>
   ```

### 2. Scopes and Permissions

You can request additional scopes from the OIDC provider to access more user data. For example, to request the user's email and profile from Google:

```python
# settings.py
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']
```

### 3. Logging Out

To log users out of both Poly and the OIDC provider, add the following to your logout view:

```python
# apps/accounts/views.py
from django.contrib.auth import logout
from social_django.utils import psa

@psa('social:complete')
def custom_logout(request, backend):
    """Logout from both Poly and the OIDC provider."""
    logout(request)
    return redirect('login')
```

### 4. Handling Errors

Customize error handling for OIDC authentication failures. Example:

```python
# apps/accounts/views.py
from social_django.views import auth, complete

def oidc_error(request):
    """Custom error handling for OIDC authentication."""
    error = request.GET.get('error', 'Unknown error')
    return render(request, 'accounts/oidc_error.html', {'error': error})
```

Add the error URL to `urls.py`:

```python
# config/urls.py
from django.urls import path
from apps.accounts.views import oidc_error

urlpatterns = [
    ...
    path('auth/error/', oidc_error, name='oidc_error'),
    ...
]
```

---

## Troubleshooting

### 1. OIDC Provider Not Redirecting

- **Symptom**: After clicking an OIDC provider, the page does not redirect.
- **Solution**:
  - Ensure the provider's credentials (`SOCIAL_AUTH_<PROVIDER>_KEY` and `SOCIAL_AUTH_<PROVIDER>_SECRET`) are correct.
  - Verify that the provider's callback URL is configured correctly in the provider's dashboard.
  - Check the Django logs for errors.

### 2. Authentication Failing with "Invalid Credentials"

- **Symptom**: Authentication fails with an "Invalid Credentials" error.
- **Solution**:
  - Ensure the provider's credentials are correct.
  - Verify that the provider's callback URL matches the one configured in the provider's dashboard.
  - Check the provider's API status for outages.

### 3. User Not Auto-Provisioned

- **Symptom**: New users are not automatically created after OIDC login.
- **Solution**:
  - Ensure `AUTO_PROVISION_DID_USERS` is set to `True` in `settings.py`.
  - Verify that the authentication pipeline includes the `create_user` step.
  - Check the Django logs for errors during user creation.

### 4. Missing User Data

- **Symptom**: User data (e.g., email, name) is not being saved after OIDC login.
- **Solution**:
  - Ensure the provider's scopes include the required permissions (e.g., `email`, `profile`).
  - Add a custom pipeline step to save the user data (see [Customizing the Pipeline](#customizing-the-pipeline)).

---

## Best Practices

1. **Secure Credentials**:
   - Store OIDC credentials in environment variables or a secure secrets manager.
   - Never hardcode credentials in `settings.py`.

2. **Use HTTPS**:
   - Always use HTTPS in production to secure authentication flows.

3. **Limit Scopes**:
   - Only request the scopes you need from the OIDC provider.

4. **Error Handling**:
   - Implement custom error handling for OIDC authentication failures.

5. **Logging**:
   - Log authentication events for debugging and security auditing.

6. **Testing**:
   - Test OIDC integration in a staging environment before deploying to production.

7. **Documentation**:
   - Document the OIDC setup process for your team and users.

---

## Further Reading

- [python-social-auth Documentation](https://python-social-auth.readthedocs.io/)
- [OpenID Connect Specification](https://openid.net/connect/)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)