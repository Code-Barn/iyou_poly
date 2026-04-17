"""
Cactus Comments integration for Polly polls and proposals.

Cactus Comments is a decentralized commenting system that uses the Matrix network.
This module provides integration for adding comment threads to polls and proposals.
"""

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def cactus_comments(poll_id, site_name="polly", homeserver_url="https://matrix.cactus.chat:8448", server_name="cactus.chat"):
    """
    Render Cactus Comments section for a poll or proposal.
    
    Usage:
        {% cactus_comments poll.id %}
        {% cactus_comments poll.id "my-site" "https://matrix.example.com:8448" "example.com" %}
    
    Args:
        poll_id: The ID of the poll or proposal
        site_name: Unique identifier for your site (registered with Cactusbot)
        homeserver_url: URL of the Matrix homeserver with Cactus Comments appservice
        server_name: Server name of the Matrix homeserver
    """
    comment_section_id = f"poll_{poll_id}"
    
    return mark_safe(f'''
    <div class="cactus-comments-wrapper" 
         data-site-name="{site_name}"
         data-comment-section-id="{comment_section_id}"
         data-homeserver-url="{homeserver_url}"
         data-server-name="{server_name}">
        <div id="cactus-comments-{poll_id}" class="cactus-comments-container">
            <p class="cactus-loading">Loading comments...</p>
        </div>
    </div>
    <script>
    (function() {{
        // Load Cactus Comments script dynamically
        if (typeof initComments !== 'undefined') {{
            initComments({{
                node: document.getElementById('cactus-comments-{poll_id}'),
                defaultHomeserverUrl: '{homeserver_url}',
                serverName: '{server_name}',
                siteName: '{site_name}',
                commentSectionId: '{comment_section_id}',
                pageSize: 10,
                loginEnabled: true,
                guestPostingEnabled: true
            }});
        }} else {{
            // Load external script if not already loaded
            var script = document.createElement('script');
            script.src = 'https://cactus.chat/cactus.js';
            script.onload = function() {{
                initComments({{
                    node: document.getElementById('cactus-comments-{poll_id}'),
                    defaultHomeserverUrl: '{homeserver_url}',
                    serverName: '{server_name}',
                    siteName: '{site_name}',
                    commentSectionId: '{comment_section_id}',
                    pageSize: 10,
                    loginEnabled: true,
                    guestPostingEnabled: true
                }});
            }};
            document.head.appendChild(script);
            
            // Load styles
            var link = document.createElement('link');
            link.rel = 'stylesheet';
            link.href = 'https://cactus.chat/style.css';
            document.head.appendChild(link);
        }}
    }})();
    </script>
    ''')


@register.simple_tag
def cactus_comments_count(poll_id, site_name="polly"):
    """
    Get comment count for a poll without rendering the full comments UI.
    Useful for displaying "X comments" next to poll links.
    """
    return 0  # Cactus doesn't provide a simple count API; this is a placeholder


class CactusCommentsWidget:
    """
    Server-side widget for rendering Cactus Comments with server-side rendering support.
    Use this for SSR or when you need more control over the comments integration.
    """
    
    def __init__(self, poll_id, site_name="polly", homeserver_url="https://matrix.cactus.chat:8448", server_name="cactus.chat"):
        self.poll_id = poll_id
        self.site_name = site_name
        self.homeserver_url = homeserver_url
        self.server_name = server_name
        self.comment_section_id = f"poll_{poll_id}"
    
    def render(self):
        """Render the Cactus Comments widget HTML."""
        return mark_safe(f'''
        <div id="cactus-comments-{self.poll_id}" class="cactus-comments-container"
             data-site-name="{self.site_name}"
             data-comment-section-id="{self.comment_section_id}"
             data-homeserver-url="{self.homeserver_url}"
             data-server-name="{self.server_name}">
        </div>
        ''')
    
    def get_embed_code(self):
        """Get the embed code for this comment section."""
        return f'''
        <!-- Cactus Comments for Poll #{self.poll_id} -->
        <script src="https://cactus.chat/cactus.js"></script>
        <link rel="stylesheet" href="https://cactus.chat/style.css">
        <div id="cactus-comments-{self.poll_id}"></div>
        <script>
        initComments({{
            node: document.getElementById('cactus-comments-{self.poll_id}'),
            defaultHomeserverUrl: '{self.homeserver_url}',
            serverName: '{self.server_name}',
            siteName: '{self.site_name}',
            commentSectionId: 'poll_{self.poll_id}',
            pageSize: 10,
            loginEnabled: true,
            guestPostingEnabled: true
        }});
        </script>
        '''


def get_cactus_config():
    """
    Get the Cactus Comments configuration from settings or defaults.
    Extend this to add settings-based configuration.
    """
    from django.conf import settings
    
    return {
        "homeserver_url": getattr(settings, "CACTUS_HOMESERVER_URL", "https://matrix.cactus.chat:8448"),
        "server_name": getattr(settings, "CACTUS_SERVER_NAME", "cactus.chat"),
        "site_name": getattr(settings, "CACTUS_SITE_NAME", "polly"),
        "login_enabled": getattr(settings, "CACTUS_LOGIN_ENABLED", True),
        "guest_posting_enabled": getattr(settings, "CACTUS_GUEST_POSTING_ENABLED", True),
    }