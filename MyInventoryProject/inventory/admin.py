from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category, Product, StockMovement, Tag

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")
    search_fields = ("name",)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "quantity_on_hand", "reorder_level", "price", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("sku", "name")

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "move_type", "quantity", "created_at", "note")
    list_filter = ("move_type", "created_at")
    search_fields = ("product__sku", "product__name", "note")

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)



