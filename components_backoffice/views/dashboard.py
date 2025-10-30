from django.conf import settings
from django.http import Http404
from django.shortcuts import render



def _ensure_feature_enabled():
    if not getattr(settings, "ENABLE_COMPONENTS_BACKOFFICE", False):
        raise Http404()


def dashboard_view(request):
    _ensure_feature_enabled()
    if not getattr(request.user, "is_authenticated", False) or not getattr(request.user, "is_superuser", False):
        raise Http404()
    context = {}
    return render(request, "components_backoffice/dashboard.html", context)


