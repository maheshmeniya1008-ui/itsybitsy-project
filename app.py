import os
from typing import Optional, List, Dict, Any, Union
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Header, Path, Depends
from pydantic import BaseModel, Field

from database import get_connection, test_connection

load_dotenv()

app = FastAPI(
    title="Itsybitsy Product Data API",
    version="1.0.0"
)


# -------------------------------
# Product Request Model
# -------------------------------
class ProductCreate(BaseModel):
    source_product_id: str = Field(
        min_length=1, max_length=100
    )
    product_name: str = Field(
        min_length=1, max_length=255
    )
    upc: Optional[str] = Field(
        default=None, max_length=50
    )
    brand: Optional[str] = Field(
        default=None, max_length=150
    )
    category: Optional[str] = Field(
        default=None, max_length=150
    )
    pack_size: Optional[str] = Field(
        default=None, max_length=100
    )
    variation: Optional[str] = Field(
        default=None, max_length=150
    )


class ProductUpdate(BaseModel):
    product_name: str = Field(
        min_length=1, max_length=255
    )
    upc: Optional[str] = Field(
        default=None, max_length=50
    )
    brand: Optional[str] = Field(
        default=None, max_length=150
    )
    category: Optional[str] = Field(
        default=None, max_length=150
    )
    pack_size: Optional[str] = Field(
        default=None, max_length=100
    )
    variation: Optional[str] = Field(
        default=None, max_length=150
    )



# Add these classes below your existing ProductUpdate class

class PriceInput(BaseModel):
    regular_price: Optional[float] = Field(default=None, ge=0)
    promotional_price: Optional[float] = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    unit_price: Optional[float] = Field(default=None, ge=0)
    displayed_discount: Optional[str] = Field(
        default=None, max_length=50
    )


class AvailabilityInput(BaseModel):
    retailer: str = Field(
        default="Itsybitsy.in", max_length=150
    )
    city: Optional[str] = Field(default=None, max_length=100)
    state_name: Optional[str] = Field(default=None, max_length=100)
    zip_code: Optional[str] = Field(default=None, max_length=10)
    in_stock: Optional[bool] = None
    availability_label: Optional[str] = Field(
        default=None, max_length=100
    )
    pickup_available: Optional[bool] = None
    delivery_available: Optional[bool] = None
    in_store_available: Optional[bool] = None



# -------------------------------
# Home API
# -------------------------------
@app.get("/")
def home():
    return {
        "message": "Itsybitsy Product Data API is running"
    }


# -------------------------------
# Database Health API
# -------------------------------
@app.get("/health/db")
def database_health():
    try:
        database_name = test_connection()
        return {
            "status": "success",
            "database": database_name,
            "message": "SQL Server connected successfully"
        }
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {error}"
        )


# -------------------------------
# Create Product API
# -------------------------------
@app.post("/products", status_code=201)
def create_product(product: ProductCreate):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.Products (
                SourceProductID,
                UPC,
                ProductName,
                Brand,
                Category,
                PackSize,
                Variation
            )
            OUTPUT INSERTED.ProductID
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            product.source_product_id,
            product.upc,
            product.product_name,
            product.brand,
            product.category,
            product.pack_size,
            product.variation
        )

        product_id = cursor.fetchone()[0]
        connection.commit()

        return {
            "status": "success",
            "message": "Product created successfully",
            "product_id": product_id
        }

    except Exception as error:
        if connection:
            connection.rollback()

        message = str(error)

        if "2601" in message or "2627" in message:
            raise HTTPException(
                status_code=409,
                detail="This source_product_id already exists."
            )

        raise HTTPException(
            status_code=500,
            detail=f"Could not create product: {message}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Get All Products API
# -------------------------------
@app.get("/products")
def get_products():
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                ProductID,
                SourceProductID,
                UPC,
                ProductName,
                Brand,
                Category,
                PackSize,
                Variation,
                CreatedAt,
                UpdatedAt
            FROM dbo.Products
            ORDER BY ProductID DESC
            """
        )

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        products = [
            dict(zip(columns, row))
            for row in rows
        ]

        return {
            "status": "success",
            "count": len(products),
            "products": products
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve products: {error}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Get Product By ID API
# -------------------------------
@app.get("/products/{product_id}")
def get_product(product_id: int):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                ProductID,
                SourceProductID,
                UPC,
                ProductName,
                Brand,
                Category,
                PackSize,
                Variation,
                CreatedAt,
                UpdatedAt
            FROM dbo.Products
            WHERE ProductID = ?
            """,
            product_id
        )

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        columns = [column[0] for column in cursor.description]

        return {
            "status": "success",
            "product": dict(zip(columns, row))
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve product: {error}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Update Product API
# -------------------------------
@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    product: ProductUpdate
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.Products
            SET
                ProductName = ?,
                UPC = ?,
                Brand = ?,
                Category = ?,
                PackSize = ?,
                Variation = ?,
                UpdatedAt = SYSUTCDATETIME()
            WHERE ProductID = ?
            """,
            product.product_name,
            product.upc,
            product.brand,
            product.category,
            product.pack_size,
            product.variation,
            product_id
        )

        if cursor.rowcount == 0:
            connection.rollback()
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        connection.commit()

        return {
            "status": "success",
            "message": "Product updated successfully",
            "product_id": product_id
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not update product: {error}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Create or Update Product Price
# -------------------------------
@app.put("/products/{product_id}/price")
def save_product_price(
    product_id: int,
    price: PriceInput
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT ProductID
            FROM dbo.Products
            WHERE ProductID = ?
            """,
            product_id
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        cursor.execute(
            """
            UPDATE dbo.ProductPrices
            SET
                RegularPrice = ?,
                PromotionalPrice = ?,
                Currency = ?,
                UnitPrice = ?,
                DisplayedDiscount = ?,
                UpdatedAt = SYSUTCDATETIME()
            WHERE ProductID = ?
            """,
            price.regular_price,
            price.promotional_price,
            price.currency.upper(),
            price.unit_price,
            price.displayed_discount,
            product_id
        )

        if cursor.rowcount == 0:
            cursor.execute(
                """
                INSERT INTO dbo.ProductPrices (
                    ProductID,
                    RegularPrice,
                    PromotionalPrice,
                    Currency,
                    UnitPrice,
                    DisplayedDiscount
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                product_id,
                price.regular_price,
                price.promotional_price,
                price.currency.upper(),
                price.unit_price,
                price.displayed_discount
            )

        connection.commit()

        return {
            "status": "success",
            "message": "Product price saved successfully",
            "product_id": product_id
        }

    except HTTPException:
        if connection:
            connection.rollback()
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not save price: {error}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Get Current Product Price
# -------------------------------
@app.get("/products/{product_id}/price")
def get_product_price(product_id: int):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                p.ProductID,
                p.ProductName,
                pr.RegularPrice,
                pr.PromotionalPrice,
                pr.Currency,
                pr.UnitPrice,
                pr.DisplayedDiscount,
                pr.UpdatedAt
            FROM dbo.Products AS p
            LEFT JOIN dbo.ProductPrices AS pr
                ON p.ProductID = pr.ProductID
            WHERE p.ProductID = ?
            """,
            product_id
        )

        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        columns = [column[0] for column in cursor.description]

        return {
            "status": "success",
            "price": dict(zip(columns, row))
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve price: {error}"
        )

    finally:
        if connection:
            connection.close()



# -------------------------------
# Create Availability Record
# -------------------------------
@app.post("/products/{product_id}/availability", status_code=201)
def create_availability(
    product_id: int,
    availability: AvailabilityInput
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.ProductAvailability (
                ProductID,
                Retailer,
                City,
                StateName,
                ZipCode,
                InStock,
                AvailabilityLabel,
                PickupAvailable,
                DeliveryAvailable,
                InStoreAvailable
            )
            OUTPUT INSERTED.AvailabilityID
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            product_id,
            availability.retailer,
            availability.city,
            availability.state_name,
            availability.zip_code,
            availability.in_stock,
            availability.availability_label,
            availability.pickup_available,
            availability.delivery_available,
            availability.in_store_available
        )

        availability_id = cursor.fetchone()[0]
        connection.commit()

        return {
            "status": "success",
            "message": "Availability created successfully",
            "availability_id": availability_id,
            "product_id": product_id
        }

    except Exception as error:
        if connection:
            connection.rollback()

        message = str(error)

        if "547" in message:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        raise HTTPException(
            status_code=500,
            detail=f"Could not create availability: {message}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Get Product Availability
# -------------------------------
@app.get("/products/{product_id}/availability")
def get_product_availability(product_id: int):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                AvailabilityID,
                ProductID,
                Retailer,
                City,
                StateName,
                ZipCode,
                InStock,
                AvailabilityLabel,
                PickupAvailable,
                DeliveryAvailable,
                InStoreAvailable,
                UpdatedAt
            FROM dbo.ProductAvailability
            WHERE ProductID = ?
            ORDER BY AvailabilityID DESC
            """,
            product_id
        )

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        return {
            "status": "success",
            "count": len(rows),
            "availability": [
                dict(zip(columns, row))
                for row in rows
            ]
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve availability: {error}"
        )

    finally:
        if connection:
            connection.close()


# -------------------------------
# Update Availability Record
# -------------------------------
@app.put("/availability/{availability_id}")
def update_availability(
    availability_id: int,
    availability: AvailabilityInput
):
    connection = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.ProductAvailability
            SET
                Retailer = ?,
                City = ?,
                StateName = ?,
                ZipCode = ?,
                InStock = ?,
                AvailabilityLabel = ?,
                PickupAvailable = ?,
                DeliveryAvailable = ?,
                InStoreAvailable = ?,
                UpdatedAt = SYSUTCDATETIME()
            WHERE AvailabilityID = ?
            """,
            availability.retailer,
            availability.city,
            availability.state_name,
            availability.zip_code,
            availability.in_stock,
            availability.availability_label,
            availability.pickup_available,
            availability.delivery_available,
            availability.in_store_available,
            availability_id
        )

        if cursor.rowcount == 0:
            connection.rollback()
            raise HTTPException(
                status_code=404,
                detail="Availability record not found"
            )

        connection.commit()

        return {
            "status": "success",
            "message": "Availability updated successfully",
            "availability_id": availability_id
        }

    except HTTPException:
        raise

    except Exception as error:
        if connection:
            connection.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Could not update availability: {error}"
        )

    finally:
        if connection:
            connection.close()


# ===============================================================
# Security Token Verification & Category Product APIs
# ===============================================================

def verify_api_token(token: Optional[str] = None):
    """
    Validate the secret security key / token provided by the client.
    Supports master token from .env and dynamic client API keys from dbo.ApiKeys table.
    """
    if not token or not token.strip():
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "message": "Invalid or missing security token / key.",
                "hint": "Please provide a valid API key in header 'X-API-Key', query '?token=', or URL path."
            }
        )

    expected_token = os.getenv("API_SECURITY_KEY", "itsybitsy_secret_token_2026").strip()
    provided = token.strip()

    # 1. Master key check
    if provided == expected_token:
        return {"role": "admin", "client": "MasterAdmin"}

    # 2. Check dynamic database API keys (Feature #6)
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ClientName, Role, IsActive 
            FROM dbo.ApiKeys 
            WHERE ApiKey = ?
            """,
            provided
        )
        row = cursor.fetchone()
        conn.close()
        if row and row[2]:  # If found and IsActive == 1
            return {"role": row[1], "client": row[0]}
    except Exception:
        pass

    raise HTTPException(
        status_code=401,
        detail={
            "status": "error",
            "message": "Invalid or unauthorized API key.",
            "hint": "Ensure your API key is active or contact the administrator."
        }
    )


def query_products_by_category(category_slug: str) -> List[Dict[str, Any]]:
    """
    Query products from SQL Server matching the given category slug or name.
    Matches across Category column, Collection URL slug, or product title.
    Returns JSON format identical to FakeStoreAPI products list.
    """
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cleaned_cat = category_slug.strip().lower()
        cat_spaces = cleaned_cat.replace("-", " ")
        cat_like = f"%{cleaned_cat}%"
        cat_spaces_like = f"%{cat_spaces}%"

        cursor.execute(
            """
            SELECT
                p.ProductID,
                p.SourceProductID,
                p.ProductName,
                p.Brand,
                p.Category,
                p.PackSize,
                p.Variation,
                pr.RegularPrice,
                pr.PromotionalPrice,
                pr.Currency,
                pa.InStock,
                pa.AvailabilityLabel,
                cr.SourceURL,
                p.CreatedAt,
                p.UpdatedAt
            FROM dbo.Products p
            LEFT JOIN dbo.ProductPrices pr
                ON p.ProductID = pr.ProductID
            LEFT JOIN (
                SELECT
                    ProductID,
                    InStock,
                    AvailabilityLabel,
                    ROW_NUMBER() OVER(
                        PARTITION BY ProductID
                        ORDER BY AvailabilityID DESC
                    ) as rn
                FROM dbo.ProductAvailability
            ) pa
                ON p.ProductID = pa.ProductID AND pa.rn = 1
            LEFT JOIN (
                SELECT
                    ProductID,
                    MIN(SourceURL) as SourceURL
                FROM dbo.CollectionRecords
                GROUP BY ProductID
            ) cr
                ON p.ProductID = cr.ProductID
            WHERE
                LOWER(ISNULL(p.Category, '')) = ?
                OR LOWER(REPLACE(ISNULL(p.Category, ''), ' ', '-')) = ?
                OR LOWER(ISNULL(p.Category, '')) LIKE ?
                OR LOWER(ISNULL(p.Category, '')) LIKE ?
                OR LOWER(ISNULL(cr.SourceURL, '')) LIKE ?
                OR LOWER(p.ProductName) LIKE ?
            ORDER BY p.ProductID DESC
            """,
            cleaned_cat,
            cleaned_cat,
            cat_like,
            cat_spaces_like,
            cat_like,
            f"%{cleaned_cat}%"
        )

        rows = cursor.fetchall()
        products_list = []

        for row in rows:
            (
                product_id,
                source_id,
                product_name,
                brand,
                category,
                pack_size,
                variation,
                regular_price,
                promotional_price,
                currency,
                in_stock,
                availability_label,
                source_url,
                created_at,
                updated_at,
            ) = row

            # Active/effective price
            active_price = (
                float(promotional_price)
                if promotional_price is not None
                else (float(regular_price) if regular_price is not None else None)
            )

            products_list.append({
                "id": product_id,
                "title": product_name,
                "price": active_price,
                "regular_price": float(regular_price) if regular_price is not None else None,
                "promotional_price": float(promotional_price) if promotional_price is not None else None,
                "currency": currency or "INR",
                "category": (category or cleaned_cat).lower().replace(" ", "-"),
                "brand": brand,
                "pack_size": pack_size,
                "variation": variation,
                "in_stock": in_stock,
                "availability": availability_label or ("In Stock" if in_stock else "Out of Stock"),
                "source_product_id": source_id,
                "url": source_url or f"https://itsybitsy.in/products/{source_id}",
            })

        return products_list

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve category products: {error}"
        )
    finally:
        if connection:
            connection.close()


def query_all_categories() -> List[str]:
    """Retrieve distinct category slugs."""
    connection = None
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT DISTINCT Category
            FROM dbo.Products
            WHERE Category IS NOT NULL AND LTRIM(RTRIM(Category)) <> ''
            ORDER BY Category
            """
        )
        rows = cursor.fetchall()
        categories = []
        for row in rows:
            cat_slug = row[0].strip().lower().replace(" ", "-")
            if cat_slug not in categories:
                categories.append(cat_slug)
        return categories
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not retrieve categories: {error}"
        )
    finally:
        if connection:
            connection.close()


# ---------------------------------------------------------------
# 1. User Suggested URL Pattern:
# https://<host>/itsy_bitsyAPI/<security_key>/products/category/<category_name>
# ---------------------------------------------------------------
@app.get(
    "/itsy_bitsyAPI/{security_key}/products/category/{category_slug}",
    summary="Get products by category with path security token",
    response_description="JSON list of category products (FakeStoreAPI style)"
)
def get_products_by_category_with_token(
    security_key: str = Path(..., description="Secret security token / key"),
    category_slug: str = Path(..., description="Category slug, e.g. mdf-collection"),
    envelope: bool = Query(
        False,
        description="If true, wraps output in an envelope object with count"
    )
):
    verify_api_token(security_key)
    products = query_products_by_category(category_slug)

    if envelope:
        return {
            "status": "success",
            "category": category_slug,
            "count": len(products),
            "products": products
        }

    return products


# ---------------------------------------------------------------
# 2. Get All Available Categories with Path Token:
# https://<host>/itsy_bitsyAPI/<security_key>/products/categories
# ---------------------------------------------------------------
@app.get(
    "/itsy_bitsyAPI/{security_key}/products/categories",
    summary="Get all available product categories",
    response_description="JSON list of category names"
)
def get_categories_with_token(
    security_key: str = Path(..., description="Secret security token / key")
):
    verify_api_token(security_key)
    return query_all_categories()


# ---------------------------------------------------------------
# 3. Get All Products with Path Token:
# https://<host>/itsy_bitsyAPI/<security_key>/products
# ---------------------------------------------------------------
@app.get(
    "/itsy_bitsyAPI/{security_key}/products",
    summary="Get all products with path security token"
)
def get_all_products_with_token(
    security_key: str = Path(..., description="Secret security token / key")
):
    verify_api_token(security_key)
    # Using '%' to return all products
    return query_products_by_category("%")


# ---------------------------------------------------------------
# 4. Standard Query/Header Token Endpoints:
# https://<host>/products/category/<category_slug>?token=<security_key>
# ---------------------------------------------------------------
@app.get(
    "/products/category/{category_slug}",
    summary="Get products by category with query param or header token"
)
@app.get(
    "/itsy_bitsyAPI/products/category/{category_slug}",
    summary="Get products by category with query param or header token (itsy_bitsyAPI prefix)"
)
def get_products_by_category_standard(
    category_slug: str = Path(..., description="Category slug, e.g. mdf-collection"),
    token: Optional[str] = Query(None, description="Security token / key"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    envelope: bool = Query(False, description="If true, wraps output in an envelope")
):
    provided_token = token or x_api_key
    verify_api_token(provided_token)
    products = query_products_by_category(category_slug)

    if envelope:
        return {
            "status": "success",
            "category": category_slug,
            "count": len(products),
            "products": products
        }

    return products


# ---------------------------------------------------------------
# 5. Price & Availability History Endpoint (Feature #1)
# ---------------------------------------------------------------
@app.get(
    "/products/{product_id}/history",
    summary="Get price and stock change history for a specific product"
)
def get_product_history(
    product_id: int = Path(..., description="Product ID"),
    token: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    provided_token = token or x_api_key
    if provided_token:
        verify_api_token(provided_token)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT HistoryID, ProductID, JobID, ChangeType, OldData, NewData, ChangedAt
            FROM dbo.ProductHistory
            WHERE ProductID = ?
            ORDER BY ChangedAt DESC
            """,
            product_id
        )
        rows = cursor.fetchall()
        history = []
        for r in rows:
            history.append({
                "history_id": r[0],
                "product_id": r[1],
                "job_id": r[2],
                "change_type": r[3],
                "old_data": r[4],
                "new_data": r[5],
                "changed_at": str(r[6]) if r[6] else None
            })
        return {"product_id": product_id, "total_changes": len(history), "history": history}
    finally:
        connection.close()


@app.get(
    "/products/recent-price-drops",
    summary="Get products with recent price drops or changes"
)
def get_recent_price_drops(
    limit: int = Query(20, ge=1, le=100),
    token: Optional[str] = Query(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
):
    provided_token = token or x_api_key
    if provided_token:
        verify_api_token(provided_token)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT TOP ({limit})
                h.HistoryID, h.ProductID, p.ProductName, p.Brand, p.Category,
                h.ChangeType, h.OldData, h.NewData, h.ChangedAt
            FROM dbo.ProductHistory h
            JOIN dbo.Products p ON h.ProductID = p.ProductID
            WHERE h.ChangeType = 'PRICE_CHANGE'
            ORDER BY h.ChangedAt DESC
            """
        )
        rows = cursor.fetchall()
        alerts = []
        for r in rows:
            alerts.append({
                "history_id": r[0],
                "product_id": r[1],
                "product_name": r[2],
                "brand": r[3],
                "category": r[4],
                "change_type": r[5],
                "old_data": r[6],
                "new_data": r[7],
                "changed_at": str(r[8]) if r[8] else None
            })
        return {"count": len(alerts), "price_alerts": alerts}
    finally:
        connection.close()


# ---------------------------------------------------------------
# 6. Smart Analytics & AI Insights Endpoint (Feature #4 & #5)
# ---------------------------------------------------------------
@app.get(
    "/analytics/insights",
    summary="Calculate smart statistics, KPIs and top discount recommendations"
)
def get_analytics_insights():
    connection = get_connection()
    try:
        cursor = connection.cursor()
        # Aggregate stats
        cursor.execute(
            """
            SELECT 
                COUNT(p.ProductID) AS total_products,
                AVG(pr.RegularPrice) AS avg_regular_price,
                AVG(pr.PromotionalPrice) AS avg_promotional_price,
                MAX(pr.RegularPrice - pr.PromotionalPrice) AS max_discount_amount,
                SUM(CASE WHEN pa.InStock = 1 THEN 1 ELSE 0 END) AS in_stock_count,
                SUM(CASE WHEN pa.InStock = 0 THEN 1 ELSE 0 END) AS out_of_stock_count
            FROM dbo.Products p
            LEFT JOIN dbo.ProductPrices pr ON p.ProductID = pr.ProductID
            LEFT JOIN dbo.ProductAvailability pa ON p.ProductID = pa.ProductID
            """
        )
        row = cursor.fetchone()
        
        # Top 10 Best Deals / High Discount
        cursor.execute(
            """
            SELECT TOP 10 
                p.ProductID, p.ProductName, p.Brand, p.Category,
                pr.RegularPrice, pr.PromotionalPrice,
                ROUND(((pr.RegularPrice - pr.PromotionalPrice) / NULLIF(pr.RegularPrice, 0)) * 100, 2) AS DiscountPct,
                pa.AvailabilityLabel
            FROM dbo.Products p
            JOIN dbo.ProductPrices pr ON p.ProductID = pr.ProductID
            LEFT JOIN dbo.ProductAvailability pa ON p.ProductID = pa.ProductID
            WHERE pr.RegularPrice > pr.PromotionalPrice AND pr.RegularPrice > 0
            ORDER BY DiscountPct DESC
            """
        )
        top_deals = []
        for d in cursor.fetchall():
            top_deals.append({
                "product_id": d[0],
                "product_name": d[1],
                "brand": d[2],
                "category": d[3],
                "regular_price": float(d[4]) if d[4] else None,
                "promotional_price": float(d[5]) if d[5] else None,
                "discount_percentage": float(d[6]) if d[6] else 0.0,
                "availability": d[7]
            })

        return {
            "kpis": {
                "total_products": row[0] or 0,
                "avg_regular_price": round(float(row[1]), 2) if row[1] else 0,
                "avg_promotional_price": round(float(row[2]), 2) if row[2] else 0,
                "max_discount_savings": float(row[3]) if row[3] else 0,
                "in_stock_count": row[4] or 0,
                "out_of_stock_count": row[5] or 0
            },
            "top_deals": top_deals
        }
    finally:
        connection.close()


# ---------------------------------------------------------------
# 7. Background Scraper Trigger Endpoint (Feature #3)
# ---------------------------------------------------------------
import subprocess

@app.post(
    "/scraper/trigger",
    summary="Trigger the background scraper job on-demand"
)
def trigger_scraper_job(
    max_products: int = Query(5, ge=1, le=50, description="Max products to scrape in this run")
):
    try:
        # Run daily_mdf_job.py asynchronously in the background
        process = subprocess.Popen(
            ["python", "daily_mdf_job.py", "--max", str(max_products)],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            shell=False
        )
        return {
            "status": "success",
            "message": f"Scraping job launched in background for up to {max_products} products.",
            "pid": process.pid
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------
# 8. Multi-Tenant API Key Management (Feature #6)
# ---------------------------------------------------------------
import secrets

class ApiKeyCreate(BaseModel):
    client_name: str = Field(min_length=2, max_length=100)
    role: str = Field(default="client", max_length=50)

@app.post("/admin/api-keys", summary="Generate a new Client API Key")
def create_api_key(
    data: ApiKeyCreate,
    admin_token: str = Query(..., description="Master security token required")
):
    expected_token = os.getenv("API_SECURITY_KEY", "itsybitsy_secret_token_2026").strip()
    if admin_token.strip() != expected_token:
        raise HTTPException(status_code=403, detail="Only Master Admin can create API keys.")

    new_key = f"itsy_{secrets.token_hex(16)}"
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.ApiKeys (ClientName, ApiKey, Role, IsActive)
            OUTPUT INSERTED.KeyID
            VALUES (?, ?, ?, 1)
            """,
            data.client_name, new_key, data.role
        )
        key_id = cur.fetchone()[0]
        conn.commit()
        return {
            "status": "success",
            "key_id": key_id,
            "client_name": data.client_name,
            "api_key": new_key,
            "role": data.role
        }
    finally:
        conn.close()

@app.get("/admin/api-keys", summary="List all active client API keys")
def list_api_keys(admin_token: str = Query(...)):
    expected_token = os.getenv("API_SECURITY_KEY", "itsybitsy_secret_token_2026").strip()
    if admin_token.strip() != expected_token:
        raise HTTPException(status_code=403, detail="Unauthorized")

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT KeyID, ClientName, ApiKey, Role, IsActive, CreatedAt FROM dbo.ApiKeys ORDER BY KeyID DESC")
        keys = []
        for r in cur.fetchall():
            keys.append({
                "key_id": r[0],
                "client_name": r[1],
                "api_key": r[2],
                "role": r[3],
                "is_active": bool(r[4]),
                "created_at": str(r[5])
            })
        return {"keys": keys}
    finally:
        conn.close()


