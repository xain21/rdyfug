from django.shortcuts import render
from .models import UserViewPermission


def _forbidden(request):
    message = f"Sorry {request.user.username}, you do not have permission to view this page."
    return render(request, 'forbidden.html', {'message': message})


def view_permission_required(view_name):
    """Legacy decorator for a fixed, literal permission name."""
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if request.user.is_superuser:
                return func(request, *args, **kwargs)

            if not UserViewPermission.objects.filter(user=request.user, view_name=view_name, can_view=True).exists():
                return _forbidden(request)

            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def category_permission_required(kind):
    """
    Dynamic permission check for the generic committee/category views.

    `kind` is either 'list' or 'details'. The actual permission checked is
    built from the category's slug at request time (e.g. 'list:hr',
    'details:it-support'), so a brand-new category created in Admin is
    automatically permission-controlled without any code change - an admin
    just grants UserViewPermission rows for it.
    """
    def decorator(func):
        def wrapper(request, *args, category_slug=None, **kwargs):
            if request.user.is_superuser or category_slug is None:
                return func(request, *args, category_slug=category_slug, **kwargs)

            view_name = f"{kind}:{category_slug}"
            if not UserViewPermission.objects.filter(user=request.user, view_name=view_name, can_view=True).exists():
                return _forbidden(request)

            return func(request, *args, category_slug=category_slug, **kwargs)
        return wrapper
    return decorator
