# Template Organization

This document outlines the template organization strategy for the Polly project. The goal is to ensure consistency, reusability, scalability, and maintainability across all templates.

---

## **1. Template Hierarchy**

The project follows a structured template hierarchy to separate global, app-specific, and reusable components:

```
polly/
├── templates/                  # Project-wide templates
│   ├── base.html               # Base template (shared layout)
│   ├── registration/           # Authentication templates (login, register, etc.)
│   │   ├── login.html
│   │   ├── register.html
│   │   └── ...
│   ├── partials/               # Reusable partial templates (e.g., navbar, footer)
│   │   ├── navbar.html
│   │   ├── footer.html
│   │   └── ...
│   └── README.md               # This file
└── apps/
    └── <app_name>/             # App-specific templates
        └── templates/
            └── <app_name>/     # App-specific templates (e.g., poll_list.html)
                ├── poll_list.html
                ├── poll_detail.html
                └── partials/   # App-specific partials (e.g., vote_results.html)
                    └── vote_results.html
```

---

## **2. Naming Conventions**

### **2.1 Base Template**
- **`base.html`**: The shared layout template that all other templates extend.

### **2.2 App-Specific Templates**
- **`<app_name>/<template_name>.html`**: App-specific templates (e.g., `poller/poll_list.html`).
- **Example**:
  - `poller/poll_list.html`
  - `poller/poll_detail.html`

### **2.3 Partial Templates**
- **`partials/_<partial_name>.html`**: Reusable partial templates (e.g., `partials/_navbar.html`).
- **OR**: Place partials in a `partials/` subdirectory within the app (e.g., `poller/partials/vote_results.html`).

### **2.4 Authentication Templates**
- **`registration/<template_name>.html`**: Templates for authentication flows (e.g., `registration/login.html`).

---

## **3. Template Blocks**

The `base.html` template defines the following blocks for customization:

| Block Name   | Purpose                          | Example Usage                     |
|--------------|----------------------------------|-----------------------------------|
| `title`      | Page title                       | `{% block title %}Login{% endblock %}` |
| `head`       | Additional CSS/JS                | `{% block head %}<link rel="stylesheet" href="custom.css">{% endblock %}` |
| `content`    | Main content                     | `{% block content %}<h1>Hello!</h1>{% endblock %}` |
| `scripts`    | Page-specific JavaScript         | `{% block scripts %}<script src="custom.js"></script>{% endblock %}` |

---

## **4. Static Assets**

Static assets (CSS, JS, images) are organized as follows:

```
polly/
└── static/
    ├── css/          # Global CSS files
    ├── js/           # Global JavaScript files
    ├── images/       # Global images
    └── <app_name>/   # App-specific static assets
        ├── css/
        ├── js/
        └── images/
```

### **4.1 Using Static Assets**
- Use the `{% static %}` template tag to reference static assets:
  ```html
  <link rel="stylesheet" href="{% static 'css/styles.css' %}">
  <script src="{% static 'js/scripts.js' %}"></script>
  <img src="{% static 'images/logo.png' %}" alt="Logo">
  ```

---

## **5. Template Inheritance**

All templates **must** extend `base.html` and override blocks as needed:

```html
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
    <h1>Hello, World!</h1>
{% endblock %}
```

---

## **6. Adding New Templates**

### **6.1 Project-Wide Templates**
1. Place the template in `polly/templates/`.
2. Extend `base.html` and override blocks as needed.
3. Include reusable partials using `{% include "partials/<partial_name>.html" %}`.

### **6.2 App-Specific Templates**
1. Place the template in `polly/apps/<app_name>/templates/<app_name>/`.
2. Extend `base.html` and override blocks as needed.
3. Include reusable partials using `{% include "<app_name>/partials/<partial_name>.html" %}`.

### **6.3 Partial Templates**
1. Place the partial in `polly/templates/partials/` (for project-wide partials) or `polly/apps/<app_name>/templates/<app_name>/partials/` (for app-specific partials).
2. Include the partial in other templates using `{% include "partials/<partial_name>.html" %}`.

---

## **7. Best Practices**

### **7.1 Reusability**
- Maximize reuse of partials (e.g., navbar, footer, forms).
- Avoid duplicating code across templates.

### **7.2 Consistency**
- Follow the naming conventions outlined above.
- Use consistent indentation (4 spaces) and formatting.

### **7.3 Accessibility**
- Use semantic HTML (e.g., `<nav>`, `<main>`, `<footer>`).
- Include `alt` text for images.
- Ensure keyboard navigability.

### **7.4 Performance**
- Minimize the use of inline JavaScript/CSS.
- Use `{% static %}` for asset references to enable caching.

---

## **8. Example Workflow**

### **8.1 Creating a New Page**
1. Create a new template in `polly/apps/<app_name>/templates/<app_name>/<template_name>.html`.
2. Extend `base.html` and override the `content` block:
   ```html
   {% extends "base.html" %}

   {% block title %}New Page{% endblock %}

   {% block content %}
       <h1>Welcome to the New Page!</h1>
   {% endblock %}
   ```
3. Add a URL route in `polly/apps/<app_name>/urls.py`:
   ```python
   from django.urls import path
   from .views import NewPageView

   urlpatterns = [
       path("new-page/", NewPageView.as_view(), name="new_page"),
   ]
   ```
4. Add a view in `polly/apps/<app_name>/views.py`:
   ```python
   from django.views import View
   from django.shortcuts import render

   class NewPageView(View):
       def get(self, request):
           return render(request, "<app_name>/new_page.html")
   ```

### **8.2 Creating a Reusable Partial**
1. Create a partial in `polly/templates/partials/_alert.html`:
   ```html
   <div class="alert alert-{{ type }}">
       {{ message }}
   </div>
   ```
2. Include the partial in another template:
   ```html
   {% include "partials/alert.html" with type="success" message="Operation completed!" %}
   ```

---

## **9. Troubleshooting**

### **9.1 Template Not Found**
- Ensure the template is in the correct directory.
- Verify the template name and path in the `render()` call or `{% include %}` tag.
- Check that `APP_DIRS: True` is set in `config/settings.py`.

### **9.2 Static Files Not Loading**
- Ensure `django.contrib.staticfiles` is in `INSTALLED_APPS`.
- Verify that `STATIC_URL` is set in `config/settings.py`.
- Use the `{% static %}` template tag to reference static files.

### **9.3 Block Not Overriding**
- Ensure the block name matches exactly (case-sensitive).
- Verify that the template extends `base.html`.

---

## **10. Future Enhancements**

### **10.1 Template Theming**
- Add support for dark mode and custom themes.
- Use CSS variables for theming (e.g., `--primary-color`).

### **10.2 Component Library**
- Create a library of reusable UI components (e.g., modals, cards, forms).
- Document components in this `README.md`.

### **10.3 Internationalization (i18n)**
- Add support for multiple languages using Django’s i18n framework.
- Use `{% trans %}` and `{% blocktrans %}` tags for translatable content.

---

## **11. Resources**

- [Django Template Documentation](https://docs.djangoproject.com/en/6.0/topics/templates/)
- [Django Static Files Documentation](https://docs.djangoproject.com/en/6.0/howto/static-files/)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [HTMX Documentation](https://htmx.org/docs/)