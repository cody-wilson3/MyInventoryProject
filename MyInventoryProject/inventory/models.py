from django.db import models, transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.core.validators import MinValueValidator

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    quantity_on_hand = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    image = models.ImageField(upload_to="product_images/", blank=True, null=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    website_link = models.URLField(max_length=500, blank=True, null=True)
    group_parent = models.ForeignKey(
        "self",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="group_children",
        help_text="Optional: set this if this item belongs under another item on the main page."
    )

    def __str__(self):
        return f"{self.sku} — {self.name}"

    def clean(self):
        # Disallow self-parenting
        if self.group_parent_id and self.group_parent_id == self.id:
            raise ValidationError({"group_parent": "An item cannot be its own group parent."})
        # Optional: keep groups only one level deep
        if self.group_parent and self.group_parent.group_parent_id:
            raise ValidationError(
                {"group_parent": "Nested groups are not allowed. Choose a header that has no parent."})

    @property
    def needs_restock(self):
        return self.quantity_on_hand <= self.reorder_level

    @property
    def inventory_value(self):
        # convenience: qty * price
        return self.quantity_on_hand * (self.price or Decimal("0.00"))





class StockMovement(models.Model):
    IN, OUT = "IN", "OUT"
    MOVE_TYPES = [(IN, "Stock In"), (OUT, "Stock Out")]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    move_type = models.CharField(max_length=3, choices=MOVE_TYPES)
    quantity = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.quantity == 0:
            raise ValidationError("Quantity must be > 0.")
        if self.move_type == self.OUT and self.product and self.product.quantity_on_hand < self.quantity:
            raise ValidationError("Cannot move out more than quantity on hand.")

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                p = Product.objects.select_for_update().get(pk=self.product_id)
                if self.move_type == self.IN:
                    p.quantity_on_hand += self.quantity
                else:
                    p.quantity_on_hand -= self.quantity
                p.save()
