import django_filters.rest_framework
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import filters, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import RecipeFilter
from .models import (Favorite, Ingredient, IngredientRecipe, Purchase, Recipe,
                     Subscribe, Tag)
from .permissions import AdminOrAuthorOrReadOnly
from .serializers import (CreateRecipeSerializer, FavoriteSerializer,
                          IngredientSerializer, ListRecipeSerializer,
                          PurchaseSerializer, ShowFollowersSerializer,
                          SubscribeSerializer, TagSerializer)

User = get_user_model()


class TagsViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    filter_backends = [django_filters.rest_framework.DjangoFilterBackend]
    filter_class = RecipeFilter
    pagination_class = PageNumberPagination
    permission_classes = [AdminOrAuthorOrReadOnly]

    def get_serializer_class(self):
        if self.action in ['list']:
            return ListRecipeSerializer
        return CreateRecipeSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({'request': self.request})
        return context


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny, ]
    pagination_class = None
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', ]


@api_view(['get'])
@permission_classes([IsAuthenticated])
def show_subscribs(request):
    user_ubj = User.objects.filter(following__user=request.user)
    paginator = PageNumberPagination
    paginator.page_size = 10
    result_page = paginator.paginate_queryset(user_ubj, request)
    serializer = ShowFollowersSerializer(
        result_page,
        many=True,
        context={'current_user': request.user}
    )
    return paginator.get_paginated_response(serializer.data)


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id):
        user = request.user
        data = {
            'user': user.id,
            'author': author_id
        }
        serializer = SubscribeSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status.HTTP_201_CREATED)

    def delete(self, request, user_id):
        user = request.user
        follow = get_object_or_404(
            Subscribe,
            user=user,
            author_id=user_id
        )
        follow.delete()
        return Response('Подписка удалена', status.HTTP_204_NO_CONTENT)


class FavoriteViewSet(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request, recipe_id):
        user = request.user
        data = {
            'user': user,
            'recipe_id': recipe_id
        }
        serializer = FavoriteSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status.HTTP_201_CREATED)

    def delete(self, request, recipe_id):
        user = request.user
        favorite_recipe = get_object_or_404(
            Favorite,
            user=user,
            recipe_id=recipe_id
        )
        favorite_recipe.delete()
        return Response(
            'Рецепт удален из избранного',
            status.HTTP_204_NO_CONTENT
        )


class PurchaseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, recipe_id):
        user = request.user
        data = {
            'user': user,
            'recipe_id': recipe_id
        }
        serializer = PurchaseSerializer(
            data=data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status.HTTP_201_CREATED)

    def delete(self, request, recipe_id):
        user = request.user
        purchace_list_recipe = get_object_or_404(
            Purchase,
            user=user,
            recipe_id=recipe_id
        )
        purchace_list_recipe.delete()
        return Response(
            'Рецепт удален из списка покупок',
            status.HTTP_204_NO_CONTENT
        )


class DownloadPurchaseList(APIView):
    permission_classes = [IsAuthenticated, ]

    def get(self, request):
        user = request.user
        shopping_cart = user.purchase.all()
        purchase_list = {}
        for record in shopping_cart:
            recipe = record.recipe
            ingredients = IngredientRecipe.objects.filter(recipe=recipe)
            for ingredient in ingredients:
                amount = ingredient.amout
                name = ingredient.name
                measurement_unit = ingredient.measurement_unit
                if name is not purchase_list:
                    purchase_list[name] = {
                        'measurement_unit': measurement_unit,
                        'amount': amount
                    }
                else:
                    purchase_list[name]['amount'] = (
                        purchase_list[name]['amount'] + amount
                    )
        wishlist = []
        for item in purchase_list:
            wishlist.append(
                f'{item} - {purchase_list[item]["amount"]}'
                f'{purchase_list[item]["measurement_unit"]}/n'
            )
        wishlist.append('/n')
        wishlist.append('FoodGram, 2021')
        response = HttpResponse(wishlist, 'Content-Type: application/pdf')
        response['Content-Disposition'] = 'attachment; filename="wishlist.pdf"'
        return response
