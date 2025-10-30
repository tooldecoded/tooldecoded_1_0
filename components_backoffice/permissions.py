from django.contrib.auth.models import Group


REQUIRED_GROUP_NAME = "Components Editors"


def user_is_components_editor(user) -> bool:
    if not user.is_authenticated:
        return False
    # Only superusers are allowed per project policy
    return bool(getattr(user, "is_superuser", False))


