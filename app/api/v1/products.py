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


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Get a single product by ID.
    Public endpoint - no authentication required.
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
