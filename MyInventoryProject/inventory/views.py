from django.db.models import Q
from collections import defaultdict

from .forms import StockMovementForm
from .models import Tag
from decimal import Decimal


def product_list(request):
    q = (request.GET.get("q") or "").strip()
    tag_name = (request.GET.get("tag") or "").strip()

    products = (
        Product.objects
        .select_related("category", "group_parent")
        .prefetch_related("tags", "group_children__tags", "group_children__category")
    )

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
            products = products.filter(Q(tags=active_tag) | Q(group_children__tags=active_tag)).distinct()

    # Build maps
    headers = [p for p in products if p.group_parent_id is None]
    children_map = defaultdict(list)
    for p in products:
        if p.group_parent_id:
            children_map[p.group_parent_id].append(p)

    # Split headers into those with children vs standalone (no children)
    headers_with_children = [h for h in headers if children_map.get(h.id)]
    standalone = [h for h in headers if not children_map.get(h.id)]

    standalone_total = sum((p.price or Decimal("0")) for p in standalone)
    group_totals = {
        header.id: sum((c.price or Decimal("0")) for c in children_map[header.id]) + (header.price or Decimal("0"))
        for header in headers_with_children
    }
    grand_total = standalone_total + sum(group_totals.values())

    # Sort nicely
    headers_with_children.sort(key=lambda p: (p.category.name if p.category_id else "", p.name.lower()))
    standalone.sort(key=lambda p: (p.category.name if p.category_id else "", p.name.lower()))
    for k in children_map:
        children_map[k].sort(key=lambda p: p.name.lower())

    all_tags = Tag.objects.order_by("name")

    return render(request, "inventory/product_list.html", {
        "headers_with_children": headers_with_children,
        "standalone": standalone,
        "children_map": children_map,
        "q": q,
        "all_tags": all_tags,
        "active_tag": active_tag,
        "standalone_total": standalone_total,
        "group_totals": group_totals,
        "grand_total": grand_total,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category"), pk=pk)
    return render(request, "inventory/product_detail.html", {"product": product})


from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from .forms import ProductForm
from .models import Product

def product_create(request):
    if request.method == "POST":
        # (you can remove this block if you no longer have a Discard button)
        if "discard" in request.POST:
            messages.info(request, "New product discarded.")
            return redirect(reverse("inventory:product_list"))

        form = ProductForm(request.POST, request.FILES)   # <-- pass files
        if form.is_valid():
            product = form.save()
            messages.success(request, "Product created.")
            return redirect(reverse("inventory:product_detail", args=[product.pk]))
    else:
        form = ProductForm()

    return render(request, "inventory/product_form.html", {"form": form, "title": "Create Product"})


def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)  # <-- pass files
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect(reverse("inventory:product_detail", args=[product.pk]))
    else:
        form = ProductForm(instance=product)

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
