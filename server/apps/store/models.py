import uuid
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db.models import Sum
from apps.users.models import User


# Create your models here.
class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='books')
    number_of_pages = models.IntegerField()
    price_in_euros = models.DecimalField(max_digits=10, decimal_places=2)
    weight_in_kilograms = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return self.title
    
class MusicAlbum(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='music_albums')
    number_of_tracks = models.IntegerField()
    price_in_euros = models.DecimalField(max_digits=10, decimal_places=2)
    weight_in_kilograms = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"Music Album by {self.artist} ({self.number_of_tracks} tracks)"
    
class SoftwareLicense(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price_in_euros = models.DecimalField(max_digits=10, decimal_places=2)
    weight_in_kilograms = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return str(self.id)


class ShoppingCart(models.Model):
    """Represents a shopping cart that can contain multiple products."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shopping_carts', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Shopping Cart {self.id}"
    
    def add_product(self, product, quantity=1):
        """
        Add a product to the shopping cart.
        
        Args:
            product: Book, MusicAlbum, or SoftwareLicense instance
            quantity: Number of items to add (default: 1)
        
        Returns:
            ShoppingCartItem: The created or updated cart item
        """
        # Get the ContentType for the product
        content_type = ContentType.objects.get_for_model(product.__class__)
        
        # Try to get existing cart item for this product
        cart_item, created = ShoppingCartItem.objects.get_or_create(
            cart=self,
            content_type=content_type,
            object_id=product.id,
            defaults={
                'quantity': quantity,
                'product_price': product.price_in_euros,
                'product_weight': product.weight_in_kilograms
            }
        )
        
        # If item already exists, update quantity
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return cart_item
    
    def remove_product(self, product, quantity=1):
        """
        Remove a product from the shopping cart.
        
        Args:
            product: Book, MusicAlbum, or SoftwareLicense instance
            quantity: Number of items to remove (default: 1)
        
        Returns:
            bool: True if product was removed, False otherwise
        """
        content_type = ContentType.objects.get_for_model(product.__class__)
        
        try:
            cart_item = ShoppingCartItem.objects.get(
                cart=self,
                content_type=content_type,
                object_id=product.id
            )
            
            # If removing all or more, delete the item
            if cart_item.quantity <= quantity:
                cart_item.delete()
                return True
            else:
                # Reduce quantity
                cart_item.quantity -= quantity
                cart_item.save()
                return True
        except ShoppingCartItem.DoesNotExist:
            return False
    
    def calculate_total_price(self):
        """
        Calculate the total price of all items in the shopping cart.
        
        Returns:
            decimal.Decimal: Total price in euros
        """
        total = self.items.aggregate(
            total=Sum(models.F('quantity') * models.F('product_price'))
        )['total']
        return total or 0
    
    def calculate_total_weight(self):
        """
        Calculate the total weight of all items in the shopping cart.
        
        Returns:
            decimal.Decimal: Total weight in kilograms
        """
        total = self.items.aggregate(
            total=Sum(models.F('quantity') * models.F('product_weight'))
        )['total']
        return total or 0
    
    def get_total_price(self):
        """Alias for calculate_total_price for convenience."""
        return self.calculate_total_price()
    
    def get_total_weight(self):
        """Alias for calculate_total_weight for convenience."""
        return self.calculate_total_weight()


class ShoppingCartItem(models.Model):
    """Represents a single item in a shopping cart."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(ShoppingCart, on_delete=models.CASCADE, related_name='items')
    quantity = models.PositiveIntegerField(default=1)
    
    # Generic foreign key to support Book, MusicAlbum, and SoftwareLicense
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    product = GenericForeignKey('content_type', 'object_id')
    
    # Cached fields for price and weight to optimize calculations
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_weight = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['cart', 'content_type', 'object_id']
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.quantity}x {self.product} in cart {self.cart.id}"
    
    def save(self, *args, **kwargs):
        """Override save to update cached price and weight from the product."""
        if self.product:
            self.product_price = self.product.price_in_euros
            self.product_weight = self.product.weight_in_kilograms
        super().save(*args, **kwargs)
    
    def get_subtotal_price(self):
        """
        Calculate the subtotal price for this cart item.
        
        Returns:
            decimal.Decimal: Subtotal price (quantity * product_price)
        """
        return self.quantity * self.product_price
    
    def get_subtotal_weight(self):
        """
        Calculate the subtotal weight for this cart item.
        
        Returns:
            decimal.Decimal: Subtotal weight (quantity * product_weight)
        """
        return self.quantity * self.product_weight
