from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from product_management.services import (
    BundleComponentItem,
    create_bare_tool,
    create_bundle_from_products,
    extract_component_from_product,
    undo_last_change,
)
from toolanalysis.models import (
    Brands,
    Components,
    ListingTypes,
    ProductComponents,
    Products,
)


class ProductManagementServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand = Brands.objects.create(name="Tooldecoded")
        cls.listing_type = ListingTypes.objects.create(name="Direct")
        cls.superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )

    def _component_payload(self):
        return {
            "name": "Bare Component",
            "sku": "COMP-001",
            "brand": self.brand,
            "description": "Test component",
            "listingtype": self.listing_type,
            "motortype": None,
            "itemtypes": [],
            "subcategories": [],
            "categories": [],
            "batteryplatforms": [],
            "batteryvoltages": [],
            "productlines": [],
            "features": [],
            "image": "",
            "is_featured": False,
            "standalone_price": None,
            "showcase_priority": 0,
            "fair_price_narrative": None,
            "isaccessory": False,
        }

    def _product_payload(self, name="Bare Product", sku="PROD-001"):
        return {
            "name": name,
            "sku": sku,
            "brand": self.brand,
            "description": "Test product",
            "listingtype": self.listing_type,
            "motortype": None,
            "status": None,
            "image": "",
            "bullets": "",
            "isaccessory": False,
        }

    def test_create_bare_tool_creates_component_and_product(self):
        component_data = self._component_payload()
        product_data = self._product_payload()

        component, product = create_bare_tool(
            component_data=component_data,
            product_data=product_data,
            user=self.superuser,
        )

        self.assertIsInstance(component, Components)
        self.assertIsInstance(product, Products)
        self.assertTrue(
            ProductComponents.objects.filter(product=product, component=component).exists()
        )

    def test_create_bundle_from_products_links_components(self):
        component_data = self._component_payload()
        component_data["sku"] = "COMP-XYZ"
        component, _ = create_bare_tool(component_data=component_data, user=self.superuser)

        bundle_data = self._product_payload(name="Bundle", sku="BUNDLE-001")
        product = create_bundle_from_products(
            bundle_data=bundle_data,
            component_items=[BundleComponentItem(component=component, quantity=2)],
            user=self.superuser,
        )

        link = ProductComponents.objects.get(product=product, component=component)
        self.assertEqual(link.quantity, 2)

    def test_extract_component_from_product_copies_core_fields(self):
        product = Products.objects.create(**self._product_payload())
        component = extract_component_from_product(product, user=self.superuser)

        self.assertEqual(component.name, product.name)
        self.assertEqual(component.brand, product.brand)
        self.assertEqual(component.sku, product.sku)

    def test_undo_last_change_removes_new_component(self):
        component_data = self._component_payload()
        component, _ = create_bare_tool(component_data=component_data, user=self.superuser)

        undo_last_change("component", component.id, user=self.superuser)

        self.assertFalse(Components.objects.filter(id=component.id).exists())


class ProductManagementViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.brand = Brands.objects.create(name="Tooldecoded")
        cls.listing_type = ListingTypes.objects.create(name="Direct")
        cls.superuser = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
        )
        cls.user = get_user_model().objects.create_user(
            username="user",
            email="user@example.com",
            password="password",
        )

    def test_dashboard_requires_superuser(self):
        client = Client()
        client.force_login(self.user)
        response = client.get(reverse("product_management:dashboard"))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_loads_for_superuser(self):
        client = Client()
        client.force_login(self.superuser)
        response = client.get(reverse("product_management:dashboard"))
        self.assertEqual(response.status_code, 200)

# Create your tests here.
