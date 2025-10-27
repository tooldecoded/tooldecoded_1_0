from django.db import models
import uuid
from datetime import datetime

class Attributes(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    unit = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'Attributes'
        ordering = ['name']
        unique_together = ('name', 'unit')

class ItemCategories(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)
    level = models.IntegerField(blank=True, null=True)
    sortorder = models.IntegerField(blank=True, null=True)
    attributes = models.ManyToManyField('Attributes')
    class Meta:
        db_table = 'ItemCategories'
        ordering = ['level', 'sortorder', 'name']
        unique_together = ('parent', 'name', 'level')

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
    itemcategories = models.ManyToManyField('ItemCategories')
    batteryplatforms = models.ManyToManyField('BatteryPlatforms')
    batteryvoltages = models.ManyToManyField('BatteryVoltages')
    image = models.TextField(blank=True, null=True)
    bullets = models.TextField(blank=True, null=True)
    listingtype = models.ForeignKey('ListingTypes', on_delete=models.CASCADE, blank=True, null=True)
    status = models.ForeignKey('Statuses', on_delete=models.CASCADE, blank=True, null=True)
    releasedate = models.DateField(blank=True, null=True)
    discontinueddate = models.DateField(blank=True, null=True)
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
    itemcategories = models.ManyToManyField('ItemCategories')
    batteryplatforms = models.ManyToManyField('BatteryPlatforms')
    batteryvoltages = models.ManyToManyField('BatteryVoltages')
    productlines = models.ManyToManyField('ProductLines')
    image = models.TextField(blank=True, null=True)
    listingtype = models.ForeignKey('ListingTypes', on_delete=models.CASCADE, blank=True, null=True)
    fair_price_narrative = models.JSONField(blank=True, null=True)
    class Meta:
        db_table = 'Components'
        ordering = ['name']
        unique_together = ('brand', 'sku')

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
