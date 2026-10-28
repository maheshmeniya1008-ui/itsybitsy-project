import argparse
from scraper import extract_product, PRODUCT_URL
from database import get_connection
import sys

def save_product_to_database(data):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # 1. Start a collection job
        cursor.execute(
            """
            INSERT INTO dbo.CollectionJobs (
                Status, StartedAt
            )
            OUTPUT INSERTED.JobID
            VALUES (N'Running', SYSUTCDATETIME())
            """
        )
        job_id = cursor.fetchone()[0]

        source_id = data["source_product_id"]

        # Do not save an unverified brand value.
        brand = data.get("brand")
        if brand and brand.startswith("S1 Z6 WEB"):
            brand = None

        # 2. Insert or update product identity
        cursor.execute(
            """
            SELECT ProductID
            FROM dbo.Products
            WHERE SourceProductID = ?
            """,
            source_id
        )
        existing = cursor.fetchone()

        category = data.get("category")

        if existing:
            product_id = existing[0]

            cursor.execute(
                """
                UPDATE dbo.Products
                SET
                    ProductName = ?,
                    Brand = COALESCE(?, Brand),
                    Category = COALESCE(?, Category),
                    UpdatedAt = SYSUTCDATETIME()
                WHERE ProductID = ?
                """,
                data["product_name"],
                brand,
                category,
                product_id
            )
        else:
            cursor.execute(
                """
                INSERT INTO dbo.Products (
                    SourceProductID,
                    ProductName,
                    Brand,
                    Category
                )
                OUTPUT INSERTED.ProductID
                VALUES (?, ?, ?, ?)
                """,
                source_id,
                data["product_name"],
                brand,
                category
            )
            product_id = cursor.fetchone()[0]

        # 3. Check and record Price Change in dbo.ProductHistory
        cursor.execute(
            """
            SELECT TOP 1 RegularPrice, PromotionalPrice, Currency
            FROM dbo.ProductPrices
            WHERE ProductID = ?
            """,
            product_id
        )
        old_price_row = cursor.fetchone()
        new_reg = data.get("regular_price")
        new_promo = data.get("promotional_price")
        new_curr = data.get("currency") or "INR"

        if old_price_row:
            old_reg, old_promo, old_curr = old_price_row[0], old_price_row[1], old_price_row[2]
            # Check if prices changed
            if (old_reg != new_reg) or (old_promo != new_promo):
                import json
                old_json = json.dumps({"regular_price": float(old_reg) if old_reg is not None else None, "promotional_price": float(old_promo) if old_promo is not None else None, "currency": old_curr})
                new_json = json.dumps({"regular_price": float(new_reg) if new_reg is not None else None, "promotional_price": float(new_promo) if new_promo is not None else None, "currency": new_curr})
                cursor.execute(
                    """
                    INSERT INTO dbo.ProductHistory (
                        ProductID, JobID, ChangeType, OldData, NewData, ChangedAt
                    )
                    VALUES (?, ?, 'PRICE_CHANGE', ?, ?, SYSUTCDATETIME())
                    """,
                    product_id, job_id, old_json, new_json
                )

            cursor.execute(
                """
                UPDATE dbo.ProductPrices
                SET
                    RegularPrice = ?,
                    PromotionalPrice = ?,
                    Currency = ?,
                    UpdatedAt = SYSUTCDATETIME()
                WHERE ProductID = ?
                """,
                new_reg, new_promo, new_curr, product_id
            )
        else:
            cursor.execute(
                """
                INSERT INTO dbo.ProductPrices (
                    ProductID,
                    RegularPrice,
                    PromotionalPrice,
                    Currency
                )
                VALUES (?, ?, ?, ?)
                """,
                product_id, new_reg, new_promo, new_curr
            )

        # 4. Convert website availability to a boolean
        availability_text = str(
            data.get("availability", "Unknown")
        ).lower()

        if availability_text in ("instock", "instockavailable"):
            in_stock = True
            availability_label = "In Stock"
        elif availability_text in (
            "outofstock", "soldout", "out_of_stock"
        ):
            in_stock = False
            availability_label = "Out of Stock"
        else:
            in_stock = None
            availability_label = "Unknown"

        # 5. Insert or update availability and check for change
        retailer = "Itsybitsy.in"

        cursor.execute(
            """
            SELECT TOP 1 AvailabilityID, InStock, AvailabilityLabel
            FROM dbo.ProductAvailability
            WHERE ProductID = ?
              AND Retailer = ?
              AND ISNULL(City, '') = ''
              AND ISNULL(ZipCode, '') = ''
            ORDER BY AvailabilityID DESC
            """,
            product_id,
            retailer
        )
        availability_row = cursor.fetchone()

        if availability_row:
            old_instock, old_label = availability_row[1], availability_row[2]
            if (old_instock != in_stock) or (old_label != availability_label):
                import json
                old_json = json.dumps({"in_stock": old_instock, "availability_label": old_label})
                new_json = json.dumps({"in_stock": in_stock, "availability_label": availability_label})
                cursor.execute(
                    """
                    INSERT INTO dbo.ProductHistory (
                        ProductID, JobID, ChangeType, OldData, NewData, ChangedAt
                    )
                    VALUES (?, ?, 'AVAILABILITY_CHANGE', ?, ?, SYSUTCDATETIME())
                    """,
                    product_id, job_id, old_json, new_json
                )

            cursor.execute(
                """
                UPDATE dbo.ProductAvailability
                SET
                    InStock = ?,
                    AvailabilityLabel = ?,
                    UpdatedAt = SYSUTCDATETIME()
                WHERE AvailabilityID = ?
                """,
                in_stock,
                availability_label,
                availability_row[0]
            )
        else:
            cursor.execute(
                """
                INSERT INTO dbo.ProductAvailability (
                    ProductID,
                    Retailer,
                    InStock,
                    AvailabilityLabel
                )
                VALUES (?, ?, ?, ?)
                """,
                product_id,
                retailer,
                in_stock,
                availability_label
            )

        # 6. Record collection source and timestamp
        cursor.execute(
            """
            INSERT INTO dbo.CollectionRecords (
                ProductID,
                JobID,
                SourceURL,
                ValidationStatus,
                DataFreshness,
                Notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            product_id,
            job_id,
            data["product_url"],
            "Valid" if data.get("product_name") else "Partial",
            "Current",
            "Collected using scraper.py"
        )

        # 7. Mark job complete
        cursor.execute(
            """
            UPDATE dbo.CollectionJobs
            SET
                Status = N'Completed',
                CompletedAt = SYSUTCDATETIME(),
                ProductsProcessed = 1
            WHERE JobID = ?
            """,
            job_id
        )

        connection.commit()

        return {
            "status": "success",
            "job_id": job_id,
            "product_id": product_id,
            "source_product_id": source_id,
            "message": "Product data saved to SQL Server"
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    try:
        print("Collecting product data...")
        # product_data = extract_product(PRODUCT_URL)
        # Keep this import at the top of save_product.py
        # from scraper import extract_product, PRODUCT_URL
        #product_data = extract_product(PRODUCT_URL, refresh="--refresh" in sys.argv)

        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--url",
            default=PRODUCT_URL,
            help="Itsybitsy product URL"
        )

        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Fetch a fresh product page instead of using cache"
        )

        args = parser.parse_args()

        product_data = extract_product(args.url, refresh=args.refresh)

        print("\n--- DATA TO SAVE ---")
        print(product_data)

        result = save_product_to_database(product_data)

        print("\n--- DATABASE SAVE RESULT ---")
        print(result)

    except Exception as error:
        print("Collection or database save failed:", error)
        sys.exit(1)