from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import ShoppingCart, ShoppingCartItem, Book, MusicAlbum, SoftwareLicense


class ProductSerializer(serializers.Serializer):
    """
    Generic serializer for products that handles Book, MusicAlbum, and SoftwareLicense.
    """
    def to_representation(self, instance):
        if isinstance(instance, Book):
            return {
                'id': str(instance.id),
                'type': 'book',
                'title': instance.title,
                'author': str(instance.author),
                'price_in_euros': str(instance.price_in_euros),
                'weight_in_kilograms': str(instance.weight_in_kilograms),
            }
        elif isinstance(instance, MusicAlbum):
            return {
                'id': str(instance.id),
                'type': 'music_album',
                'artist': str(instance.artist),
                'number_of_tracks': instance.number_of_tracks,
                'price_in_euros': str(instance.price_in_euros),
                'weight_in_kilograms': str(instance.weight_in_kilograms),
            }
        elif isinstance(instance, SoftwareLicense):
            return {
                'id': str(instance.id),
                'type': 'software_license',
                'price_in_euros': str(instance.price_in_euros),
                'weight_in_kilograms': str(instance.weight_in_kilograms),
            }
        return {}


class ShoppingCartItemSerializer(serializers.ModelSerializer):
    """Serializer for shopping cart items."""
    product = ProductSerializer(read_only=True)
    subtotal_price = serializers.SerializerMethodField()
    subtotal_weight = serializers.SerializerMethodField()
    product_type = serializers.SerializerMethodField()
    product_id = serializers.UUIDField(source='object_id', read_only=True)
    
    class Meta:
        model = ShoppingCartItem
        fields = [
            'id',
            'product_id',
            'product_type',
            'product',
            'quantity',
            'product_price',
            'product_weight',
            'subtotal_price',
            'subtotal_weight',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'product_price', 'product_weight', 'created_at', 'updated_at']
    
    def get_subtotal_price(self, obj):
        return str(obj.get_subtotal_price())
    
    def get_subtotal_weight(self, obj):
        return str(obj.get_subtotal_weight())
    
    def get_product_type(self, obj):
        return obj.content_type.model


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Serializer for shopping carts."""
    items = ShoppingCartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    total_weight = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ShoppingCart
        fields = [
            'id',
            'user',
            'items',
            'total_price',
            'total_weight',
            'item_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_price(self, obj):
        return str(obj.calculate_total_price())
    
    def get_total_weight(self, obj):
        return str(obj.calculate_total_weight())
    
    def get_item_count(self, obj):
        return obj.items.count()


class AddProductSerializer(serializers.Serializer):
    """Serializer for adding a product to the cart."""
    product_type = serializers.ChoiceField(
        choices=['book', 'musicalbum', 'softwarelicense'],
        required=True,
        help_text="Type of product: 'book', 'musicalbum', or 'softwarelicense'"
    )
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate(self, attrs):
        product_type = attrs['product_type'].lower()
        product_id = attrs['product_id']
        
        # Map product type to model
        model_map = {
            'book': Book,
            'musicalbum': MusicAlbum,
            'softwarelicense': SoftwareLicense,
        }
        
        if product_type not in model_map:
            raise serializers.ValidationError(
                f"Invalid product_type. Must be one of: {', '.join(model_map.keys())}"
            )
        
        # Get the model class
        model_class = model_map[product_type]
        
        # Check if product exists
        try:
            product = model_class.objects.get(id=product_id)
            attrs['product'] = product
        except model_class.DoesNotExist:
            raise serializers.ValidationError(
                f"{product_type} with id {product_id} does not exist."
            )
        
        return attrs


class RemoveProductSerializer(serializers.Serializer):
    """Serializer for removing a product from the cart."""
    product_type = serializers.ChoiceField(
        choices=['book', 'musicalbum', 'softwarelicense'],
        required=True
    )
    product_id = serializers.UUIDField(required=True)
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate(self, attrs):
        product_type = attrs['product_type'].lower()
        product_id = attrs['product_id']
        
        # Map product type to model
        model_map = {
            'book': Book,
            'musicalbum': MusicAlbum,
            'softwarelicense': SoftwareLicense,
        }
        
        if product_type not in model_map:
            raise serializers.ValidationError(
                f"Invalid product_type. Must be one of: {', '.join(model_map.keys())}"
            )
        
        # Get the model class
        model_class = model_map[product_type]
        
        # Check if product exists
        try:
            product = model_class.objects.get(id=product_id)
            attrs['product'] = product
        except model_class.DoesNotExist:
            raise serializers.ValidationError(
                f"{product_type} with id {product_id} does not exist."
            )
        
        return attrs

