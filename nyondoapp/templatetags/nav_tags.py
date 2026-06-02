from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, *names):
    """Return 'active' if the current request URL name matches any provided names."""
    request = context.get('request')
    if not request:
        return ''
    resolver_match = getattr(request, 'resolver_match', None)
    if not resolver_match:
        return ''
    current = resolver_match.url_name
    return 'active' if current in names else ''
