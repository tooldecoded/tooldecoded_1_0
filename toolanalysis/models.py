from django.db import models
import uuid
from datetime import datetime

class Attributes(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    unit = models.TextField(blank=True, null=True)
    displayformat = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Attributes'
        ordering = ['sortorder', 'name']

class Features(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    description = models.TextField(blank=True, null=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Features'
        ordering = ['sortorder', 'name']

class ComponentFeatures(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    component = models.ForeignKey('Components', on_delete=models.CASCADE)
    feature = models.ForeignKey('Features', on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'ComponentFeatures'
        ordering = ['component', 'feature']
        unique_together = ('component', 'feature')

class Categories(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    fullname = models.TextField(unique=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Categories'
        ordering = ['sortorder', 'name']

class Subcategories(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    fullname = models.TextField(unique=True)
    categories = models.ManyToManyField('Categories')
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Subcategories'
        ordering = ['sortorder', 'name']

class ItemTypes(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    fullname = models.TextField(unique=True)
    categories = models.ManyToManyField('Categories')
    subcategories = models.ManyToManyField('Subcategories')
    sortorder = models.IntegerField(blank=True, null=True)
    attributes = models.ManyToManyField('Attributes')
    class Meta:
        db_table = 'ItemTypes'
        ordering = ['sortorder', 'name']

class MotorTypes(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'MotorTypes'
        ordering = ['sortorder', 'name']

class ListingTypes(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    retailer = models.ForeignKey('Retailers', on_delete=models.CASCADE, blank=True, null=True)
    class Meta:
        db_table = 'ListingTypes'
        ordering = ['name']

class Brands(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    color = models.TextField(blank=True, null=True)
    logo = models.TextField(blank=True, null=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Brands'
        ordering = ['sortorder']


class BatteryVoltages(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    value = models.IntegerField(unique=True)
    class Meta:
        db_table = 'BatteryVoltages'
        ordering = ['value']

class BatteryPlatforms(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    brand = models.ForeignKey('Brands', on_delete=models.CASCADE, blank=True, null=True)
    voltage = models.ManyToManyField('BatteryVoltages')
    class Meta:
        db_table = 'BatteryPlatforms'
        ordering = ['name']

class Retailers(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    url = models.TextField(blank=True, null=True)
    logo = models.TextField(blank=True, null=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Retailers'
        ordering = ['sortorder']
        
class Products(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey('Brands', on_delete=models.CASCADE, blank=True, null=True)
    sku = models.TextField(blank=True, null=True)
    itemtypes = models.ManyToManyField('ItemTypes')
    subcategories = models.ManyToManyField('Subcategories')
    categories = models.ManyToManyField('Categories')
    batteryplatforms = models.ManyToManyField('BatteryPlatforms')
    batteryvoltages = models.ManyToManyField('BatteryVoltages')
    image = models.TextField(blank=True, null=True)
    bullets = models.TextField(blank=True, null=True)
    listingtype = models.ForeignKey('ListingTypes', on_delete=models.CASCADE, blank=True, null=True)
    status = models.ForeignKey('Statuses', default='Active', on_delete=models.CASCADE, blank=True, null=True)
    releasedate = models.DateField(blank=True, null=True)
    discontinueddate = models.DateField(blank=True, null=True)
    motortype = models.ForeignKey('MotorTypes', on_delete=models.SET_NULL, blank=True, null=True)
    features = models.ManyToManyField('Features')
    isaccessory = models.BooleanField(default=False)
    class Meta:
        db_table = 'Products'
        ordering = ['name']
        unique_together = ('brand', 'sku')

class Components(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey('Brands', on_delete=models.CASCADE, blank=True, null=True)
    sku = models.TextField(blank=True, null=True)
    itemtypes = models.ManyToManyField('ItemTypes')
    subcategories = models.ManyToManyField('Subcategories')
    categories = models.ManyToManyField('Categories')
    batteryplatforms = models.ManyToManyField('BatteryPlatforms')
    batteryvoltages = models.ManyToManyField('BatteryVoltages')
    productlines = models.ManyToManyField('ProductLines')
    motortype = models.ForeignKey('MotorTypes', on_delete=models.SET_NULL, blank=True, null=True)
    image = models.TextField(blank=True, null=True)
    features = models.ManyToManyField('Features')
    listingtype = models.ForeignKey('ListingTypes', on_delete=models.CASCADE, blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    standalone_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    showcase_priority = models.IntegerField(default=0, help_text="Higher priority = appears first in browse page sections")
    fair_price_narrative = models.JSONField(blank=True, null=True)
    isaccessory = models.BooleanField(default=False)
    class Meta:
        db_table = 'Components'
        ordering = ['name']
        unique_together = ('brand', 'sku')
        verbose_name = "Component"
        verbose_name_plural = "Components"

class ProductComponents(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    product = models.ForeignKey('Products', on_delete=models.CASCADE, blank=True, null=True)
    component = models.ForeignKey('Components', on_delete=models.CASCADE, blank=True, null=True)
    quantity = models.IntegerField(default=1)
    class Meta:
        db_table = 'ProductComponents'
        ordering = ['product', 'component']
        unique_together = ('product', 'component')

class ComponentAttributes(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    component = models.ForeignKey('Components', on_delete=models.CASCADE)
    attribute = models.ForeignKey('Attributes', on_delete=models.CASCADE)
    value = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'ComponentAttributes'
        ordering = ['component', 'attribute']
        unique_together = ('component', 'attribute', 'value')

class ProductAccessories(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    product = models.ForeignKey('Products', on_delete=models.CASCADE, blank=True, null=True)
    name = models.TextField()
    quantity = models.IntegerField(default=1)
    class Meta:
        db_table = 'ProductAccessories'
        ordering = ['product', 'quantity', 'name']
        unique_together = ('product', 'name')

class ProductSpecifications(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    product = models.ForeignKey('Products', on_delete=models.CASCADE, blank=True, null=True)
    name = models.TextField()
    value = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'ProductSpecifications'
        ordering = ['product', 'name']
        unique_together = ('product', 'name')

class ProductImages(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    product = models.ForeignKey('Products', on_delete=models.CASCADE, blank=True, null=True)
    image = models.TextField()
    class Meta:
        db_table = 'ProductImages'
        ordering = ['product']
        unique_together = ('product', 'image')

class Statuses(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField(unique=True)
    color = models.TextField(blank=True, null=True)
    icon = models.TextField(blank=True, null=True)
    sortorder = models.IntegerField(blank=True, null=True)
    class Meta:
        db_table = 'Statuses'
        ordering = ['sortorder']

class ProductLines(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    description = models.TextField(blank=True, null=True)
    brand = models.ForeignKey('Brands', on_delete=models.CASCADE, blank=True, null=True)
    batteryplatform = models.ManyToManyField('BatteryPlatforms')
    batteryvoltage = models.ManyToManyField('BatteryVoltages')
    image = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'ProductLines'
        ordering = ['name']
        unique_together = ('name', 'brand')

class PriceListings(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    retailer = models.ForeignKey('Retailers', on_delete=models.CASCADE, blank=True, null=True)
    product = models.ForeignKey('Products', on_delete=models.CASCADE, blank=True, null=True)
    retailer_sku = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.TextField(default='USD')
    url = models.TextField(blank=True, null=True)
    datepulled = models.DateField(default=datetime.now)
    class Meta:
        db_table = 'PriceListings'
        ordering = ['retailer', 'product', 'datepulled']
        unique_together = ('retailer', 'product', 'retailer_sku', 'price', 'datepulled')

class ComponentPricingHistory(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    component = models.ForeignKey('Components', on_delete=models.CASCADE, related_name='pricing_history')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    source_type = models.CharField(max_length=20, choices=[
        ('standalone', 'Standalone Product'),
        ('prorated', 'Prorated from Bundle'),
        ('manual', 'Manual Override')
    ])
    source_product = models.ForeignKey('Products', on_delete=models.SET_NULL, null=True, blank=True)
    source_pricelisting = models.ForeignKey('PriceListings', on_delete=models.SET_NULL, null=True, blank=True)
    calculation_date = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(blank=True, null=True, help_text="Additional calculation details")
    
    class Meta:
        db_table = 'ComponentPricingHistory'
        ordering = ['-calculation_date']
        indexes = [
            models.Index(fields=['component', '-calculation_date']),
        ]
