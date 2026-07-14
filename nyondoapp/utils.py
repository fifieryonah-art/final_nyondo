from django.shortcuts import redirect
from functools import wraps

from .models import Employee


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            employee = getattr(request.user, "employee_profile", None)
            if employee is None:
                return redirect("login")

            if employee.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            return redirect("login")

        return wrapper

    return decorator


def admin_required(view_func):
    return role_required(["admin"])(view_func)


def manager_required(view_func):
    return role_required(["manager"])(view_func)


def attendant_required(view_func):
    return role_required(["attendant"])(view_func)