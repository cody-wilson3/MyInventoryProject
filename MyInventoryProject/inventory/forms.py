from django import forms
from .models import Product, StockMovement, Tag


class ProductForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select existing tags below, or add new ones."
    )
    new_tags = forms.CharField(
        required=False,
        help_text="Add new tags (comma-separated), e.g. essential, non-essential"
    )

    class Meta:
        model = Product
        fields = [
            "sku", "name", "category", "quantity_on_hand",
            "reorder_level", "is_active", "tags", "image", "price", "website_link", "group_parent"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don’t allow selecting self as parent
        qs = Product.objects.all()
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        # Optional: only allow headers (items without a parent) to be selectable as parents
        self.fields["group_parent"].queryset = qs.filter(group_parent__isnull=True)
        self.fields["group_parent"].required = False
        self.fields["group_parent"].label = "Group parent"
        self.fields["group_parent"].help_text = "Leave blank if this is the header item."

    def save(self, commit=True):
        product = super().save(commit=commit)
        raw = (self.cleaned_data.get("new_tags") or "")
        new_names = [t.strip() for t in raw.split(",") if t.strip()]
        if new_names:
            created = [Tag.objects.get_or_create(name=name)[0] for name in new_names]
            product.tags.add(*created)
        return product


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["product", "move_type", "quantity", "note"]
