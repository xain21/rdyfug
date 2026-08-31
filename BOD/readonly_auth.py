from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password


class ReadOnlyModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()

        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            user = UserModel._default_manager.get(
                **{UserModel.USERNAME_FIELD: username}
            )
        except UserModel.DoesNotExist:
            return None

        # Validate the existing password hash without upgrading it.
        if check_password(password, user.password):
            if self.user_can_authenticate(user):
                return user

        return None