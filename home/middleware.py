from django.template.loader import render_to_string
from django.urls import resolve, Resolver404


class AiChatWidgetMiddleware:
    """Inject the AI chat widget into all HTML responses for authenticated users."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.user.is_authenticated:
            return response
        path = request.path_info
        if not path.startswith('/challenges/') and not path.startswith('/games/quiz/'):
            return response
        content_type = response.get('Content-Type', '')
        if 'text/html' not in content_type:
            return response
        try:
            resolve(request.path_info)
        except Resolver404:
            return response
        if hasattr(response, 'content') and b'</body>' in response.content:
            try:
                from django.middleware.csrf import get_token
                csrf_token = get_token(request)
                widget_html = render_to_string('ai_chat_widget.html', {
                    'user': request.user,
                    'csrf_token': csrf_token,
                }, request=request)
                response.content = response.content.replace(
                    b'</body>', widget_html.encode() + b'\n</body>'
                )
                if hasattr(response, 'charset'):
                    response['Content-Length'] = len(response.content)
            except Exception:
                pass
        return response
