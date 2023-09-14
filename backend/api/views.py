from django.contrib.auth.hashers import make_password, check_password
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import User, Tag, Ingredient, Recipe
from .serializers import (
    UserSerializer, AnonimusUserSerializer, ChangePasswordSerializer,
    TagSerializer, IngredientSerializer, RecipeSerializer
)
from .pagination import PageNumberLimitPagination
from .permissions import IsResponsibleUserOrReadOnly
from .filters import PartialNameFilter
from .decorators import not_allowed_put_method


class UserViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin,
    mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = (PageNumberLimitPagination)

    def perform_create(self, serializer):
        password = make_password(
            serializer.validated_data['password']
        )
        serializer.save(
            password=password
        )

    def get_permissions(self):
        if self.detail:
            self.permission_classes = (permissions.IsAuthenticated,)
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return AnonimusUserSerializer
        return self.serializer_class

    # def get_serializer_context(self):
    #     user = self.request.user
    #     if user.is_authenticated:
    #         followers = self.queryset.filter(
    #             subsriptions__user=self.request.user
    #         )
    #         return {
    #             'request': self.request,
    #             'format': self.format_kwarg,
    #             'view': self,
    #             'followers': followers,
    #         }
    #     return super().get_serializer_context()

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def me(self, request):
        followers = self.queryset.filter(subscriptions__user=request.user)
        serializer = UserSerializer(
            request.user,
            context={
                'request': request,
                'followers': followers,
            }
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=(permissions.IsAuthenticated,)
    )
    def set_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data
        )
        user = request.user
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        if not check_password(
            serializer.validated_data['current_password'],
            user.password
        ):
            return Response(
                {'current_password': 'Пароль не верен.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        user.password = make_password(
            serializer.validated_data['new_password']
        )
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = PartialNameFilter


@not_allowed_put_method
class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    pagination_class = (PageNumberLimitPagination)
    permission_classes = (IsResponsibleUserOrReadOnly,)

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user,
        )

    def destroy(self, request, *args, **kwargs):
        recipe = get_object_or_404(self.queryset, id=kwargs.get('pk'))
        recipe.tags.clear()
        recipe.ingredients.clear()
        return super().destroy(request, *args, **kwargs)
