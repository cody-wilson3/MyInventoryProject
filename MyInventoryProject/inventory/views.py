from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .forms import ProductForm, StockMovementForm
from .models import Product, Tag


def product_list(request):
    q = (request.GET.get("q") or "").strip()
    tag_name = (request.GET.get("tag") or "").strip()

    products = Product.objects.select_related("category").prefetch_related("tags")

    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(sku__icontains=q) |
            Q(category__name__icontains=q) |
            Q(tags__name__icontains=q)
        ).distinct()

    active_tag = None
    if tag_name:
        active_tag = Tag.objects.filter(name__iexact=tag_name).first()
        if active_tag:
            products = products.filter(tags=active_tag)

    all_tags = Tag.objects.order_by("name")

    return render(request, "inventory/product_list.html", {
        "products": products,
        "q": q,
        "all_tags": all_tags,
        "active_tag": active_tag,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    return render(request, "inventory/product_detail.html", {"product": product})


def product_create(request):
    if request.method == "POST":
        # If Discard was clicked, bail out before validating/saving
        if "discard" in request.POST:
            messages.info(request, "New product discarded.")
            return redirect(reverse("inventory:product_list"))

        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, "Product created.")
            return redirect(reverse("inventory:product_detail", args=[product.pk]))
    else:
        form = ProductForm()

    return render(request, "inventory/product_form.html", {"form": form, "title": "Create Product"})



def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Product updated.")
        return redirect(reverse("inventory:product_detail", args=[product.pk]))
    return render(request, "inventory/product_form.html", {"form": form, "title": "Edit Product"})


def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect(reverse("inventory:product_list"))
    return render(request, "inventory/product_confirm_delete.html", {"product": product})


def stock_movement_create(request):
    form = StockMovementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        movement = form.save(commit=False)
        try:
            movement.full_clean()
        except Exception as e:
            form.add_error(None, e)
        else:
            movement.save()
            messages.success(request, "Stock movement recorded.")
            return redirect(reverse("inventory:product_detail", args=[movement.product.pk]))
    return render(request, "inventory/stockmovement_form.html", {"form": form})
