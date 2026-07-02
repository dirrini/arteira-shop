from marshmallow import Schema, ValidationError, fields, validates_schema


class RegisterSchema(Schema):
    name = fields.Str(required=True, validate=lambda value: 2 <= len(value.strip()) <= 80)
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda value: 8 <= len(value) <= 128)


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=lambda value: 1 <= len(value) <= 128)


class SellerSchema(Schema):
    display_name = fields.Str(required=True, validate=lambda value: 2 <= len(value.strip()) <= 80)
    bio = fields.Str(load_default="", validate=lambda value: len(value) <= 1000)
    city = fields.Str(required=True, validate=lambda value: 2 <= len(value.strip()) <= 80)
    state = fields.Str(required=True, validate=lambda value: len(value.strip()) == 2)
    document = fields.Str(load_default="", validate=lambda value: len(value) <= 32)


class ProductSchema(Schema):
    title = fields.Str(required=True, validate=lambda value: 3 <= len(value.strip()) <= 120)
    description = fields.Str(required=True, validate=lambda value: 10 <= len(value.strip()) <= 3000)
    category = fields.Str(required=True, validate=lambda value: 2 <= len(value.strip()) <= 60)
    price_cents = fields.Int(required=True, strict=True)
    inventory = fields.Int(required=True, strict=True)
    images = fields.List(fields.Url(), load_default=list)
    materials = fields.List(fields.Str(), load_default=list)
    lead_time_days = fields.Int(load_default=3, strict=True)

    @validates_schema
    def validate_numbers(self, data, **kwargs):
        if data.get("price_cents", 0) < 100:
            raise ValidationError("Product price must be at least R$ 1,00", field_name="price_cents")
        if data.get("inventory", 0) < 0:
            raise ValidationError("Inventory cannot be negative", field_name="inventory")
        if data.get("lead_time_days", 0) < 0:
            raise ValidationError("Lead time cannot be negative", field_name="lead_time_days")


class CheckoutSchema(Schema):
    product_id = fields.Str(required=True)
    quantity = fields.Int(required=True, strict=True)

    @validates_schema
    def validate_quantity(self, data, **kwargs):
        if data.get("quantity", 0) <= 0:
            raise ValidationError("Quantity must be greater than zero", field_name="quantity")
