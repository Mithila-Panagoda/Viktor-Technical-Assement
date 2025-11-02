from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
from django import forms
from .models import Book, MusicAlbum, SoftwareLicense, ShoppingCart, ShoppingCartItem

# Register your models here.
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'author', 'price_in_euros', 'weight_in_kilograms']
    list_filter = ['author']
    search_fields = ['title']

@admin.register(MusicAlbum)
class MusicAlbumAdmin(admin.ModelAdmin):
    list_display = ['id', 'artist', 'number_of_tracks', 'price_in_euros', 'weight_in_kilograms']
    list_filter = ['artist']
    search_fields = ['artist__username']

@admin.register(SoftwareLicense)
class SoftwareLicenseAdmin(admin.ModelAdmin):
    list_display = ['id', 'price_in_euros', 'weight_in_kilograms']


class ShoppingCartItemInline(GenericTabularInline):
    """Inline admin for managing cart items directly from the cart."""
    model = ShoppingCartItem
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    extra = 1
    # GenericTabularInline automatically includes content_type and object_id, so we don't need to list them
    fields = ['content_type', 'object_id', 'quantity', 'get_product_info', 'product_price', 'product_weight', 'get_subtotal_price', 'get_subtotal_weight']
    readonly_fields = ['get_product_info', 'product_price', 'product_weight', 'get_subtotal_price', 'get_subtotal_weight']
    can_delete = False  # Disable deletion from inline
    verbose_name = "Cart Item"
    verbose_name_plural = "Cart Items"
    
    def has_add_permission(self, request, obj=None):
        """Allow adding new items."""
        return True
    
    def has_change_permission(self, request, obj=None):
        """Allow viewing existing items (read-only)."""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion of existing items from inline."""
        return False
    
    def get_formset(self, request, obj=None, **kwargs):
        """Override to ensure formset handles content_type properly."""
        from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
        
        formset_class = super().get_formset(request, obj, **kwargs)
        original_form_init = formset_class.form.__init__
        original_form_clean = formset_class.form.clean
        
        def form_init(self, *args, **kwargs):
            original_form_init(self, *args, **kwargs)
            # Check if this is an existing item (has instance with pk)
            is_existing_item = hasattr(self, 'instance') and self.instance and self.instance.pk
            
            # Ensure content_type and object_id fields exist and are configured
            if hasattr(self, 'fields'):
                # Make sure content_type exists - create it if needed
                if 'content_type' not in self.fields:
                    from django.contrib.contenttypes.models import ContentType as CT
                    from django.forms import ModelChoiceField
                    self.fields['content_type'] = ModelChoiceField(
                        queryset=CT.objects.none(),
                        required=False
                    )
                if 'content_type' in self.fields:
                    if is_existing_item:
                        # Make read-only for existing items
                        self.fields['content_type'].widget.attrs['readonly'] = True
                        self.fields['content_type'].widget.attrs['disabled'] = True
                    else:
                        # Allow selection for new items
                        allowed_content_types = ContentType.objects.filter(
                            model__in=['book', 'musicalbum', 'softwarelicense']
                        )
                        self.fields['content_type'].queryset = allowed_content_types
                        self.fields['content_type'].empty_label = "Select product type..."
                
                # Make sure object_id exists - create it if needed
                if 'object_id' not in self.fields:
                    from django.forms import UUIDField
                    self.fields['object_id'] = UUIDField(required=False)
                
                if 'object_id' in self.fields:
                    if is_existing_item:
                        # Make read-only for existing items
                        self.fields['object_id'].widget.attrs['readonly'] = True
                        self.fields['object_id'].widget.attrs['disabled'] = True
                    else:
                        self.fields['object_id'].help_text = "Enter the UUID of the product"
                
                if 'quantity' in self.fields:
                    if is_existing_item:
                        # Make read-only for existing items
                        self.fields['quantity'].widget.attrs['readonly'] = True
                        self.fields['quantity'].widget.attrs['disabled'] = True
                    else:
                        self.fields['quantity'].help_text = "Number of items to add"
        
        def form_clean(self):
            """Auto-set price and weight from product."""
            # For disabled fields (read-only existing items), we need to handle them specially
            is_existing_item = hasattr(self, 'instance') and self.instance and self.instance.pk
            
            cleaned_data = original_form_clean(self)
            
            # For disabled fields, restore values from instance if not in cleaned_data
            if hasattr(self, 'instance') and self.instance and self.instance.pk:
                if 'content_type' in self.fields and self.fields['content_type'].widget.attrs.get('disabled'):
                    if not cleaned_data.get('content_type'):
                        cleaned_data['content_type'] = self.instance.content_type
                if 'object_id' in self.fields and self.fields['object_id'].widget.attrs.get('disabled'):
                    if not cleaned_data.get('object_id'):
                        cleaned_data['object_id'] = self.instance.object_id
                if 'quantity' in self.fields and self.fields['quantity'].widget.attrs.get('disabled'):
                    if not cleaned_data.get('quantity'):
                        cleaned_data['quantity'] = self.instance.quantity
            
            content_type = cleaned_data.get('content_type')
            object_id = cleaned_data.get('object_id')
            
            # Only auto-set price/weight for new items
            if content_type and object_id:
                is_new_item = not (hasattr(self, 'instance') and self.instance and self.instance.pk)
                if is_new_item:
                    # New item - set price and weight from product
                    model_class = content_type.model_class()
                    if model_class:
                        try:
                            product = model_class.objects.get(id=object_id)
                            cleaned_data['product_price'] = product.price_in_euros
                            cleaned_data['product_weight'] = product.weight_in_kilograms
                        except model_class.DoesNotExist:
                            raise forms.ValidationError(
                                f"{content_type.model} with id {object_id} does not exist."
                            )
            
            return cleaned_data
        
        # Create a custom formset class that ensures empty_form is configured
        class CustomFormSet(formset_class):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # Configure empty_form after it's created
                if hasattr(self, 'empty_form') and hasattr(self.empty_form, 'fields'):
                    # Ensure content_type exists
                    if 'content_type' not in self.empty_form.fields:
                        from django.contrib.contenttypes.models import ContentType as CT
                        from django.forms import ModelChoiceField
                        self.empty_form.fields['content_type'] = ModelChoiceField(
                            queryset=CT.objects.none(),
                            required=False
                        )
                    
                    if 'content_type' in self.empty_form.fields:
                        allowed_content_types = ContentType.objects.filter(
                            model__in=['book', 'musicalbum', 'softwarelicense']
                        )
                        self.empty_form.fields['content_type'].queryset = allowed_content_types
                        self.empty_form.fields['content_type'].empty_label = "Select product type..."
                    
                    # Ensure object_id exists
                    if 'object_id' not in self.empty_form.fields:
                        from django.forms import UUIDField
                        self.empty_form.fields['object_id'] = UUIDField(required=False)
                    
                    if 'object_id' in self.empty_form.fields:
                        self.empty_form.fields['object_id'].help_text = "Enter the UUID of the product"
                    if 'quantity' in self.empty_form.fields:
                        self.empty_form.fields['quantity'].help_text = "Number of items to add"
        
        # Apply custom methods to the form class
        CustomFormSet.form.__init__ = form_init
        CustomFormSet.form.clean = form_clean
        
        return CustomFormSet
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Filter content types to only show Book, MusicAlbum, and SoftwareLicense."""
        if db_field.name == 'content_type':
            kwargs['queryset'] = ContentType.objects.filter(
                model__in=['book', 'musicalbum', 'softwarelicense']
            )
            kwargs['empty_label'] = "Select product type..."
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    def get_product_info(self, obj):
        """Display product information if item is saved."""
        if obj.pk and obj.product:
            if isinstance(obj.product, Book):
                return f"Book: {obj.product.title}"
            elif isinstance(obj.product, MusicAlbum):
                return f"Album: {obj.product.artist}"
            elif isinstance(obj.product, SoftwareLicense):
                return f"License: {obj.product.id}"
        return "Select product type and enter product ID"
    get_product_info.short_description = 'Product'
    
    def get_subtotal_price(self, obj):
        if obj and obj.pk:
            try:
                subtotal = obj.get_subtotal_price()
                return f"€{float(subtotal):.2f}"
            except (TypeError, ValueError, AttributeError):
                return "-"
        return "-"
    get_subtotal_price.short_description = 'Subtotal Price'
    
    def get_subtotal_weight(self, obj):
        if obj and obj.pk:
            try:
                subtotal = obj.get_subtotal_weight()
                return f"{float(subtotal):.2f} kg"
            except (TypeError, ValueError, AttributeError):
                return "-"
        return "-"
    get_subtotal_weight.short_description = 'Subtotal Weight'


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'created_at', 'get_item_count', 'get_total_price', 'get_total_weight']
    list_filter = ['created_at', 'user']
    readonly_fields = ['id', 'created_at', 'updated_at', 'get_total_price_display', 'get_total_weight_display', 'get_item_count_display']
    inlines = [ShoppingCartItemInline]
    fieldsets = (
        ('Cart Information', {
            'fields': ('id', 'user', 'created_at', 'updated_at')
        }),
        ('Cart Summary', {
            'fields': ('get_total_price_display', 'get_total_weight_display', 'get_item_count_display'),
            'classes': ('collapse',)
        }),
    )
    
    def get_total_price(self, obj):
        if obj.pk:
            return f"€{obj.calculate_total_price():.2f}"
        return "-"
    get_total_price.short_description = 'Total Price'
    
    def get_total_weight(self, obj):
        if obj.pk:
            return f"{obj.calculate_total_weight():.2f} kg"
        return "-"
    get_total_weight.short_description = 'Total Weight'
    
    def get_item_count(self, obj):
        if obj.pk:
            return obj.items.count()
        return 0
    get_item_count.short_description = 'Items'
    
    # Display fields for detail view
    def get_total_price_display(self, obj):
        if obj.pk:
            return f"€{obj.calculate_total_price():.2f}"
        return "€0.00"
    get_total_price_display.short_description = 'Total Price'
    
    def get_total_weight_display(self, obj):
        if obj.pk:
            return f"{obj.calculate_total_weight():.2f} kg"
        return "0.00 kg"
    get_total_weight_display.short_description = 'Total Weight'
    
    def get_item_count_display(self, obj):
        if obj.pk:
            return obj.items.count()
        return 0
    get_item_count_display.short_description = 'Item Count'


@admin.register(ShoppingCartItem)
class ShoppingCartItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'cart', 'get_product_type', 'get_product_name', 'quantity', 'get_subtotal_price', 'get_subtotal_weight']
    list_filter = ['cart', 'created_at', 'content_type']
    readonly_fields = ['id', 'created_at', 'updated_at', 'product_price', 'product_weight', 'get_subtotal_price', 'get_subtotal_weight']
    search_fields = ['cart__id', 'object_id']
    
    fieldsets = (
        ('Cart Item Information', {
            'fields': ('cart', 'content_type', 'object_id', 'quantity')
        }),
        ('Product Details', {
            'fields': ('product_price', 'product_weight', 'created_at', 'updated_at')
        }),
        ('Calculations', {
            'fields': ('get_subtotal_price', 'get_subtotal_weight'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Filter to only show items with allowed content types
        allowed_content_types = ContentType.objects.filter(
            model__in=['book', 'musicalbum', 'softwarelicense']
        )
        return qs.filter(content_type__in=allowed_content_types)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'content_type':
            # Filter content types to only show Book, MusicAlbum, and SoftwareLicense
            kwargs['queryset'] = ContentType.objects.filter(
                model__in=['book', 'musicalbum', 'softwarelicense']
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def get_product_type(self, obj):
        return obj.content_type.model if obj.content_type else "-"
    get_product_type.short_description = 'Product Type'
    get_product_type.admin_order_field = 'content_type__model'
    
    def get_product_name(self, obj):
        if obj.product:
            if isinstance(obj.product, Book):
                return obj.product.title
            elif isinstance(obj.product, MusicAlbum):
                return f"Album by {obj.product.artist}"
            elif isinstance(obj.product, SoftwareLicense):
                return str(obj.product.id)
        return "-"
    get_product_name.short_description = 'Product'
    
    def get_subtotal_price(self, obj):
        if obj and obj.pk:
            try:
                subtotal = obj.get_subtotal_price()
                return f"€{float(subtotal):.2f}"
            except (TypeError, ValueError, AttributeError):
                return "-"
        return "-"
    get_subtotal_price.short_description = 'Subtotal Price'
    
    def get_subtotal_weight(self, obj):
        if obj and obj.pk:
            try:
                subtotal = obj.get_subtotal_weight()
                return f"{float(subtotal):.2f} kg"
            except (TypeError, ValueError, AttributeError):
                return "-"
        return "-"
    get_subtotal_weight.short_description = 'Subtotal Weight'
