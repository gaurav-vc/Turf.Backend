from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import BaseModel
from accounts.models import User

class Product(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='shop_products/', blank=True, null=True)
    in_stock = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ShopOrder(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shop_orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default='PENDING')
    delivery_address = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.id} ({self.user.email})"

class OrderItem(BaseModel):
    order = models.ForeignKey(ShopOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField(default=1)
    custom_name = models.CharField(max_length=100, blank=True)
    custom_number = models.CharField(max_length=10, blank=True)
    size = models.CharField(max_length=20, default='M')

class ProductReview(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_reviews')
    order = models.ForeignKey(ShopOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    verified_purchase = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('product', 'user')

    def __str__(self):
        return f"{self.user.email} - {self.product.name} ({self.rating}★)"

