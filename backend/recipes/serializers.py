from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer as BaseUserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from .models import (Favorite, Ingredient, IngredientRecipe, Purchase, Recipe,
                     Subscribe, Tag)

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class SubscribeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscribe
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name', 'purchases'
        )

    def validata(self, data):
        user = self.context['request'].user
        author = data['author'].author_id

        if (self.context['request'].method == 'GET'
                and Subscribe.objects.filter(
                    user=user, author=author).exists()):
            raise serializers.ValidationError('Вы уже подписаны')


class AddFavouriteRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = '__all__'

        def validata(self, data):
            user = self.context['request'].user
            recipe_id = data['request'].recipe_id

            if (self.context['requests'].method == 'GET'
                    and Favorite.objects.filter(
                        user=user, recipe__id=recipe_id).exists()):
                raise serializers.ValidationError(
                    'Рецепт уже добавлен в избранное'
                )
            recipe = get_object_or_404(Recipe, id=recipe_id)

            if (self.context['request'].method == 'DELETE'
                    and Favorite.objeacts.filter(
                        user=user, recipe=recipe).exists()):
                raise serializers.ValidationError()
            return data


class ShoppingListRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = '__all__'


class ListRecipeUserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=request.user, author=obj).exists()


class IngredientInRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = IngredientRecipe
        fields = '__all__'


class IngredientInRecipeSerializerToCreateRecipe(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount',)


class ListRecipeSerializer(serializers.ModelSerializer):
    author = ListRecipeUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_ingredients(self, obj):
        qs = IngredientRecipe.objects.filter(recipe=obj)
        return IngredientInRecipeSerializerToCreateRecipe(qs, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        user = request.user
        return Favorite.objects.filter(recipe=obj, user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        user = request.user
        return Purchase.objects.filter(recipe=obj, user=user).exists()


class RecipeSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None,
        required=True,
        allow_empty_file=False,
        use_url=True,
    )
    author = ListRecipeUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)

    class Meta:
        model = Recipe
        fields = '__all__'


class ShowFollowerRecipeSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(
        max_length=None,
        required=True,
        allow_empty_file=False,
        use_url=True,
    )

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class ShowFollowersSerializer(serializers.ModelSerializer):

    recipes = ShowFollowerRecipeSerializer(many=True, read_only=True)
    recipes_count = serializers.SerializerMethodField('count_author_recipes')
    is_subscribed = serializers.SerializerMethodField('check_if_subscribed')

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')

    def count_author_recipes(self, user):
        return len(user.recipes.all())

    def check_if_subscribed(self, user):
        current_user = self.context.get('current_user')
        other_user = user.following.all()
        if user.is_anonymous:
            return False
        if other_user.count() == 0:
            return False
        return Subscribe.objects.filter(
            user=user, author=current_user
        ).exists()


class ShowIngredientsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'amount', )


class UserSerializerModified(BaseUserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return Subscribe.objects.filter(user=request.user, author=obj).exists()


class ShowRecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializerModified(read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_ingredients(self, obj):
        qs = IngredientRecipe.objects.filter(recipe=obj)
        return IngredientInRecipeSerializer(qs, many=True).data

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        user = request.user
        return Favorite.objects.filter(recipe=obj, user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        user = request.user
        return Purchase.objects.filter(recipe=obj, user=user).exists()


class AddIngredientToRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField()

    class Meta:
        model = Ingredient
        fields = ('id', 'amount')


class CreateRecipeSerializer(serializers.ModelSerializer):
    image = Base64ImageField(max_length=None, use_url=True)
    author = UserSerializerModified(read_only=True)
    ingredients = AddIngredientToRecipeSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'name', 'image', 'text', 'cooking_time')

    def create(self, validated_data):
        tags_data = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        for ingredient in ingredients_data:
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше нуля!')
        author = self.context.get('request').user
        recipe = Recipe.objects.create(
            author=author, **validated_data)
        recipe.save()
        recipe.tags.set(tags_data)
        for ingredient in ingredients_data:
            ingredient_model = Ingredient.objects.get(id=ingredient['id'])
            amount = ingredient['amount']
            IngredientRecipe.objects.create(
                ingredient=ingredient_model,
                recipe=recipe,
                amount=amount
            )
        return recipe

    def update(self, instance, validated_data):
        ingredient_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        for ingredient in ingredient_data:
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше нуля!')
        IngredientRecipe.objects.filter(recipe=instance).delete()
        for new_ingredient in ingredient_data:
            IngredientRecipe.objects.create(
                ingredient=Ingredient.objects.get(id=new_ingredient['id']),
                recipe=instance,
                amount=new_ingredient['amount']
            )
        instance.name = validated_data.pop('name')
        instance.text = validated_data.pop('text')
        if validated_data.get('image') is not None:
            instance.image = validated_data.pop('image')
        instance.cooking_time = validated_data.pop('cooking_time')
        instance.save()
        instance.tags.set(tags_data)
        return instance

    def to_representation(self, instance):
        return ShowRecipeSerializer(
            instance,
            context={
                'request': self.context.get('request')
            }
        ).data





#
# class FavoriteSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = Favorite
#         fields = '__all__'
#
#     def validata(self, data):
#         user = self.context['request'].user
#         recipe_id = data['request'].recipe_id
#
#         if (self.context['requests'].method == 'GET'
#                 and Favorite.objects.filter(
#                     user=user, recipe__id=recipe_id).exists()):
#             raise serializers.ValidationError(
#                 'Рецепт уже добавлен в избранное'
#             )
#         recipe = get_object_or_404(Recipe, id=recipe_id)
#
#         if (self.context['request'].method == 'DELETE'
#                 and Favorite.objeacts.filter(
#                     user=user, recipe=recipe).exists()):
#             raise serializers.ValidationError()
#         return data
#
#
# class PurchaseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Purchase
#         fields = '__all__'
#
#     def validata(self, data):
#         user = self.context['request'].user
#         recipe_id = data['request'].recipe_id
#
#         if (self.context['request'].method == 'GET'
#                 and Purchase.objects.filter(
#                     user=user,
#                     recipe__id=recipe_id).exists()):
#             raise serializers.ValidationError(
#                 'Вы уже добавили рецепт в список покупок'
#             )
#
#         recipe = get_object_or_404(Recipe, id=recipe_id)
#
#         if (self.context['request'].method == 'DELETE'
#                 and Purchase.objects.filter(
#                     user=user,
#                     recipe=recipe).exists()):
#             raise serializers.ValidationError()
#
#
# class CreateFavoriteRecipeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Recipe
#         fields = '__all__'
#
#
# class PurchaseListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Recipe
#         fields = '__all__'
#
#
# class ListRecipeUserSerializer(serializers.ModelSerializer):
#     is_subscribe = serializers.SerializerMethodField()
#
#     class Meta:
#         model = User
#         fields = ('email', 'id', 'username',
#                   'first_name', 'last_name', 'is_subscribed')
#
#     def get_is_subscribe(self, obj):
#         request = self.context['request']
#         if request is None or request.user.is_anonymous:
#             return False
#         return Subscribe.objects.filters(
#             user=request.user, author=obj
#         ).exists()
#
#
# class IngredientCreateRecipeSerializer(serializers.ModelSerializer):
#     id = IngredientSerializer()
#
#     class Meta:
#         model = IngredientRecipe
#         fields = '__all__'
#
#
# class RecipeSerializer(serializers.ModelSerializer):
#     image = serializers.ImageField(
#         max_length=None,
#         required=True,
#         allow_empty_file=False,
#         use_url=True,
#     )
#     author = ListRecipeUserSerializer(read_only=True)
#     tags = TagSerializer(many=True, read_only=True)
#     ingredients = IngredientSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = Recipe
#         fields = '__all__'
#
# class ShowSubscriberRecipeSerializer(serializers.ModelSerializer):
#     image = serializers.ImageField(
#         max_length=None,
#         required=True,
#         allow_empty_file=False,
#         use_url=True,
#     )
#
#     class Meta:
#         model = Recipe
#         fields = ('id', 'name', 'image', 'cooking_time')
#
#
# class ShowFollowersSerializer(serializers.ModelSerializer):
#
#     recipes = ShowSubscriberRecipeSerializer(many=True, read_only=True)
#     recipes_count = serializers.SerializerMethodField('count_author_recipes')
#     is_subscribed = serializers.SerializerMethodField('check_if_subscribed')
#
#     class Meta:
#         model = User
#         fields = ('email', 'id', 'username', 'first_name',
#                   'last_name', 'is_subscribed', 'recipes', 'recipes_count')
#
#     def count_author_recipes(self, user):
#         return len(user.recipes.all())
#
#     def check_if_subscribed(self, user):
#         current_user = self.context.get('current_user')
#         other_user = user.following.all()
#         if user.is_anonymous:
#             return False
#         if other_user.count() == 0:
#             return False
#         return Subscribe.objects.filter(
#             user=user, author=current_user
#         ).exists()
#
#
# class ShowIngredientsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Ingredient
#         fields = ('id', 'amount', )
#
#
# class UserSerializer(serializers.ModelSerializer):
#
#     class Meta:
#         model = User
#         fields = ('email', 'id', 'username',
#                   'first_name', 'last_name', 'purchases')
#
#
# class UserSerializerModified(BaseUserSerializer):
#     is_subscribed = serializers.SerializerMethodField()
#
#     class Meta(BaseUserSerializer.Meta):
#         fields = ('email', 'id', 'username',
#                   'first_name', 'last_name', 'is_subscribed')
#
#     def get_is_subscribed(self, obj):
#         request = self.context.get('request')
#         if request is None or request.user.is_anonymous:
#             return False
#         return Subscribe.objects.filter(user=request.user, author=obj).exists()
#
#
# class ShowRecipeSerializer(serializers.ModelSerializer):
#     tags = TagSerializer(many=True, read_only=True)
#     author = UserSerializerModified(read_only=True)
#     ingredients = serializers.SerializerMethodField()
#     is_favorited = serializers.SerializerMethodField()
#     is_in_shopping_cart = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Recipe
#         fields = ('id', 'tags', 'author', 'ingredients',
#                   'is_favorited', 'is_in_shopping_cart',
#                   'name', 'image', 'text', 'cooking_time')
#
#     def get_ingredients(self, obj):
#         qs = IngredientRecipe.objects.filter(recipe=obj)
#         return IngredientCreateRecipeSerializer(qs, many=True).data
#
#     def get_is_favorited(self, obj):
#         request = self.context.get('request')
#         if request is None or request.user.is_anonymous:
#             return False
#         user = request.user
#         return Favorite.objects.filter(recipe=obj, user=user).exists()
#
#     def get_is_in_shopping_cart(self, obj):
#         request = self.context.get('request')
#         if request is None or request.user.is_anonymous:
#             return False
#         user = request.user
#         return Purchase.objects.filter(recipe=obj, user=user).exists()
#
#
# class AddIngredientToRecipeSerializer(serializers.ModelSerializer):
#     id = serializers.IntegerField()
#     amount = serializers.IntegerField()
#
#     class Meta:
#         model = Ingredient
#         fields = ('id', 'amount')
#
#
# class CreateRecipeSerializer(serializers.ModelSerializer):
#     tags = serializers.PrimaryKeyRelatedField(
#         many=True,
#         queryset=Tag.objects.all()
#     )
#     ingredients = IngredientCreateRecipeSerializer(many=True)
#
#     class Meta:
#         model = Recipe
#         fields = '__all__'
#
#     def create(self, validated_data):
#         ingredients = validated_data.pop('ingredients')
#         tags = validated_data.pop('tags')
#
#         for ingredient in ingredients:
#             if ingredient['amount'] <= 0:
#                 raise serializers.ValidationError(
#                     'Количество ингредиентов должно быть больше 0.'
#                 )
#         recipe = Recipe.objects.create(**validated_data)
#         recipe.save()
#         recipe.tags.set(tags)
#         for ingredient in ingredients:
#             IngredientRecipe.objects.create(
#                 recipe=recipe,
#                 ingredient=ingredient['id'],
#                 amount=ingredient['amount'],
#             )
#         return recipe
#
#     def update(self, instance, validated_data):
#         ingredients = validated_data.pop('ingredients')
#         for ingredient in ingredients:
#             if ingredient['amount'] <= 0:
#                 raise serializers.ValidationError(
#                     'Количество ингредиентов должно быть больше 0.'
#                 )
#         IngredientRecipe.objects.filter(recipe=instance).delete()
#         for new_ingredient in ingredients:
#             IngredientRecipe.objects.create(
#                 id=new_ingredient['id'],
#                 recipe=instance,
#                 amount=new_ingredient['amount']
#             )
#         instance.name = validated_data.pop('name')
#         instance.text = validated_data.pop('text')
#         if validated_data.get('image') is not None:
#             instance.image = validated_data.pop('image')
#         instance.cooking_time = validated_data.pop('cooking_time')
#         instance.save()
#         instance.tags.set('tags')
#         return instance
#
#     def to_representation(self, instance):
#         data = RecipeSerializer(
#             instance,
#             context={'request': self.context['request']}
#         ).data
#         return data
#
#
# class ListRecipeSerializer(serializers.ModelSerializer):
#     tag = TagSerializer()
#     author = UserSerializer(many=True)
#     ingredient = IngredientSerializer(many=True)
#
#     class Meta:
#         model = Recipe
#         fields = '__all__'
