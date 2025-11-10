from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem , Notification
from .serializers import *
from groceryproducts.models import *
from foodproduct.models import *
from fashion.models import *
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from django.conf import settings
import razorpay
from vendors.authentication import VendorJWTAuthentication
from users.models import Coupon
from django.db.models.functions import TruncMonth
from django.db.models import Count, Sum,F
from datetime import datetime
from rest_framework import generics, status
from rest_framework.response import Response
from datetime import timedelta
from django.utils.dateparse import parse_date
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from django_filters import rest_framework as filters
from django.db.models import Q
from deliverypartner.models import DeliveryNotification
from coupon_tracking.models import UserCouponUsage
from django.db import transaction
import random
from geopy.distance import geodesic
from decimal import Decimal
from deliverypartner.models import DeliveryCharges
from django.utils import timezone
from deliverypartner.models import OrderAssign
from .utils import send_order_placed_notification, send_new_order_notification

import logging

logger = logging.getLogger(__name__)


class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        cart_items = CartItem.objects.filter(cart__user=request.user)
        serializer = CartItemSerializer(cart_items, many=True, context={'request': request})
        total_cart_amount = sum(item['total_amount'] for item in serializer.data)

        response_data = {
            "count": len(serializer.data),
            "results": serializer.data,
            "total_cart_amount": total_cart_amount
        }

        return Response(response_data)


#add to cart


# class AddToCartView(generics.CreateAPIView):
#     def create(self, request, *args, **kwargs):
#         data = request.data

#         product_type = data.get("product_type")
#         product_id = data.get("product_id")
#         vendor = data.get("vendor")
#         quantity = int(data.get("quantity", 1))
#         variant = data.get("variant")  # Used for grocery (weight) and dish (size)
#         color = data.get("color")  # Used for clothing
#         size = data.get("size")  # Used for clothing

#         # Map product_type to models
#         product_model = {
#             "clothing": Clothing,
#             "dish": Dish,
#             "grocery": GroceryProducts
#         }.get(product_type)

#         if not product_model:
#             return Response({"error": "Invalid product type"}, status=status.HTTP_400_BAD_REQUEST)

#         product = product_model.objects.filter(id=product_id).first()
#         if not product:
#             return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

#         # Handle product-specific variant selection
#         if product_type == "clothing":
#             if not color or not size:
#                 return Response({"error": "Color and size are required for clothing"}, status=status.HTTP_400_BAD_REQUEST)

#             selected_color = next((c for c in product.colors if c["color_name"] == color), None)
#             if not selected_color:
#                 return Response({"error": f"Color '{color}' not available"}, status=status.HTTP_400_BAD_REQUEST)

#             selected_size = next((s for s in selected_color["sizes"] if s["size"] == size), None)
#             if not selected_size:
#                 return Response({"error": f"Size '{size}' not available in color '{color}'"}, status=status.HTTP_400_BAD_REQUEST)

#             if selected_size["stock"] < quantity:
#                 return Response({"error": "Insufficient stock"}, status=status.HTTP_400_BAD_REQUEST)

#             price = selected_size["price"]
#             variant = f"{color} - {size}"

#         elif product_type == "grocery" and variant:
#             price = product.get_price_for_variant(variant)
#         elif product_type == "dish" and variant:
#             price = product.get_price_for_variant(variant)
#         else:
#             price = product.offer_price if product.offer_price else product.price

#         # Get or create cart
#         cart, created = Cart.objects.get_or_create(user=request.user)

#         # ** Restrict grocery and dish items from different vendors **
#         if product_type in ["grocery", "dish"]:
#             existing_items = CartItem.objects.filter(cart=cart)
#             if existing_items.exists():
#                 existing_vendor = existing_items.first().vendor_id
#                 if existing_vendor != vendor:
#                     return Response({"error": "You can only add grocery or food items from a single vendor at a time."}, status=status.HTTP_400_BAD_REQUEST)

#         # Check if the product is already in the cart
#         cart_item = CartItem.objects.filter(
#             cart=cart,
#             vendor_id=vendor,
#             product_type=product_type,
#             product_id=product_id,
#             variant=variant
#         ).first()

#         if cart_item:
#             cart_item.quantity += quantity
#             cart_item.save()
#             message = "Product quantity updated in cart"
#         else:
#             cart_item = CartItem.objects.create(
#                 cart=cart,
#                 vendor_id=vendor,
#                 product_type=product_type,
#                 product_id=product_id,
#                 quantity=quantity,
#                 variant=variant,  # Color and size stored as variant
#                 price=price
#             )
#             message = "Product added to cart"

#         return Response(
#             {
#                 "message": message,
#                 "cart_item": {
#                     "id": cart_item.id,
#                     "quantity": cart_item.quantity,
#                     "variant": variant
#                 }
#             },
#             status=status.HTTP_201_CREATED
#         )

from django.shortcuts import get_object_or_404

class AddToCartView(generics.CreateAPIView):
    """
    API view to add items to the shopping cart.
    Supports multiple product types: Fashion, Restaurant, and Grocery.
    """

    def create(self, request, *args, **kwargs):
        data = request.data

        # Extract and validate input data
        product_type = data.get("product_type")
        product_id = data.get("product_id")
        vendor_id = data.get("vendor")
        quantity = data.get("quantity", 1)
        variant = data.get("variant")
        color = data.get("color")
        size = data.get("size")

        # Validate required fields
        if not product_type or not product_id or not vendor_id:
            return Response(
                {"error": "product_type, product_id, and vendor are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate and convert quantity
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response(
                {"error": "Quantity must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Product model mapping
        model_map = {
            "Fashion": Clothing,
            "Restaurant": Dish,  # Fixed typo: "Restaurent" -> "Restaurant"
            "Grocery": GroceryProducts
        }

        product_model = model_map.get(product_type)
        if not product_model:
            return Response(
                {"error": f"Invalid product type. Must be one of: {', '.join(model_map.keys())}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get product instance
        product = get_object_or_404(product_model, id=product_id)

        # Process based on product type
        if product_type == "Fashion":
            result = self._handle_clothing(product, color, size, quantity)
        elif product_type == "Restaurant":
            result = self._handle_dish(product, variant)
        elif product_type == "Grocery":
            result = self._handle_grocery(product, variant, quantity)
        else:
            result = {"error": "Unsupported product type."}

        # Check for errors in processing
        if "error" in result:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        price = result["price"]
        variant = result["variant"]

        # Get or create cart
        cart, _ = Cart.objects.get_or_create(user=request.user)

        # Check if the item is already in cart
        cart_item = CartItem.objects.filter(
            cart=cart,
            product_type=product_type,
            product_id=product_id,
            vendor_id=vendor_id,
            variant=variant
        ).first()

        if cart_item:
            # Update existing cart item
            cart_item.quantity += quantity
            cart_item.price = price  # Update price in case it changed
            cart_item.save()
            message = "Cart item updated successfully."
        else:
            # Create new cart item
            cart_item = CartItem.objects.create(
                cart=cart,
                vendor_id=vendor_id,
                product_type=product_type,
                product_id=product_id,
                quantity=quantity,
                variant=variant,
                price=price
            )
            message = "Item added to cart successfully."

        return Response({
            "message": message,
            "cart_item": {
                "id": cart_item.id,
                "product_type": product_type,
                "product_id": product_id,
                "variant": variant,
                "quantity": cart_item.quantity,
                "price": float(price),
                "total_price": float(Decimal(str(cart_item.quantity)) * Decimal(str(price)))
            }
        }, status=status.HTTP_201_CREATED)

    def _handle_clothing(self, product, color, size, quantity):
        """Handle clothing product logic."""
        if not color or not size:
            return {"error": "Color and size are required for clothing items."}

        # Get color
        try:
            selected_color = ClothingColor.objects.get(
                clothing=product,
                color_name__iexact=color
            )
        except ClothingColor.DoesNotExist:
            return {"error": f"Color '{color}' is not available for this item."}

        # Get size
        try:
            selected_size = ClothingSize.objects.get(
                color=selected_color,
                size__iexact=size
            )
        except ClothingSize.DoesNotExist:
            return {"error": f"Size '{size}' is not available for color '{color}'."}

        # Check stock availability
        if selected_size.stock < quantity:
            return {
                "error": f"Insufficient stock. Only {selected_size.stock} units available."
            }

        # Get price
        price = float(selected_size.offer_price or selected_size.price)
        variant = f"{color} - {size}"

        return {"price": price, "variant": variant}

    def _handle_dish(self, product, variant):
        """Handle restaurant dish logic."""
        if not variant:
            return {"error": "Dish variant is required."}

        price = product.get_price_for_variant(variant)

        try:
            price = float(price)
        except (ValueError, TypeError):
            return {
                "error": f"Invalid price configuration for variant '{variant}'."
            }

        return {"price": price, "variant": variant}

    def _handle_grocery(self, product, variant, quantity):
        """Handle grocery product logic with stock management."""
        if not variant:
            return {"error": "Grocery variant is required."}

        price = product.get_price_for_weight(variant)

        try:
            price = float(price)
        except (ValueError, TypeError):
            return {
                "error": f"Invalid price configuration for variant '{variant}'."
            }

        # Handle stock deduction for grocery items
        stock_updated = False

        if isinstance(product.weights, list):
            for weight_data in product.weights:
                if weight_data.get("weight") == variant:
                    available_qty = weight_data.get("quantity", 0)
                    if available_qty < quantity:
                        return {
                            "error": f"Insufficient stock. Only {available_qty} units available for '{variant}'."
                        }
                    weight_data["quantity"] = available_qty - quantity
                    stock_updated = True
                    break

        elif isinstance(product.weights, dict):
            if variant in product.weights:
                available_qty = product.weights[variant].get("quantity", 0)
                if available_qty < quantity:
                    return {
                        "error": f"Insufficient stock. Only {available_qty} units available for '{variant}'."
                    }
                product.weights[variant]["quantity"] = available_qty - quantity
                stock_updated = True

        if not stock_updated:
            return {"error": f"Variant '{variant}' not found in product inventory."}

        # Save the updated stock
        product.save()

        return {"price": price, "variant": variant}



class RemoveFromCartView(generics.GenericAPIView):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        cart_item_id = kwargs.get("pk")
        quantity_to_set = int(request.data.get("quantity", 1))

        cart_item = CartItem.objects.filter(id=cart_item_id, cart__user=request.user).first()

        if not cart_item:
            return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

        if quantity_to_set > cart_item.quantity:
            cart_item.quantity = quantity_to_set
            message = "Item quantity updated"
        elif quantity_to_set < cart_item.quantity:
            cart_item.quantity -= (cart_item.quantity - quantity_to_set)
            message = "Item quantity updated"
        else:
            return Response({"message": "No change in quantity"}, status=status.HTTP_200_OK)

        cart_item.save()

        return Response(
            {"message": message, "cart_item": {"id": cart_item_id, "quantity": cart_item.quantity}},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, *args, **kwargs):
        cart_item_id = kwargs.get("pk")
        cart_item = CartItem.objects.filter(id=cart_item_id, cart__user=request.user).first()

        if cart_item:
            cart_item.delete()
            return Response({"message": "Item removed from cart"}, status=status.HTTP_200_OK)

        return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)


class GroceryCartView(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        cart, created = Cart.objects.get_or_create(user=user)
        cart_items = CartItem.objects.filter(cart=cart, product_type="grocery")

        grocery_items = []
        total_amount = 0

        for item in cart_items:
            product = GroceryProducts.objects.filter(id=item.product_id).first()
            if product:
                item_total = item.price * item.quantity
                total_amount += item_total

                grocery_items.append({
                    "id": item.product_id,
                    "vendor_id": item.vendor_id,
                    "name": product.name,
                    "price": item.price,
                    "quantity": item.quantity,
                    "variant": item.variant,
                    "images": [
                        request.build_absolute_uri(img.image.url) for img in product.images.all()
                    ],
                    "item_total": item_total
                })

        return Response({
            "grocery_products": grocery_items,
            "total_amount": total_amount
        })


class DishCartView(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        cart, created = Cart.objects.get_or_create(user=user)
        cart_items = CartItem.objects.filter(cart=cart, product_type="dish")

        dish_items = []
        total_amount = 0

        for item in cart_items:
            product = Dish.objects.filter(id=item.product_id).first()
            if product:
                item_total = item.price * item.quantity
                total_amount += item_total

                dish_items.append({
                    "id": item.product_id,
                    "vendor_id": item.vendor_id,
                    "name": product.name,
                    "price": item.price,
                    "quantity": item.quantity,
                    "variant": item.variant,
                    "images": [
                        request.build_absolute_uri(img.image.url) for img in product.images.all()
                    ],
                    "item_total": item_total
                })

        return Response({
            "dishes": dish_items,
            "total_amount": total_amount
        })


class ClothingCartView(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        user = request.user
        cart, created = Cart.objects.get_or_create(user=user)
        cart_items = CartItem.objects.filter(cart=cart, product_type="clothing")

        clothing_items = []
        total_amount = 0

        for item in cart_items:
            product = Clothing.objects.filter(id=item.product_id).first()
            if product:
                item_total = item.price * item.quantity
                total_amount += item_total

                clothing_items.append({
                    "id": item.product_id,
                    "vendor_id": item.vendor_id,
                    "name": product.name,
                    "price": item.price,
                    "quantity": item.quantity,
                    "variant": item.variant,
                    "images": [
                        request.build_absolute_uri(img.image.url) for img in product.images.all()
                    ],
                    "item_total": item_total
                })

        return Response({
            "clothing": clothing_items,
            "total_amount": total_amount
        })


class CheckoutView(generics.CreateAPIView):

    queryset = Checkout.objects.all()
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        user = request.user
        logger.info(f"Checkout initiated by user: {user.id}")

        # Validate incoming data
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Fetch user's cart and items
        try:
            cart = Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return Response(
                {"error": "Cart not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        cart_items = CartItem.objects.filter(cart=cart).select_related('vendor')

        if not cart_items.exists():
            return Response(
                {"error": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Calculate total amount
        total_amount = Decimal('0.00')
        for item in cart_items:
            total_amount += Decimal(str(item.price)) * item.quantity

        logger.info(f"Initial total amount: {total_amount}")

        # Handle coupon code (if provided)
        coupon_code = request.data.get('coupon_code')
        discount_amount = Decimal('0.00')
        
        if coupon_code:
            coupon_result = self._apply_coupon(coupon_code, total_amount)
            if 'error' in coupon_result:
                return Response(
                    {"error": coupon_result['error']},
                    status=status.HTTP_400_BAD_REQUEST
                )
            discount_amount = coupon_result['discount_amount']
            logger.info(f"Coupon applied. Discount: {discount_amount}")

        final_amount = total_amount - discount_amount
        logger.info(f"Final amount after discount: {final_amount}")

        # Use database transaction to ensure data consistency
        try:
            with transaction.atomic():
                # Create checkout instance
                payment_method = validated_data.get('payment_method')
                checkout = Checkout.objects.create(
                    user=user,
                    order_id=str(uuid.uuid4()),
                    total_amount=total_amount,
                    discount_amount=discount_amount,
                    final_amount=final_amount,
                    payment_method=payment_method,
                    shipping_address=validated_data.get('shipping_address'),
                    contact_number=validated_data.get('contact_number', ''),
                    coupon_code=coupon_code,
                    coupon_discount=discount_amount,
                    payment_status='pending' if payment_method == 'online' else 'paid',
                    order_status='pending'
                )

                # Process each cart item
                for item in cart_items:
                    # Create CheckoutItem
                    CheckoutItem.objects.create(
                        checkout=checkout,
                        vendor=item.vendor,
                        product_type=item.product_type,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        color=item.color,
                        size=item.size,
                        variant=item.variant,
                        price=item.price,
                        subtotal=Decimal(str(item.price)) * item.quantity,
                    )

                    # Deduct stock based on product type
                    stock_result = self._deduct_stock(
                        item.product_type,
                        item.product_id,
                        item.quantity,
                        item.variant,
                        item.color,
                        item.size
                    )

                    if not stock_result['success']:
                        # Rollback transaction if stock deduction fails
                        raise Exception(stock_result['error'])

                # Note: If you have a separate Order model, create it here
                # For now, Checkout model serves as the order

                logger.info(f"Checkout created successfully: {checkout.order_id}")

                # Clear cart after successful checkout
                cart_items.delete()
                logger.info(f"Cart cleared for user: {user.id}")

        except Exception as e:
            logger.error(f"Checkout failed: {str(e)}")
            return Response(
                {"error": f"Checkout failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Handle online payment
        if payment_method == 'online':
            payment_response = self._create_razorpay_order(checkout, final_amount)
            if 'error' in payment_response:
                return Response(
                    payment_response,
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            # *** FIXED: Add complete order details including discounted final_amount ***
            payment_response.update({
                "order_id": checkout.order_id,
                "total_amount": float(total_amount),
                "discount_amount": float(discount_amount),
                "final_amount": float(final_amount),  # This now shows the discounted price
            })
            return Response(payment_response, status=status.HTTP_201_CREATED)

        # COD or other payment methods
        return Response({
            "order_id": checkout.order_id,
            "total_amount": float(total_amount),
            "final_amount": float(final_amount),  # Already correct for COD
            "discount_amount": float(discount_amount),
            "message": "Order placed successfully!"
        }, status=status.HTTP_201_CREATED)

    def _apply_coupon(self, coupon_code, total_amount):
        """Apply coupon code and calculate discount."""
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            current_date = timezone.now()

            # Validate coupon date
            if not (coupon.valid_from <= current_date <= coupon.valid_to):
                return {"error": "Coupon has expired."}

            # Check minimum order amount
            if hasattr(coupon, 'min_order_amount') and coupon.min_order_amount:
                if total_amount < Decimal(str(coupon.min_order_amount)):
                    return {
                        "error": f"Minimum order amount of {coupon.min_order_amount} required to use this coupon."
                    }

            # Calculate discount
            discount_amount = Decimal('0.00')
            if coupon.discount_type == 'percentage':
                discount_amount = total_amount * (Decimal(str(coupon.discount_value)) / Decimal('100'))
                if hasattr(coupon, 'max_discount') and coupon.max_discount:
                    discount_amount = min(discount_amount, Decimal(str(coupon.max_discount)))
            elif coupon.discount_type == 'fixed':
                discount_amount = Decimal(str(coupon.discount_value))
            
            # Ensure discount doesn't exceed total
            discount_amount = min(discount_amount, total_amount)

            return {"discount_amount": discount_amount}

        except Coupon.DoesNotExist:
            return {"error": "Invalid coupon code."}

    def _deduct_stock(self, product_type, product_id, quantity, variant=None, color=None, size=None):
        """
        Deduct stock based on product type.
        Returns dict with 'success' boolean and optional 'error' message.
        """
        try:
            if product_type == 'Grocery':
                return self._deduct_grocery_stock(product_id, variant, quantity)
            elif product_type == 'Fashion':
                return self._deduct_clothing_stock(product_id, color, size, quantity)
            elif product_type == 'Restaurant':
                # Restaurants typically don't manage stock
                return {"success": True}
            else:
                logger.warning(f"Unknown product type: {product_type}")
                return {"success": True}  # Don't fail checkout for unknown types

        except Exception as e:
            logger.error(f"Stock deduction failed: {str(e)}")
            return {"success": False, "error": str(e)}

    def _deduct_grocery_stock(self, product_id, variant, quantity):
        """Deduct stock for grocery products."""
        try:
            grocery_product = GroceryProducts.objects.get(id=product_id)
            weights = grocery_product.weights

            if not variant:
                return {"success": False, "error": "Variant is required for grocery items."}

            stock_updated = False

            # Handle list format
            if isinstance(weights, list):
                for weight_info in weights:
                    if weight_info.get('weight') == variant:
                        current_qty = weight_info.get('quantity', 0)
                        if current_qty < quantity:
                            return {
                                "success": False,
                                "error": f"Insufficient stock for {variant}. Available: {current_qty}"
                            }
                        weight_info['quantity'] = current_qty - quantity
                        weight_info['is_in_stock'] = (current_qty - quantity) > 0
                        stock_updated = True
                        break

            # Handle dict format
            elif isinstance(weights, dict):
                if variant in weights:
                    weight_info = weights[variant]
                    current_qty = weight_info.get('quantity', 0)
                    if current_qty < quantity:
                        return {
                            "success": False,
                            "error": f"Insufficient stock for {variant}. Available: {current_qty}"
                        }
                    weight_info['quantity'] = current_qty - quantity
                    weight_info['is_in_stock'] = (current_qty - quantity) > 0
                    stock_updated = True

            if not stock_updated:
                return {"success": False, "error": f"Variant '{variant}' not found."}

            grocery_product.save()
            logger.info(f"Grocery stock updated: Product {product_id}, Variant {variant}")
            return {"success": True}

        except GroceryProducts.DoesNotExist:
            return {"success": False, "error": f"Grocery product {product_id} not found."}

    def _deduct_clothing_stock(self, product_id, color, size, quantity):
        """Deduct stock for clothing products."""
        try:
            clothing = Clothing.objects.get(id=product_id)
            
            if not color or not size:
                return {"success": False, "error": "Color and size are required for clothing items."}

            clothing_color = ClothingColor.objects.get(
                clothing=clothing,
                color_name__iexact=color
            )
            clothing_size = ClothingSize.objects.get(
                color=clothing_color,
                size__iexact=size
            )

            # Check stock availability
            if clothing_size.stock < quantity:
                return {
                    "success": False,
                    "error": f"Insufficient stock. Available: {clothing_size.stock}"
                }

            # Deduct stock
            clothing_size.stock -= quantity
            clothing_size.save()

            logger.info(f"Clothing stock updated: Product {product_id}, Color {color}, Size {size}")
            return {"success": True}

        except Clothing.DoesNotExist:
            return {"success": False, "error": f"Clothing product {product_id} not found."}
        except ClothingColor.DoesNotExist:
            return {"success": False, "error": f"Color '{color}' not found."}
        except ClothingSize.DoesNotExist:
            return {"success": False, "error": f"Size '{size}' not available for color '{color}'."}

    def _create_razorpay_order(self, checkout, amount):
        """Create Razorpay order for online payment."""
        try:
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            razorpay_order = client.order.create({
                "amount": int(amount * 100),  # Convert to paise
                "currency": "INR",
                "payment_capture": "1",
                "notes": {
                    "order_id": checkout.order_id,
                    "user_id": checkout.user.id
                }
            })

            checkout.razorpay_order_id = razorpay_order['id']
            checkout.save()

            logger.info(f"Razorpay order created: {razorpay_order['id']}")

            return {
                "razorpay_order_id": checkout.razorpay_order_id,
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "amount": float(amount),  # This is already the final_amount (discounted)
                "currency": "INR",
                "message": "Razorpay order created successfully"
            }

        except Exception as e:
            logger.error(f"Razorpay error: {str(e)}")
            return {"error": "Payment gateway error. Please try again."}





class CheckoutListView(generics.ListAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Checkout.objects.filter(user=self.request.user)


class CheckoutDetailView(generics.RetrieveAPIView):
    queryset = Checkout.objects.all()
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Checkout.objects.filter(user=self.request.user)


class CancelOrderView(generics.UpdateAPIView):
    serializer_class = CheckoutSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Checkout.objects.filter(user=self.request.user, order_status="pending")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.order_status = "cancelled"
        instance.save()
        return Response({"message": "Order cancelled successfully."}, status=status.HTTP_200_OK)

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Enhanced Order Detail View with vendor, delivery boy, and location information
    """
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None
    # Don't set lookup_field - it defaults to 'pk' which is what works

    def get_queryset(self):
        """Optimize query with select_related and prefetch_related"""
        return Order.objects.select_related(
            'user', 
            'checkout'
        ).prefetch_related(
            'order_items'
        )


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_delivery_boy_for_order(request, order_id):
    """
    Get the delivery boy assigned to a specific order
    
    GET /api/orders/{order_id}/delivery-boy/
    """
    try:
        order = get_object_or_404(Order, order_id=order_id)
        
        # Get the latest delivery notification for this order
        notification = DeliveryNotification.objects.filter(
            order=order
        ).select_related('delivery_boy').order_by('-created_at').first()
        
        if notification and notification.delivery_boy:
            delivery_boy_data = DeliveryBoySerializer(notification.delivery_boy).data
            delivery_boy_data['notification_id'] = notification.id
            delivery_boy_data['assigned_at'] = notification.created_at
            delivery_boy_data['notification_message'] = notification.message
            
            return Response({
                'success': True,
                'delivery_boy': delivery_boy_data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'No delivery boy assigned to this order yet'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def assign_delivery_boy(request, order_id):
    """
    Assign a delivery boy to an order
    
    POST /api/orders/{order_id}/assign-delivery-boy/
    Body: {
        "delivery_boy_id": 1,
        "message": "Optional custom message"
    }
    """
    try:
        order = get_object_or_404(Order, order_id=order_id)
        delivery_boy_id = request.data.get('delivery_boy_id')
        
        if not delivery_boy_id:
            return Response({
                'success': False,
                'message': 'delivery_boy_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        delivery_boy = get_object_or_404(DeliveryBoy, id=delivery_boy_id)
        
        # Create notification
        message = request.data.get('message', f'New order #{order.order_id} assigned to you')
        
        notification = DeliveryNotification.objects.create(
            delivery_boy=delivery_boy,
            order=order,
            vendor=None,  # You can set vendor if needed
            message=message
        )
        
        return Response({
            'success': True,
            'message': 'Delivery boy assigned successfully',
            'notification_id': notification.id,
            'delivery_boy': DeliveryBoySerializer(delivery_boy).data
        }, status=status.HTTP_201_CREATED)
        
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except DeliveryBoy.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Delivery boy not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_available_delivery_boys(request):
    """
    Get list of available delivery boys for assignment
    
    GET /api/delivery-boys/available/
    """
    try:
        delivery_boys = DeliveryBoy.objects.all()
        serializer = DeliveryBoySerializer(delivery_boys, many=True)
        
        return Response({
            'success': True,
            'delivery_boys': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# Get Orders for Logged-in User
class UserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class UpdateOrderStatusView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(order_id=order_id)
            new_status = request.data.get("order_status")
            
            if new_status not in dict(Order.ORDER_STATUS_CHOICES).keys():
                return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
            
            order.order_status = new_status
            order.save()
            
            # When vendor changes status to 'PROCESSING', create notifications for delivery boys
            if new_status == 'PROCESSING':
                # Get all available delivery boys (you can add filters for nearby/available ones)
                delivery_boys = DeliveryBoy.objects.all() # Adjust filter as needed
                
                for delivery_boy in delivery_boys:
                    # Create OrderAssign entry
                    order_assign, created = OrderAssign.objects.get_or_create(
                        order=order,
                        delivery_boy=delivery_boy,
                        defaults={'status': 'ASSIGNED'}
                    )
                    
                    # Create notification for each delivery boy
                    DeliveryNotification.objects.create(
                        delivery_boy=delivery_boy,
                        order=order,
                        vendor=order.vendor,  # Assuming Order has vendor field
                        message=f"New order #{order.order_id} is ready for delivery. Tap to accept.",
                        is_read=False
                    )
            
            return Response({
                "message": f"Order {order_id} status updated to {new_status}",
                "notifications_sent": new_status == 'PROCESSING'
            }, status=status.HTTP_200_OK)
            
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)




class OrderPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrderFilter(filters.FilterSet):
    """Filter for orders by status and date range"""
    order_status = filters.CharFilter(field_name='order_status', lookup_expr='iexact')
    start_date = filters.DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = filters.DateFilter(field_name='created_at', lookup_expr='lte')
    search = filters.CharFilter(method='search_filter')

    class Meta:
        model = Order
        fields = ['order_status', 'start_date', 'end_date']

    def search_filter(self, queryset, name, value):
        """Search across order_id, user name, and payment method"""
        return queryset.filter(
            Q(order_id__icontains=value) |
            Q(user__name__icontains=value) |
            Q(payment_method__icontains=value)
        )


class AllorderviewAdmin(APIView):
    permission_classes = [IsAdminUser]
    pagination_class = OrderPagination
    
    def get(self, request):
        # Get all orders in LIFO order (newest first)
        orders = Order.objects.all().select_related('user').order_by('-created_at')
        
        # Apply filters if provided
        order_status = request.query_params.get('order_status')
        if order_status and order_status.lower() != 'all':
            orders = orders.filter(order_status__iexact=order_status)
        
        # Date filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date:
            orders = orders.filter(created_at__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__lte=end_date)
        
        # Search filtering
        search = request.query_params.get('search')
        if search:
            orders = orders.filter(
                Q(order_id__icontains=search) |
                Q(user__name__icontains=search) |
                Q(payment_method__icontains=search)
            )
        
        # Get total count before pagination
        total_count = orders.count()
        
        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(orders, request)
        
        if page is not None:
            # Calculate serial numbers for this page
            page_number = paginator.page.number
            page_size = paginator.page_size
            start_index = total_count - ((page_number - 1) * page_size)
            
            # Serialize the data
            serializer = OrderSerializer(page, many=True, context={'request': request})
            
            # Add serial numbers to each order
            data_with_serial = []
            for i, item in enumerate(serializer.data):
                item['serial_number'] = start_index - i
                data_with_serial.append(item)
            
            return paginator.get_paginated_response(data_with_serial)
        
        # Fallback without pagination (should not normally happen)
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)

# class VendorOrderListView(APIView):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [VendorJWTAuthentication]

#     def get(self, request):
#         vendor = request.user
#         status_filter = request.query_params.get('order_status')

#         vendor_orders = Order.objects.filter(checkout__items__vendor=vendor)
#         if status_filter:
#             vendor_orders = vendor_orders.filter(order_status=status_filter)

#         vendor_orders = vendor_orders.distinct().prefetch_related('checkout__items')

#         order_data = []
#         for order in vendor_orders:
#             vendor_items = order.checkout.items.filter(vendor=vendor)

#             order_data.append({
#                 "id":order.id,
#                 "order_id": order.order_id,
#                 "user_name": order.user.name,
#                 "total_amount": order.total_amount,
#                 "final_amount": order.final_amount,
#                 "used_coupon": order.used_coupon,
#                 "payment_method": order.payment_method,
#                 "payment_status": order.payment_status,
#                 "order_status": order.order_status,
#                 "shipping_address": order.shipping_address,
#                 "contact_number": order.contact_number,
#                 "created_at": order.created_at,
#                 "updated_at": order.updated_at,
#                 "products": CheckoutItemSerializer(vendor_items, many=True).data
#             })

#         return Response(order_data)

class VendorOrderListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request):
        vendor = request.user
        status_filter = request.query_params.get('order_status')

        vendor_orders = Order.objects.filter(checkout__items__vendor=vendor)
        if status_filter:
            vendor_orders = vendor_orders.filter(order_status=status_filter)

        vendor_orders = vendor_orders.distinct().prefetch_related('checkout__items')

        serialized_orders = []
        for order in vendor_orders:
            # Filter product_details only for this vendor
            all_items = order.product_details or []
            filtered_items = [
                item for item in all_items
                if any(
                    str(item.get('product_id')) == str(product.id)
                    for product in Clothing.objects.filter(id=item.get('product_id'), vendor=vendor)
                ) or any(
                    str(item.get('product_id')) == str(product.id)
                    for product in GroceryProducts.objects.filter(id=item.get('product_id'), vendor=vendor)
                ) or any(
                    str(item.get('product_id')) == str(product.id)
                    for product in Dish.objects.filter(id=item.get('product_id'), vendor=vendor)
                )
            ]

            # Temporarily override product_details for serialization
            order.product_details = filtered_items

            serializer = OrderSerializer(order, context={'request': request})
            serialized_orders.append(serializer.data)

        return Response(serialized_orders)



class VendorOrderDetailView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request, order_id):
        vendor = request.user
        order = get_object_or_404(Order, order_id=order_id, checkout__items__vendor=vendor)
        vendor_items = order.checkout.items.filter(vendor=vendor)

        data = {
            "order_id": order.order_id,
            "user_name": order.user.name,
            "total_amount": order.total_amount,
            "final_amount": order.final_amount,
            "used_coupon": order.used_coupon,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
            "order_status": order.order_status,
            "shipping_address": order.shipping_address,
            "contact_number": order.contact_number,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "products": CheckoutItemSerializer(vendor_items, many=True).data
        }

        return Response(data)

    # def patch(self, request, order_id):
    #     vendor = request.user
    #     order = get_object_or_404(Order, order_id=order_id, checkout__items__vendor=vendor)
    #     vendor_items = order.checkout.items.filter(vendor=vendor)

    #     with transaction.atomic():
    #         for item in vendor_items:
    #             item_data = request.data.get(str(item.id), {})
    #             if "order_status" in item_data:
    #                 item.status = item_data["order_status"]
    #             if "quantity" in item_data:
    #                 item.quantity = item_data["quantity"]
    #             item.save()

    #         order.update_order_status()
    #         order.recalculate_total()

    #     return Response({'message': 'Vendor-specific order items updated and order recalculated.'}, status=status.HTTP_200_OK)



class VendorOrderUpdateDetailView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def patch(self, request, order_id):
        order = get_object_or_404(Order, order_id=order_id)

        new_status = request.data.get('order_status')
        if not new_status:
            return Response(
                {"detail": "order_status field is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_statuses = [choice[0] for choice in Order.ORDER_STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {"detail": f"Invalid order_status. Must be one of {valid_statuses}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Store old status to check if it's changing
        old_status = order.order_status
        order.order_status = new_status
        order.save()

        # If status changed to 'processing', create OrderAssign entry
        if new_status.lower() == 'processing' and old_status != new_status:
            # Get an available delivery boy (you'll need to implement your logic here)
            delivery_boy = self.get_available_delivery_boy()
            
            if delivery_boy:
                # Check if assignment already exists to avoid duplicates
                existing_assignment = OrderAssign.objects.filter(
                    order=order,
                    status='ASSIGNED'
                ).first()
                
                if not existing_assignment:
                    OrderAssign.objects.create(
                        order=order,
                        delivery_boy=delivery_boy,
                        status='ASSIGNED'
                    )
            else:
                # Log or handle case where no delivery boy is available
                pass

        return Response(
            {"detail": f"Order status updated to '{new_status}'."},
            status=status.HTTP_200_OK
        )

    def get_available_delivery_boy(self):
        """
        Implement your logic to select an available delivery boy.
        Examples:
        - Round-robin assignment
        - Least busy delivery boy
        - Nearest delivery boy based on location
        - Random assignment
        """
        # Example: Get a delivery boy with fewest active assignments
        from django.db.models import Count
        
        delivery_boy = DeliveryBoy.objects.annotate(
            active_orders=Count('assigned_orders', filter=models.Q(
                assigned_orders__status__in=['ASSIGNED', 'ACCEPTED', 'PICKED', 'ON_THE_WAY']
            ))
        ).order_by('active_orders').first()
        
        return delivery_boy



class GroupedCartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        cart_items = CartItem.objects.filter(cart__user=user)

        # Group by vendor
        grouped_data = {}
        for item in cart_items:
            vendor_id = str(item.vendor.id)
            if vendor_id not in grouped_data:
                grouped_data[vendor_id] = {
                    "vendor_id": item.vendor.id,
                    "vendor_name": item.vendor.business_name,
                    "store_type" : item.product_type,
                    "vendor_logo": request.build_absolute_uri(item.vendor.store_logo.url) if item.vendor.store_logo else None,
                    "vendor_image": request.build_absolute_uri(item.vendor.display_image.url) if item.vendor.display_image else None,
                    "items": []
                }
            grouped_data[vendor_id]["items"].append(item)

        for group in grouped_data.values():
            group["item_count"] = len(group["items"])
            group["items"] = CartItemSerializer(group["items"], many=True, context={'request': request}).data

        return Response(list(grouped_data.values()), status=status.HTTP_200_OK)


class VendorCartItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, vendor_id):
        user = request.user
        shipping_address_id = request.query_params.get('shipping_address_id')
        
        cart_items = CartItem.objects.filter(cart__user=user, vendor_id=vendor_id)

        if not cart_items.exists():
            return Response({"detail": "No items found for this vendor."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CartItemSerializer(cart_items, many=True, context={'request': request})

        subtotal = sum(item.quantity * float(item.price) for item in cart_items)

        delivery_charge = Decimal('0.00')
        delivery_charge_details = None
        address_details = None

        # Initialize variable BEFORE use
        vendor_details = None

        # Always fetch vendor and include lat/long
        try:
            vendor = Vendor.objects.get(pk=vendor_id)
            vendor_details = {
                'id': vendor.id,
                'name': vendor.business_name if hasattr(vendor, 'store_name') else getattr(vendor, 'name', None),
                'latitude': float(vendor.latitude) if vendor.latitude else None,
                'longitude': float(vendor.longitude) if vendor.longitude else None,
            }
        except Vendor.DoesNotExist:
            return Response({"error": "Vendor not found"}, status=status.HTTP_404_NOT_FOUND)

        # If shipping address provided, calculate delivery charge
        if shipping_address_id:
            try:
                address = Address.objects.get(id=shipping_address_id, user=user)

                address_details = {
                    'id': address.id,
                    'address_type': address.address_type,
                    'address_name': address.address_name,
                    'address_line1': address.address_line1,
                    'address_line2': address.address_line2,
                    'latitude': float(address.latitude) if address.latitude else None,
                    'longitude': float(address.longitude) if address.longitude else None,
                    'city': address.city,
                    'state': address.state,
                    'country': address.country,
                    'pincode': address.pincode,
                    'contact_number': address.contact_number,
                    'full_address': f"{address.address_line1}, {address.city}, {address.state}, {address.pincode}"
                }

                delivery_result = self.calculate_delivery_charge(vendor, address)

                if delivery_result['success']:
                    delivery_charge = delivery_result['charge']
                    delivery_charge_details = delivery_result
                else:
                    delivery_charge_details = {'error': delivery_result.get('error', 'Could not calculate delivery charge')}

            except Address.DoesNotExist:
                delivery_charge_details = {'error': 'Invalid shipping address'}

        final_total = subtotal + float(delivery_charge)

        response_data = {
            "vendor_id": vendor_id,
            "vendor_location": vendor_details,  # ALWAYS RETURNED
            "subtotal": subtotal,
            "delivery_charge": float(delivery_charge),
            "final_total_amount": final_total,
            "items": serializer.data
        }

        if address_details:
            response_data['delivery_address'] = address_details
        
        if delivery_charge_details:
            response_data['delivery_charge_details'] = delivery_charge_details

        return Response(response_data, status=status.HTTP_200_OK)

    def calculate_delivery_charge(self, vendor, address):
        if not all([vendor.latitude, vendor.longitude, address.latitude, address.longitude]):
            return {'success': False, 'error': 'Vendor or address coordinates not available'}

        try:
            vendor_coords = (float(vendor.latitude), float(vendor.longitude))
            user_coords = (float(address.latitude), float(address.longitude))

            distance = round(geodesic(vendor_coords, user_coords).kilometers, 2)

            now = timezone.localtime().time()
            is_night = self.is_night_time(now)

            delivery_charge_obj = DeliveryCharges.objects.filter(
                distance_from__lte=distance,
                distance_to__gte=distance,
                is_active=True
            ).first()

            if not delivery_charge_obj:
                return {'success': False, 'error': f'No delivery charge configured for distance {distance}km'}

            charge = delivery_charge_obj.night_charge if is_night else delivery_charge_obj.day_charge

            return {
                'success': True,
                'distance': distance,
                'charge': Decimal(str(charge)),
                'is_night': is_night,
                'charge_type': 'night' if is_night else 'day',
                'distance_range': f"{delivery_charge_obj.distance_from}km - {delivery_charge_obj.distance_to}km"
            }

        except Exception as e:
            return {'success': False, 'error': f'Error calculating delivery charge: {str(e)}'}

    def is_night_time(self, current_time):
        try:
            delivery_config = DeliveryCharges.objects.filter(is_active=True).first()
            if delivery_config:
                night_start = delivery_config.night_start_time
                night_end = delivery_config.night_end_time
            else:
                night_start = timezone.datetime.strptime("22:00:00", "%H:%M:%S").time()
                night_end = timezone.datetime.strptime("06:00:00", "%H:%M:%S").time()
        except:
            night_start = timezone.datetime.strptime("22:00:00", "%H:%M:%S").time()
            night_end = timezone.datetime.strptime("06:00:00", "%H:%M:%S").time()

        if night_start > night_end:
            return current_time >= night_start or current_time <= night_end
        return night_start <= current_time <= night_end





class ApplyCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, vendor_id):
        user = request.user
        coupon_code = request.data.get('coupon_code')

        if not coupon_code:
            return Response(
                {'error': 'Coupon code is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            cart = Cart.objects.get(user=user)
            cart_items = CartItem.objects.filter(cart=cart, vendor_id=vendor_id)

            if not cart_items.exists():
                return Response(
                    {'error': 'No items in cart for this vendor.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_amount = sum(
                Decimal(str(item.price)) * item.quantity 
                for item in cart_items
            )

            coupon_result = self.validate_and_apply_coupon(
                coupon_code, 
                total_amount, 
                user, 
                vendor_id
            )

            if 'error' in coupon_result:
                return Response(
                    {'error': coupon_result['error']}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            coupon = coupon_result['coupon']
            discount_amount = coupon_result['discount']
            final_amount = total_amount - discount_amount
            final_amount = max(final_amount, Decimal('0.00'))

            return Response({
                'coupon_code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': float(coupon.discount_value),
                'original_amount': float(total_amount),
                'discount_amount': float(discount_amount),
                'final_amount': float(final_amount),
                'min_order_amount': float(coupon.min_order_amount) if coupon.min_order_amount else None,
                'max_discount': float(coupon.max_discount) if coupon.max_discount else None,
                'message': 'Coupon applied successfully!'
            }, status=status.HTTP_200_OK)

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to apply coupon: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def validate_and_apply_coupon(self, coupon_code, total_amount, user, vendor_id):
        now = timezone.now()
        
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                valid_from__lte=now,
                valid_to__gte=now,
                is_active=True
            )
        except Coupon.DoesNotExist:
            return {'error': 'Invalid or expired coupon code.'}

        if coupon.vendor and coupon.vendor.id != int(vendor_id):
            return {'error': 'This coupon is not valid for this vendor.'}

        if coupon.min_order_amount and total_amount < coupon.min_order_amount:
            return {
                'error': f'Minimum order amount of ₹{coupon.min_order_amount} required.'
            }

        if coupon.usage_limit == 1:
            if UserCouponUsage.objects.filter(coupon=coupon, user=user).exists():
                return {'error': 'You have already used this coupon.'}

        if coupon.is_new_customer:
            if Order.objects.filter(user=user).exists():
                return {'error': 'This coupon is for new customers only.'}

        if coupon.discount_type == 'percentage':
            discount = (total_amount * coupon.discount_value) / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else: 
            discount = min(coupon.discount_value, total_amount)

        return {'coupon': coupon, 'discount': discount}


class RemoveCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, vendor_id):
        user = request.user

        try:
            cart = Cart.objects.get(user=user)
            cart_items = CartItem.objects.filter(cart=cart, vendor_id=vendor_id)

            if not cart_items.exists():
                return Response(
                    {'error': 'No items in cart for this vendor.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            total_amount = sum(
                Decimal(str(item.price)) * item.quantity 
                for item in cart_items
            )

            return Response({
                'original_amount': float(total_amount),
                'final_amount': float(total_amount),
                'discount_amount': 0.00,
                'message': 'Coupon removed successfully!'
            }, status=status.HTTP_200_OK)

        except Cart.DoesNotExist:
            return Response(
                {'error': 'Cart not found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to remove coupon: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class VendorCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, vendor_id):
        user = request.user
        data = request.data

        shipping_address_id = data.get('shipping_address_id')
        payment_method = data.get('payment_method', 'cod')
        coupon_code = data.get('coupon_code')
        delivery_charge_amount = data.get('delivery_charge')

        # Validation
        if not shipping_address_id:
            return Response({'error': 'Shipping address is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if delivery_charge_amount is None:
            return Response({'error': 'Delivery charge is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            delivery_charge_amount = Decimal(str(delivery_charge_amount))
        except (ValueError, TypeError):
            return Response({'error': 'Invalid delivery charge value.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Fetch required objects
                address = Address.objects.select_for_update().get(id=shipping_address_id, user=user)
                vendor = Vendor.objects.select_for_update().get(id=vendor_id)
                cart = Cart.objects.select_for_update().get(user=user)
                cart_items = cart.items.filter(vendor=vendor).select_related('vendor')

                if not cart_items.exists():
                    return Response({'error': 'No items in cart for this vendor.'}, status=status.HTTP_400_BAD_REQUEST)

                # Calculate amounts
                total_amount = sum(item.price * item.quantity for item in cart_items)
                coupon = None
                coupon_discount = Decimal('0.00')

                # Apply coupon if provided
                if coupon_code:
                    coupon_result = self.validate_and_apply_coupon(coupon_code, total_amount, user, vendor_id)
                    if 'error' in coupon_result:
                        return Response({'error': coupon_result['error']}, status=status.HTTP_400_BAD_REQUEST)
                    coupon = coupon_result['coupon']
                    coupon_discount = coupon_result['discount']

                subtotal = total_amount
                discount_amount = coupon_discount
                amount_after_discount = subtotal - discount_amount
                final_amount = max(amount_after_discount + delivery_charge_amount, Decimal('0.00'))

                # Generate order details
                order_id = f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-{user.id}"
                delivery_pin = str(random.randint(100000, 999999))

                # Create checkout
                checkout = Checkout.objects.create(
                    user=user,
                    order_id=order_id,
                    total_amount=subtotal,
                    discount_amount=discount_amount,
                    delivery_charge=delivery_charge_amount,
                    final_amount=final_amount,
                    payment_method=payment_method,
                    shipping_address=address,
                    coupon=coupon,
                    coupon_code=coupon_code if coupon else None,
                    coupon_discount=coupon_discount
                )

                # Create checkout items and handle stock reduction
                product_details = []
                for item in cart_items:
                    CheckoutItem.objects.create(
                        checkout=checkout,
                        vendor=item.vendor,
                        product_type=item.product_type,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        color=item.color,
                        size=item.size,
                        variant=item.variant,
                        price=item.price,
                        subtotal=item.price * item.quantity,
                    )
                    
                    product_details.append({
                        "product_id": item.product_id,
                        "variant": item.variant,
                        "quantity": item.quantity,
                        "color": item.color,
                        "size": item.size
                    })

                    # Handle stock reduction
                    try:
                        if item.product_type == 'grocery':
                            self.handle_grocery_stock_reduction(item)
                        elif item.product_type == 'clothing':
                            self.handle_clothing_stock_reduction(item)
                    except Exception as e:
                        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

                # Create order
                order = Order.objects.create(
                    user=user,
                    checkout=checkout,
                    order_id=order_id,
                    total_amount=final_amount,
                    delivery_charge=delivery_charge_amount,
                    final_amount=final_amount,
                    payment_method=payment_method,
                    order_status='pending',
                    shipping_address=address,
                    used_coupon=checkout.coupon_code,
                    delivery_pin=delivery_pin,
                    product_details=product_details
                )

                # Create database notifications
                Notification.objects.create(
                    user=user,
                    order=order,
                    title="Order Placed Successfully",
                    message=f"Your order with ID {order_id} has been placed successfully and will be processed shortly.",
                    notification_type='general'
                )

                user_name = (
                    user.get_full_name() if callable(getattr(user, 'get_full_name', None))
                    else getattr(user, 'username', 'User')
                )

                Notification.objects.create(
                    user=user,
                    vendor=vendor,
                    order=order,
                    title="New Order Received",
                    message=f"You have received a new order with ID {order_id} from {user_name}.",
                    notification_type='new_order'
                )

                # ✨ SEND FCM PUSH NOTIFICATIONS ✨
                # These will fail gracefully if FCM is not set up or tokens are missing
                try:
                    # Send to user
                    user_notification_result = send_order_placed_notification(user, order_id, final_amount)
                    if user_notification_result:
                        logger.info(f"Successfully sent order placed notification to user {user.id}")
                    else:
                        logger.warning(f"Failed to send order placed notification to user {user.id}")
                except Exception as e:
                    logger.error(f"Error sending user notification: {str(e)}")
                
                try:
                    # Send to vendor
                    vendor_notification_result = send_new_order_notification(vendor, order_id, user_name, final_amount)
                    if vendor_notification_result:
                        logger.info(f"Successfully sent new order notification to vendor {vendor.id}")
                    else:
                        logger.warning(f"Failed to send new order notification to vendor {vendor.id}")
                except Exception as e:
                    logger.error(f"Error sending vendor notification: {str(e)}")

                # Create order items
                for item in cart_items:
                    product_name = self.get_product_name(item)
                    
                    OrderItem.objects.create(
                        order=order,
                        product_id=item.product_id,
                        product_type=item.product_type,
                        product_name=product_name,
                        quantity=item.quantity,
                        price_per_unit=item.price,
                        subtotal=item.price * item.quantity,
                        variant=item.variant,
                        status='pending'
                    )

                # Record coupon usage
                if coupon:
                    UserCouponUsage.objects.create(coupon=coupon, user=user, checkout=checkout)

                # Clear cart items
                cart_items.delete()

                # Prepare response
                response_data = {
                    "order_id": order.order_id,
                    "subtotal": float(subtotal),
                    "discount": float(discount_amount),
                    "delivery_charge": float(delivery_charge_amount),
                    "total": float(final_amount),
                    "coupon_applied": coupon.code if coupon else None,
                    "payment_method": payment_method,
                    "payment_status": "pending",
                    "delivery_pin": delivery_pin,
                    "message": "Order placed successfully!"
                }

                # Handle online payment
                if payment_method == 'online':
                    try:
                        import razorpay
                        client = razorpay.Client(
                            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                        )
                        razorpay_order = client.order.create({
                            "amount": int(final_amount * 100),
                            "currency": "INR",
                            "payment_capture": "1"
                        })
                        checkout.razorpay_order_id = razorpay_order['id']
                        checkout.save()
                        
                        response_data.update({
                            "razorpay_order_id": razorpay_order['id'],
                            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                            "razorpay_amount": int(final_amount * 100),
                            "currency": "INR"
                        })
                    except Exception as e:
                        logger.error(f"Razorpay error: {str(e)}")
                        return Response(
                            {'error': f'Payment error: {str(e)}'}, 
                            status=status.HTTP_503_SERVICE_UNAVAILABLE
                        )

                return Response(response_data, status=status.HTTP_201_CREATED)

        except (Vendor.DoesNotExist, Address.DoesNotExist, Cart.DoesNotExist) as e:
            logger.error(f"Object not found: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Checkout failed: {str(e)}", exc_info=True)
            return Response(
                {'error': f'Checkout failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get_product_name(self, item):
        """Helper method to get product name based on product type"""
        product_id = item.product_id
        product_type = item.product_type
        product_name = f"Product {product_id}"

        try:
            if product_type.lower() == 'clothing':
                product = Clothing.objects.filter(id=product_id).first()
                product_name = product.name if product else product_name
            elif product_type.lower() == 'grocery':
                product = GroceryProducts.objects.filter(id=product_id).first()
                product_name = product.name if product else product_name
            elif product_type.lower() == 'restaurent':
                product = Dish.objects.filter(id=product_id).first()
                product_name = product.name if product else product_name
        except Exception as e:
            logger.warning(f"Error fetching product name: {str(e)}")

        return product_name

    def handle_grocery_stock_reduction(self, item):
        """Handle stock reduction for grocery products"""
        product = GroceryProducts.objects.select_for_update().get(id=item.product_id)

        if isinstance(product.weights, list):
            new_weights = []
            found = False
            for weight in product.weights:
                new_weight = weight.copy()
                if weight['weight'] == item.variant:
                    if weight['quantity'] < item.quantity:
                        raise ValueError(f"Insufficient stock for {item.variant}")
                    new_weight['quantity'] = weight['quantity'] - item.quantity
                    new_weight['is_in_stock'] = new_weight['quantity'] > 0
                    found = True
                new_weights.append(new_weight)

            if not found:
                raise ValueError(f"Variant {item.variant} not found")

            GroceryProducts.objects.filter(id=product.id).update(weights=new_weights)

        elif isinstance(product.weights, dict):
            variant_data = product.weights.get(item.variant)
            if not variant_data or variant_data['quantity'] < item.quantity:
                raise ValueError(f"Insufficient stock for {item.variant}")

            updated_variant = {
                **product.weights,
                item.variant: {
                    'quantity': variant_data['quantity'] - item.quantity,
                    'is_in_stock': (variant_data['quantity'] - item.quantity) > 0,
                    'price': variant_data['price']
                }
            }
            GroceryProducts.objects.filter(id=product.id).update(weights=updated_variant)
        else:
            raise ValueError("Invalid weight format")

    def handle_clothing_stock_reduction(self, item):
        """Handle stock reduction for clothing products"""
        from django.db.models import F
        
        updated = ClothingSize.objects.filter(
            color__clothing_id=item.product_id,
            color__color_name=item.color,
            size=item.size
        ).update(stock=F('stock') - item.quantity)

        if updated == 0:
            raise ValueError("Size/color combination not found")

        size = ClothingSize.objects.get(
            color__clothing_id=item.product_id,
            color__color_name=item.color,
            size=item.size
        )
        if size.stock < 0:
            raise ValueError("Insufficient stock after reduction")

        clothing = Clothing.objects.get(id=item.product_id)
        for color in clothing.colors:
            if color['color_name'] == item.color:
                for size_entry in color.get('sizes', []):
                    if size_entry['size'] == item.size:
                        size_entry['stock'] = size.stock
        clothing.save(update_fields=['colors'])

    def validate_and_apply_coupon(self, coupon_code, total_amount, user, vendor_id):
        """Validate and apply coupon discount"""
        now = timezone.now()
        try:
            coupon = Coupon.objects.get(
                code=coupon_code,
                valid_from__lte=now,
                valid_to__gte=now,
                is_active=True
            )
        except Coupon.DoesNotExist:
            return {'error': 'Invalid or expired coupon code.'}

        if coupon.vendor and coupon.vendor.id != int(vendor_id):
            return {'error': 'This coupon is not valid for this vendor.'}

        if coupon.min_order_amount and total_amount < coupon.min_order_amount:
            return {'error': f'Minimum order amount of {coupon.min_order_amount} required.'}

        if coupon.usage_limit == 1 and UserCouponUsage.objects.filter(coupon=coupon, user=user).exists():
            return {'error': 'You have already used this coupon.'}

        if coupon.is_new_customer and Order.objects.filter(user=user).exists():
            return {'error': 'This coupon is for new customers only.'}

        if coupon.discount_type == 'percentage':
            discount = (total_amount * coupon.discount_value) / 100
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:
            discount = min(coupon.discount_value, total_amount)

        return {'coupon': coupon, 'discount': discount}


import hmac
import hashlib
class RazorpayPaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id')
        razorpay_payment_id = request.data.get('razorpay_payment_id')
        razorpay_signature = request.data.get('razorpay_signature')

        if not (razorpay_order_id and razorpay_payment_id and razorpay_signature):
            return Response({"error": "Missing payment data."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            checkout = Checkout.objects.get(razorpay_order_id=razorpay_order_id)
            order = Order.objects.get(checkout=checkout)
        except Checkout.DoesNotExist:
            return Response({"error": "Invalid order reference."}, status=status.HTTP_404_NOT_FOUND)

        generated_signature = hmac.new(
            key=settings.RAZORPAY_KEY_SECRET.encode(),
            msg=(razorpay_order_id + "|" + razorpay_payment_id).encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        if generated_signature != razorpay_signature:
            order.order_status = 'payment_failed'
            order.save(update_fields=['order_status'])
            return Response({"error": "Payment signature verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        checkout.payment_status = 'paid'
        checkout.razorpay_payment_id = razorpay_payment_id
        checkout.save(update_fields=['payment_status', 'razorpay_payment_id'])

        order.order_status = 'confirmed'
        order.save(update_fields=['order_status'])

        Notification.objects.create(
            user=order.user,
            order=order,
            title="Payment Successful",
            message=f"Your payment for order {order.order_id} was successful.",
            notification_type='payment_success'
        )

        return Response({
            "message": "Payment verified successfully.",
            "order_id": order.order_id,
            "payment_status": "paid",
            "order_status": "confirmed"
        }, status=status.HTTP_200_OK)


# Get Orders for Logged-in User

class UserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)\
            .select_related('checkout')\
            .prefetch_related('checkout__items')

#get single user order using order id
class UserOrderDetailView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    lookup_url_kwarg = 'order_id'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)\
            .select_related('checkout')\
            .prefetch_related('checkout__items')



class CancelOrderItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id, item_id):
        try:
            # Get the order with permission check
            order = get_object_or_404(
                Order,
                order_id=order_id,
                user=request.user
            )

            # Get the specific order item
            order_item = get_object_or_404(
                OrderItem,
                id=item_id,
                order=order
            )

            reason = request.data.get('reason', '')

            if not reason:
                return Response(
                    {"error": "Cancellation reason is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if order_item.status in ['cancelled', 'delivered']:
                return Response(
                    {"error": f"Item is already {order_item.status}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Update the order item
            order_item.status = 'cancelled'
            order_item.cancel_reason = reason
            order_item.cancelled_at = timezone.now()
            order_item.save()

            # Update order status and totals
            order.update_order_status()
            order.recalculate_total()
            order.save()

            # Serialize the response with proper product details
            serializer = OrderSerializer(order, context={'request': request})

            return Response({
                "success": True,
                "message": f"Order item {item_id} cancelled successfully",
                "cancelled_item": {
                    "id": order_item.id,
                    "product_id": order_item.product_id,
                    "product_name": order_item.product_name,
                    "status": order_item.status,
                    "cancel_reason": order_item.cancel_reason,
                    "cancelled_at": order_item.cancelled_at
                },
                "order": serializer.data,
                "new_order_status": order.order_status,
                "new_final_amount": str(order.final_amount)
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DeleteAllOrdersView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request):
        total = Order.objects.count()
        if total == 0:
            return Response({'message': 'No orders to delete.'}, status=status.HTTP_200_OK)

        Order.objects.all().delete()
        return Response({'message': f'All {total} orders have been deleted.'}, status=status.HTTP_200_OK)


class OrderItemsByOrderIDView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        try:
            order = get_object_or_404(Order, order_id=order_id, user=request.user)
            order_items = OrderItem.objects.filter(order=order).order_by('created_at')

            # Collect product IDs by normalized type
            fashion_ids, dish_ids, grocery_ids = [], [], []
            normalized_types = {}

            for item in order_items:
                raw_type = item.product_type.lower()
                if raw_type in ['restaurant', 'restaurent', 'food']:
                    product_type = 'dish'
                    dish_ids.append(item.product_id)
                elif raw_type in ['grocery', 'groceries']:
                    product_type = 'grocery'
                    grocery_ids.append(item.product_id)
                elif raw_type in ['fashion', 'clothing']:
                    product_type = 'fashion'
                    fashion_ids.append(item.product_id)
                else:
                    product_type = raw_type  # fallback
                normalized_types[item.id] = product_type

            # Bulk fetch products
            fashion_products = {
                c.id: c for c in Clothing.objects.filter(id__in=fashion_ids)
            }
            dish_products = {
                d.id: d for d in Dish.objects.filter(id__in=dish_ids)
            }
            grocery_products = {
                g.id: g for g in GroceryProducts.objects.filter(id__in=grocery_ids)
            }

            # Bulk fetch related images
            fashion_images = {
                c.id: ClothingImage.objects.filter(clothing=c)
                for c in fashion_products.values()
            }
            dish_images = {
                d.id: DishImage.objects.filter(dish=d)
                for d in dish_products.values()
            }
            grocery_images = {
                g.id: GroceryProductImage.objects.filter(product=g)
                for g in grocery_products.values()
            }

            items_data = []
            for item in order_items:
                product_id = item.product_id
                product_type = normalized_types.get(item.id)
                variant = item.variant
                images = []
                main_image = None
                variant_image = None
                product_name = item.product_name  # default/fallback

                if product_type == 'fashion':
                    product = fashion_products.get(product_id)
                    if product:
                        product_name = product.name
                        images = [
                            request.build_absolute_uri(img.image.url)
                            for img in fashion_images.get(product.id, []) if img.image
                        ]
                        main_image = images[0] if images else None

                        # Optional: use color-based variant image
                        if variant and '-' in variant:
                            color = variant.split('-')[0].strip().lower()
                            matched_image = next(
                                (img for img in fashion_images.get(product.id, [])
                                 if color in img.image.name.lower()),
                                None
                            )
                            if matched_image:
                                variant_image = request.build_absolute_uri(matched_image.image.url)

                elif product_type == 'dish':
                    product = dish_products.get(product_id)
                    if product:
                        product_name = product.name
                        images = [
                            request.build_absolute_uri(img.image.url)
                            for img in dish_images.get(product.id, []) if img.image
                        ]
                        main_image = images[0] if images else None

                elif product_type == 'grocery':
                    product = grocery_products.get(product_id)
                    if product:
                        product_name = product.name
                        images = [
                            request.build_absolute_uri(img.image.url)
                            for img in grocery_images.get(product.id, []) if img.image
                        ]
                        main_image = images[0] if images else None

                item_data = {
                    "id": item.id,
                    "product_id": product_id,
                    "product_name": product_name,
                    "product_type": item.product_type,
                    "quantity": item.quantity,
                    "price_per_unit": str(item.price_per_unit),
                    "subtotal": str(item.subtotal),
                    "status": item.status,
                    "variant": item.variant,
                    "cancel_reason": item.cancel_reason,
                    "cancelled_at": item.cancelled_at.isoformat() if item.cancelled_at else None,
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat(),
                    "order_id": item.order_id,
                    "color": item.color,
                    "size": item.size,
                    "product_image": main_image,
                    "images": images,
                    "variant_image": variant_image
                }
                items_data.append(item_data)

            return Response({
                "order_id": order.order_id,
                "order_status": order.order_status,
                "payment_status": order.payment_status,
                "final_amount": str(order.final_amount),
                "items": items_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)

class ReturnOrderItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id, item_id):
        # Validate Order
        order = get_object_or_404(Order, order_id=order_id, user=request.user)

        # Validate Order Item
        order_item = get_object_or_404(OrderItem, id=item_id, order=order)

        if order_item.status != 'delivered':
            return Response(
                {"error": f"Only delivered items can be returned. Current status: {order_item.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark item as returned
        order_item.status = 'return'
        order_item.cancel_reason = request.data.get('reason', '')
        order_item.cancelled_at = timezone.now()
        order_item.save()

        # Update order status and recalculate total
        order.update_order_status()
        order.recalculate_total()

        serializer = OrderSerializer(order, context={'request': request})

        # Get product details directly from the order item
        product_id = None
        product_name = None

        # Try different ways to get product information based on your model structure
        if hasattr(order_item, 'product_id'):
            product_id = order_item.product_id
        elif hasattr(order_item, 'product') and order_item.product:
            product_id = order_item.product.id
            product_name = order_item.product.name
        elif hasattr(order_item, 'product_details'):
            product_id = order_item.product_details.get('product_id')
            product_name = order_item.product_details.get('product_name')

        return Response({
            "success": True,
            "message": f"Order item {item_id} return initiated successfully",
            "returned_item": {
                "id": order_item.id,
                "product_id": product_id,
                "product_name": product_name,
                "status": order_item.status,
                "return_reason": order_item.cancel_reason,
                "returned_at": order_item.cancelled_at
            },
            "order": serializer.data,
            "new_order_status": order.order_status,
            "new_final_amount": str(order.final_amount) if order.final_amount else "0"
        }, status=status.HTTP_200_OK)

class UpdateOrderItemStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id, item_id):
        order = get_object_or_404(Order, order_id=order_id, user=request.user)
        order_item = get_object_or_404(OrderItem, id=item_id, order=order)

        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Only check: if currently cancelled, block ALL changes
        if order_item.status == 'cancelled':
            return Response(
                {"error": f"Cannot update item. Current status: cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update status
        order_item.status = new_status
        order_item.save()

        # Update parent order status if needed
        order.update_order_status()
        order.recalculate_total()

        serializer = OrderSerializer(order, context={'request': request})
        return Response({
            "message": f"Item status updated to {new_status} successfully",
            "order": serializer.data
        }, status=status.HTTP_200_OK)


class MarkNotificationAsReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id)

            if notification.user == request.user or getattr(request.user, 'vendor', None) == notification.vendor:
                notification.is_read = True
                notification.save()
                return Response({'message': 'Notification marked as read.'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Not authorized to update this notification.'}, status=status.HTTP_403_FORBIDDEN)

        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found.'}, status=status.HTTP_404_NOT_FOUND)


class VendorNotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        vendor = self.request.user
        return Notification.objects.filter(vendor=vendor)


class AdminUserOrderListView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return Order.objects.filter(user_id=user_id)\
            .select_related('user', 'checkout')\
            .prefetch_related('checkout__items')\
            .order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)


class MonthlyOrderStatsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        current_year = datetime.now().year

        stats = (
            Order.objects
            .filter(created_at__year=current_year)
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(
                total_orders=Count('id'),
                total_revenue=Sum('final_amount')
            )
            .order_by('month')
        )

        formatted_stats = [
            {
                "month": stat["month"].strftime("%B"),
                "total_orders": stat["total_orders"],
                "total_revenue": float(stat["total_revenue"] or 0.00)
            }
            for stat in stats
        ]

        return Response(formatted_stats)


class DailyRevenueComparisonAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        today = now().date()
        yesterday = today - timedelta(days=1)

        today_revenue = Order.objects.filter(
            created_at__date=today
        ).aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')

        yesterday_revenue = Order.objects.filter(
            created_at__date=yesterday
        ).aggregate(total=Sum('final_amount'))['total'] or Decimal('0.00')

        today_revenue = float(today_revenue)
        yesterday_revenue = float(yesterday_revenue)

        if yesterday_revenue == 0:
            percentage_change = 100.0 if today_revenue > 0 else 0.0
        else:
            percentage_change = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100

        data = {
            "today_revenue": round(today_revenue, 2),
            "yesterday_revenue": round(yesterday_revenue, 2),
            "percentage_change": round(percentage_change, 2)
        }

        return Response(data)


class OrderRevenueStatsAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get_stats(self, queryset):
        return {
            "orders": queryset.count(),
            "revenue": round(queryset.aggregate(total=Sum('final_amount'))['total'] or 0.00, 2)
        }

    def get(self, request, *args, **kwargs):
        now_time = now()
        date_param = request.query_params.get('date')

        # Base query
        all_orders = Order.objects.all()

        data = {
            "all_time": self.get_stats(all_orders),
            "last_12_months": self.get_stats(all_orders.filter(created_at__gte=now_time - timedelta(days=365))),
            "last_30_days": self.get_stats(all_orders.filter(created_at__gte=now_time - timedelta(days=30))),
            "last_7_days": self.get_stats(all_orders.filter(created_at__gte=now_time - timedelta(days=7))),
            "last_24_hours": self.get_stats(all_orders.filter(created_at__gte=now_time - timedelta(hours=24))),
        }

        # If a specific date is provided
        if date_param:
            selected_date = parse_date(date_param)
            if selected_date:
                day_orders = all_orders.filter(created_at__date=selected_date)
                data["selected_date"] = {
                    "date": selected_date,
                    "orders": day_orders.count(),
                    "revenue": round(day_orders.aggregate(total=Sum('final_amount'))['total'] or 0.00, 2)
                }
            else:
                data["selected_date"] = {"error": "Invalid date format. Use YYYY-MM-DD."}

        return Response(data)

class RevenueBySpecificDateAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        date_str = request.GET.get('date')

        if not date_str:
            return Response({"error": "Please provide a 'date' parameter in YYYY-MM-DD format."}, status=400)

        selected_date = parse_date(date_str)

        if not selected_date:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        revenue = (
            Order.objects
            .filter(created_at__date=selected_date)
            .aggregate(total=Sum('final_amount'))['total'] or 0.00
        )

        return Response({
            "date": selected_date,
            "revenue": round(revenue, 2)
        })

class ProductCountAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, *args, **kwargs):
        clothing_count = Clothing.objects.count()
        dish_count = Dish.objects.count()
        grocery_count = GroceryProducts.objects.count()
        vendor_count = Vendor.objects.count()

        total = clothing_count + dish_count + grocery_count

        return Response({
            "clothing": clothing_count,
            "dishes": dish_count,
            "grocery": grocery_count,
            "total_products": total,
            "vendors": vendor_count
        })





from deliverypartner.serializers import DeliveryBoyOrderAssignSerializer


class OrderAssignByStatusAPIView(APIView):
    permission_classes = []
    
    def get(self, request, delivery_boy_id):
        # Get status from query parameters
        order_status = request.query_params.get('status', None)
        
        # Get all OrderAssign records
        queryset = OrderAssign.objects.filter(delivery_boy=delivery_boy_id)
        
        # Filter by status if provided
        if order_status:
            # Validate if status is valid
            valid_statuses = ['ASSIGNED', 'ACCEPTED', 'PICKED', 'ON_THE_WAY', 'DELIVERED', 'RETURNED', 'REJECTED']
            
            if order_status.upper() not in valid_statuses:
                return Response(
                    {
                        'error': 'Invalid status',
                        'message': f'Status must be one of: {", ".join(valid_statuses)}'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            queryset = queryset.filter(status=order_status.upper())
        
        # Select related to optimize queries
        queryset = queryset.select_related(
            'order', 
            'delivery_boy', 
            'order__user',
            'order__checkout'
        ).prefetch_related(
            'order__user__addresses',
            'order__checkout__items__vendor'
        ).order_by('-assigned_at')
        
        # Paginate the results (optional - if you want pagination)
        # For now, returning all results
        serializer = DeliveryBoyOrderAssignSerializer(queryset, many=True)
        
        return Response(
            {
                'count': queryset.count(),
                'next': None,
                'previous': None,
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )