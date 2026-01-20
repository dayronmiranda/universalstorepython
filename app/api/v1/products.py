"""Products endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from bson import ObjectId
from typing import List, Optional

from app.database import get_database
from app.api.deps import require_product_manager, get_optional_user
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    CategoryCreate,
    CategoryResponse,
)
from app.schemas.common import SuccessResponse, PaginatedResponse
from app.utils.validators import validate_object_id

router = APIRouter()


# Helper function to convert product document to response
def product_to_response(product: dict) -> ProductResponse:
    """Convert database product document to ProductResponse"""
    return ProductResponse(
        id=str(product["_id"]),
        name=product["name"],
        description=product.get("description"),
        price=product["price"],
        sale_price=product.get("sale_price"),
        stock=product.get("stock", 0),
        reserved_stock=product.get("reserved_stock", 0),
        available_stock=max(0, product.get("stock", 0) - product.get("reserved_stock", 0)),
        image=product.get("image"),
        images=product.get("images", []),
        category=str(product["category"]) if product.get("category") else None,
        featured=product.get("featured", False),
        on_sale=product.get("on_sale", False),
        stock_status=product.get("stock_status", "instock"),
        active=product.get("active", True),
        created_at=product.get("created_at", datetime.utcnow()),
        updated_at=product.get("updated_at", datetime.utcnow()),
    )


@router.get("/products", response_model=List[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    on_sale: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    List products with optional filtering and pagination.
    Public endpoint - no authentication required.
    """
    # Build query
    query = {}

    # Non-admin users can only see active products
    if not current_user or current_user.get("role") not in ["admin", "product_manager"]:
        query["active"] = True

    if category:
        if validate_object_id(category):
            query["category"] = ObjectId(category)

    if featured is not None:
        query["featured"] = featured

    if on_sale is not None:
        query["on_sale"] = on_sale

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]

    # Calculate pagination
    skip = (page - 1) * limit

    # Fetch products
    cursor = db.products.find(query).skip(skip).limit(limit).sort("created_at", -1)
    products = await cursor.to_list(length=limit)

    return [product_to_response(p) for p in products]


@router.get("/products/search", response_model=List[ProductResponse])
async def search_products(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Search products by name or description.
    Public endpoint - no authentication required.
    """
    query = {
        "active": True,
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    }

    cursor = db.products.find(query).limit(limit)
    products = await cursor.to_list(length=limit)

    return [product_to_response(p) for p in products]


@router.get("/products/stats")
async def get_product_stats(
    current_user: dict = Depends(require_product_manager),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get product statistics (Admin only).
    """
    # Aggregate product statistics
    pipeline = [
        {
            "$facet": {
                "total": [{"$count": "count"}],
                "active": [{"$match": {"active": True}}, {"$count": "count"}],
                "out_of_stock": [{"$match": {"stock": 0}}, {"$count": "count"}],
                "low_stock": [{"$match": {"stock": {"$lte": 10, "$gt": 0}}}, {"$count": "count"}],
                "by_category": [
                    {"$match": {"active": True, "category": {"$exists": True}}},
                    {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ],
                "total_value": [
                    {"$match": {"active": True}},
                    {"$group": {"_id": None, "value": {"$sum": {"$multiply": ["$price", "$stock"]}}}}
                ]
            }
        }
    ]

    result = await db.products.aggregate(pipeline).to_list(length=1)

    if not result:
        return {
            "success": True,
            "data": {
                "total_products": 0,
                "active_products": 0,
                "out_of_stock": 0,
                "low_stock": 0,
                "total_value": 0.0,
                "by_category": {}
            }
        }

    data = result[0]

    # Format category stats
    by_category = {}
    for cat in data.get("by_category", []):
        if cat["_id"]:
            cat_doc = await db.categories.find_one({"_id": ObjectId(cat["_id"])})
            cat_name = cat_doc["name"] if cat_doc else str(cat["_id"])
            by_category[cat_name] = cat["count"]

    return {
        "success": True,
        "data": {
            "total_products": data["total"][0]["count"] if data["total"] else 0,
            "active_products": data["active"][0]["count"] if data["active"] else 0,
            "out_of_stock": data["out_of_stock"][0]["count"] if data["out_of_stock"] else 0,
            "low_stock": data["low_stock"][0]["count"] if data["low_stock"] else 0,
            "total_value": data["total_value"][0]["value"] if data["total_value"] else 0.0,
            "by_category": by_category
        }
    }


@router.get("/products/stock")
async def get_products_stock(
    product_ids: str = Query(..., description="Comma-separated product IDs"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Check stock availability for multiple products.
    Public endpoint - no authentication required.
    """
    # Parse product IDs
    id_list = [pid.strip() for pid in product_ids.split(",") if pid.strip()]

    if not id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No product IDs provided"
        )

    # Validate all IDs
    valid_ids = []
    for pid in id_list:
        if validate_object_id(pid):
            valid_ids.append(ObjectId(pid))

    if not valid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid product IDs provided"
        )

    # Get products
    cursor = db.products.find({"_id": {"$in": valid_ids}, "active": True})
    products = await cursor.to_list(length=len(valid_ids))

    # Format response
    stock_info = {}
    for product in products:
        product_id = str(product["_id"])
        stock_info[product_id] = {
            "stock": product.get("stock", 0),
            "reserved_stock": product.get("reserved_stock", 0),
            "available_stock": max(0, product.get("stock", 0) - product.get("reserved_stock", 0)),
            "stock_status": product.get("stock_status", "instock")
        }

    return {
        "success": True,
        "data": stock_info
    }


@router.get("/products/tracking")
async def get_stock_tracking(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(require_product_manager),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get stock tracking history (Admin only).
    """
    from datetime import timedelta

    start_date = datetime.utcnow() - timedelta(days=days)

    # Query stock movements/changes
    # This is a simplified version - in production you'd have a stock_movements collection
    products = await db.products.find(
        {"active": True},
        {"name": 1, "stock": 1, "reserved_stock": 1, "updated_at": 1}
    ).sort("updated_at", -1).limit(100).to_list(length=100)

    tracking_data = []
    for product in products:
        if product.get("updated_at") and product["updated_at"] >= start_date:
            tracking_data.append({
                "product_id": str(product["_id"]),
                "product_name": product.get("name"),
                "current_stock": product.get("stock", 0),
                "reserved_stock": product.get("reserved_stock", 0),
                "last_updated": product.get("updated_at")
            })

    return {
        "success": True,
        "data": {
            "period_days": days,
            "products": tracking_data
        }
    }


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Get a single product by ID.
    Public endpoint - no authentication required.
    Note: This endpoint is defined AFTER specific routes like /products/stats
    """
    if not validate_object_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID"
        )

    product = await db.products.find_one({"_id": ObjectId(product_id)})

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Non-admin users can only see active products
    if not current_user or current_user.get("role") not in ["admin", "product_manager"]:
        if not product.get("active", True):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )

    return product_to_response(product)


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_product_manager)
):
    """
    Create a new product.
    Requires product_manager or admin role.
    """
    # Validate category if provided
    if product_data.category:
        if not validate_object_id(product_data.category):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )

        category = await db.categories.find_one({"_id": ObjectId(product_data.category)})
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    # Create product document
    product_dict = product_data.model_dump(exclude_unset=True)
    product_dict["created_at"] = datetime.utcnow()
    product_dict["updated_at"] = datetime.utcnow()
    product_dict["reserved_stock"] = 0

    if product_data.category:
        product_dict["category"] = ObjectId(product_data.category)

    result = await db.products.insert_one(product_dict)

    # Update category product count
    if product_data.category:
        await db.categories.update_one(
            {"_id": ObjectId(product_data.category)},
            {"$inc": {"product_count": 1}}
        )

    # Fetch created product
    created_product = await db.products.find_one({"_id": result.inserted_id})

    return product_to_response(created_product)


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_product_manager)
):
    """
    Update a product.
    Requires product_manager or admin role.
    """
    if not validate_object_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID"
        )

    # Check if product exists
    existing_product = await db.products.find_one({"_id": ObjectId(product_id)})
    if not existing_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Validate category if provided
    if product_data.category is not None:
        if not validate_object_id(product_data.category):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )

        category = await db.categories.find_one({"_id": ObjectId(product_data.category)})
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )

    # Build update data
    update_dict = product_data.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.utcnow()

    if product_data.category is not None:
        update_dict["category"] = ObjectId(product_data.category)

    # Update product
    await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": update_dict}
    )

    # Update category counts if category changed
    if product_data.category is not None and str(existing_product.get("category")) != product_data.category:
        # Decrease old category count
        if existing_product.get("category"):
            await db.categories.update_one(
                {"_id": existing_product["category"]},
                {"$inc": {"product_count": -1}}
            )
        # Increase new category count
        await db.categories.update_one(
            {"_id": ObjectId(product_data.category)},
            {"$inc": {"product_count": 1}}
        )

    # Fetch updated product
    updated_product = await db.products.find_one({"_id": ObjectId(product_id)})

    return product_to_response(updated_product)


@router.delete("/products/{product_id}", response_model=SuccessResponse)
async def delete_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_product_manager)
):
    """
    Delete a product (soft delete by setting active=False).
    Requires product_manager or admin role.
    """
    if not validate_object_id(product_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID"
        )

    product = await db.products.find_one({"_id": ObjectId(product_id)})

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Soft delete
    await db.products.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"active": False, "updated_at": datetime.utcnow()}}
    )

    # Update category product count
    if product.get("category"):
        await db.categories.update_one(
            {"_id": product["category"]},
            {"$inc": {"product_count": -1}}
        )

    return SuccessResponse(
        success=True,
        message="Product deleted successfully"
    )


# Category endpoints

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    List all active categories.
    Public endpoint - no authentication required.
    """
    cursor = db.categories.find({"active": True}).sort("name", 1)
    categories = await cursor.to_list(length=None)

    return [
        CategoryResponse(
            id=str(cat["_id"]),
            name=cat["name"],
            slug=cat["slug"],
            description=cat.get("description"),
            image=cat.get("image"),
            parent_id=str(cat["parent_id"]) if cat.get("parent_id") else None,
            active=cat.get("active", True),
            product_count=cat.get("product_count", 0),
            created_at=cat.get("created_at", datetime.utcnow()),
            updated_at=cat.get("updated_at", datetime.utcnow()),
        )
        for cat in categories
    ]


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_product_manager)
):
    """
    Create a new category.
    Requires product_manager or admin role.
    """
    # Check if slug already exists
    existing = await db.categories.find_one({"slug": category_data.slug})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )

    # Validate parent_id if provided
    if category_data.parent_id:
        if not validate_object_id(category_data.parent_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent category ID"
            )

        parent = await db.categories.find_one({"_id": ObjectId(category_data.parent_id)})
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )

    # Create category document
    category_dict = category_data.model_dump(exclude_unset=True)
    category_dict["created_at"] = datetime.utcnow()
    category_dict["updated_at"] = datetime.utcnow()
    category_dict["product_count"] = 0

    if category_data.parent_id:
        category_dict["parent_id"] = ObjectId(category_data.parent_id)

    result = await db.categories.insert_one(category_dict)

    # Fetch created category
    created_category = await db.categories.find_one({"_id": result.inserted_id})

    return CategoryResponse(
        id=str(created_category["_id"]),
        name=created_category["name"],
        slug=created_category["slug"],
        description=created_category.get("description"),
        image=created_category.get("image"),
        parent_id=str(created_category["parent_id"]) if created_category.get("parent_id") else None,
        active=created_category.get("active", True),
        product_count=created_category.get("product_count", 0),
        created_at=created_category.get("created_at", datetime.utcnow()),
        updated_at=created_category.get("updated_at", datetime.utcnow()),
    )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_data: CategoryCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: dict = Depends(require_product_manager)
):
    """
    Update a category.
    Requires product_manager or admin role.
    """
    if not validate_object_id(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID"
        )

    category = await db.categories.find_one({"_id": ObjectId(category_id)})

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if new slug conflicts with another category
    if category_data.slug != category.get("slug"):
        existing = await db.categories.find_one({
            "slug": category_data.slug,
            "_id": {"$ne": ObjectId(category_id)}
        })
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this slug already exists"
            )

    # Validate parent_id if provided
    if category_data.parent_id:
        if not validate_object_id(category_data.parent_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid parent category ID"
            )

        # Prevent self-parenting
        if category_data.parent_id == category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category cannot be its own parent"
            )

        parent = await db.categories.find_one({"_id": ObjectId(category_data.parent_id)})
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent category not found"
            )

    # Build update document
    update_data = category_data.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()

    if category_data.parent_id:
        update_data["parent_id"] = ObjectId(category_data.parent_id)

    # Update category
    result = await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )

    # Fetch updated category
    updated_category = await db.categories.find_one({"_id": ObjectId(category_id)})

    return CategoryResponse(
        id=str(updated_category["_id"]),
        name=updated_category["name"],
        slug=updated_category["slug"],
        description=updated_category.get("description"),
        image=updated_category.get("image"),
        parent_id=str(updated_category["parent_id"]) if updated_category.get("parent_id") else None,
        active=updated_category.get("active", True),
        product_count=updated_category.get("product_count", 0),
        created_at=updated_category.get("created_at", datetime.utcnow()),
        updated_at=updated_category.get("updated_at", datetime.utcnow()),
    )


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get a specific category by ID.
    Public endpoint - no authentication required.
    """
    if not validate_object_id(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID"
        )

    category = await db.categories.find_one({"_id": ObjectId(category_id)})

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Only return active categories for public
    if not category.get("active", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    return CategoryResponse(
        id=str(category["_id"]),
        name=category["name"],
        slug=category["slug"],
        description=category.get("description"),
        image=category.get("image"),
        parent_id=str(category["parent_id"]) if category.get("parent_id") else None,
        active=category.get("active", True),
        product_count=category.get("product_count", 0),
        created_at=category.get("created_at", datetime.utcnow()),
        updated_at=category.get("updated_at", datetime.utcnow()),
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: str,
    current_user: dict = Depends(require_product_manager),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Delete a category (Product Manager or Admin only).
    This will soft-delete by setting active=false.
    """
    if not validate_object_id(category_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID"
        )

    category = await db.categories.find_one({"_id": ObjectId(category_id)})

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Check if category has products
    product_count = await db.products.count_documents({"category": category_id, "active": True})
    if product_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete category with {product_count} active products"
        )

    # Soft delete by setting active to False
    result = await db.categories.update_one(
        {"_id": ObjectId(category_id)},
        {"$set": {"active": False, "updated_at": datetime.utcnow()}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )

    return {
        "success": True,
        "message": "Category deleted successfully"
    }


