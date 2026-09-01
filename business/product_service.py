"""
Product and Inventory Service.
Handles multi-field live search, CRUD, category/brand lookups, and stock metrics.
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from data.db import DatabaseManager, get_db

logger = logging.getLogger(__name__)


class ProductService:
    """
    Business service for Product Catalog, Live Multi-Criteria Search, and Inventory Queries.
    """

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or get_db()

    def search_products(
        self,
        query: str = "",
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        stock_status: Optional[str] = None,
        limit: int = 250,
    ) -> List[Dict[str, Any]]:
        """
        Search products with live partial matching on Product Name, Brand, Model, and Category.
        Supports multiple space-delimited search tokens (e.g. 'Samsung 55' or 'Apple 15').
        """
        base_query = """
            SELECT 
                p.id,
                p.name,
                COALESCE(p.model, '') AS model,
                p.category_id,
                c.name AS category_name,
                p.brand_id,
                b.name AS brand_name,
                p.current_stock,
                p.min_stock_alert,
                p.warranty_period_months,
                p.is_active,
                p.created_at,
                p.updated_at
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            WHERE p.is_deleted = 0
        """
        params: List[Any] = []
        conditions = []

        # Multi-term token search across name, model, brand, category
        clean_query = query.strip()
        if clean_query:
            tokens = [t.strip() for t in clean_query.split() if t.strip()]
            for token in tokens:
                pattern = f"%{token}%"
                token_sql = """
                    (
                        p.name LIKE ? OR
                        COALESCE(p.model, '') LIKE ? OR
                        COALESCE(b.name, '') LIKE ? OR
                        COALESCE(c.name, '') LIKE ?
                    )
                """
                conditions.append(token_sql)
                params.extend([pattern, pattern, pattern, pattern])

        if category_id is not None and category_id > 0:
            conditions.append("p.category_id = ?")
            params.append(category_id)

        if brand_id is not None and brand_id > 0:
            conditions.append("p.brand_id = ?")
            params.append(brand_id)

        if stock_status == "low_stock":
            conditions.append("p.current_stock <= p.min_stock_alert")
        elif stock_status == "out_of_stock":
            conditions.append("p.current_stock <= 0")
        elif stock_status == "in_stock":
            conditions.append("p.current_stock > p.min_stock_alert")

        if conditions:
            base_query += " AND " + " AND ".join(conditions)

        base_query += " ORDER BY p.name ASC LIMIT ?"
        params.append(limit)

        try:
            rows = self.db.execute_query(base_query, tuple(params))
            results = []
            for r in rows:
                p_dict = dict(r)
                current_stock = p_dict["current_stock"]
                min_alert = p_dict["min_stock_alert"]
                
                # Computed visual stock status
                if current_stock <= 0:
                    status_label = "Out of Stock"
                    status_code = "out"
                elif current_stock <= min_alert:
                    status_label = "Low Stock"
                    status_code = "low"
                else:
                    status_label = "In Stock"
                    status_code = "ok"

                p_dict["status_label"] = status_label
                p_dict["status_code"] = status_code
                p_dict["brand_name"] = p_dict["brand_name"] or "—"
                p_dict["model"] = p_dict["model"] or "—"
                p_dict["category_name"] = p_dict["category_name"] or "General"
                results.append(p_dict)
            return results
        except Exception as e:
            logger.error(f"Error executing product search: {e}", exc_info=True)
            return []

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single product with category and brand metadata."""
        query = """
            SELECT 
                p.id,
                p.name,
                COALESCE(p.model, '') AS model,
                p.category_id,
                c.name AS category_name,
                p.brand_id,
                b.name AS brand_name,
                p.current_stock,
                p.min_stock_alert,
                p.warranty_period_months,
                p.is_active,
                p.created_at,
                p.updated_at
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            WHERE p.id = ? AND p.is_deleted = 0
        """
        row = self.db.execute_one(query, (product_id,))
        return dict(row) if row else None

    def get_all_categories(self) -> List[Dict[str, Any]]:
        """Fetch active product categories."""
        query = "SELECT id, name, description FROM categories WHERE is_active = 1 ORDER BY name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(query)]
        except Exception as e:
            logger.error(f"Error fetching categories: {e}")
            return []

    def get_all_categories_with_counts(self, query: str = "") -> List[Dict[str, Any]]:
        """Fetch categories with active product count."""
        sql = """
            SELECT 
                c.id,
                c.name,
                c.description,
                c.is_active,
                c.created_at,
                c.updated_at,
                COUNT(p.id) AS product_count
            FROM categories c
            LEFT JOIN products p ON p.category_id = c.id AND p.is_deleted = 0
            WHERE c.is_active = 1
        """
        params = []
        if query.strip():
            sql += " AND (c.name LIKE ? OR COALESCE(c.description, '') LIKE ?)"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat])
        sql += " GROUP BY c.id ORDER BY c.name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching categories with counts: {e}")
            return []

    def create_category(self, name: str, description: Optional[str] = None) -> Tuple[bool, Optional[int], str]:
        """Create a new product category."""
        name = name.strip()
        description = description.strip() if description else None
        if not name:
            return False, None, "Category name is required."

        existing = self.db.execute_one("SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND is_active = 1;", (name,))
        if existing:
            return False, None, f"A category named '{name}' already exists."

        sql = "INSERT INTO categories (name, description, is_active) VALUES (?, ?, 1);"
        try:
            cat_id = self.db.execute_update(sql, (name, description))
            logger.info(f"Created category '{name}' with ID {cat_id}")
            return True, cat_id, f"Category '{name}' created successfully."
        except Exception as e:
            logger.error(f"Failed to create category: {e}", exc_info=True)
            return False, None, f"Database error: {e}"

    def update_category(self, category_id: int, name: str, description: Optional[str] = None) -> Tuple[bool, str]:
        """Update an existing category."""
        name = name.strip()
        description = description.strip() if description else None
        if not name:
            return False, "Category name is required."

        existing = self.db.execute_one(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND id != ? AND is_active = 1;",
            (name, category_id),
        )
        if existing:
            return False, f"Another category named '{name}' already exists."

        sql = """
            UPDATE categories
            SET name = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """
        try:
            self.db.execute_update(sql, (name, description, category_id))
            logger.info(f"Updated category #{category_id} ('{name}')")
            return True, f"Category '{name}' updated successfully."
        except Exception as e:
            logger.error(f"Failed to update category: {e}", exc_info=True)
            return False, f"Database error: {e}"

    def delete_category(self, category_id: int) -> Tuple[bool, str]:
        """
        Delete a category.
        Enforces business rule: Deleting a category that is still used by existing products
        is blocked with a clear message to prevent orphaned products.
        """
        cat = self.db.execute_one("SELECT name FROM categories WHERE id = ?;", (category_id,))
        cat_name = cat["name"] if cat else f"#{category_id}"

        p_row = self.db.execute_one(
            "SELECT COUNT(*) AS count FROM products WHERE category_id = ? AND is_deleted = 0;",
            (category_id,),
        )
        assigned_count = p_row["count"] if p_row else 0
        if assigned_count > 0:
            return (
                False,
                f"Cannot delete category '{cat_name}': It is currently assigned to {assigned_count} active product(s).\n\n"
                f"To delete this category, first reassign or remove the associated products in the Product Catalog.",
            )

        try:
            self.db.execute_update("DELETE FROM categories WHERE id = ?;", (category_id,))
            logger.info(f"Deleted category '{cat_name}' (ID {category_id})")
            return True, f"Category '{cat_name}' deleted successfully."
        except Exception as e:
            logger.error(f"Failed to delete category: {e}", exc_info=True)
            return False, f"Database error: {e}"

    def get_all_brands(self) -> List[Dict[str, Any]]:
        """Fetch active brands."""
        query = "SELECT id, name, description, website FROM brands WHERE is_active = 1 ORDER BY name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(query)]
        except Exception as e:
            logger.error(f"Error fetching brands: {e}")
            return []

    def get_all_brands_with_counts(self, query: str = "") -> List[Dict[str, Any]]:
        """Fetch brands with active product count."""
        sql = """
            SELECT 
                b.id,
                b.name,
                b.description,
                b.website,
                b.is_active,
                b.created_at,
                b.updated_at,
                COUNT(p.id) AS product_count
            FROM brands b
            LEFT JOIN products p ON p.brand_id = b.id AND p.is_deleted = 0
            WHERE b.is_active = 1
        """
        params = []
        if query.strip():
            sql += " AND (b.name LIKE ? OR COALESCE(b.description, '') LIKE ? OR COALESCE(b.website, '') LIKE ?)"
            pat = f"%{query.strip()}%"
            params.extend([pat, pat, pat])
        sql += " GROUP BY b.id ORDER BY b.name ASC;"
        try:
            return [dict(r) for r in self.db.execute_query(sql, tuple(params))]
        except Exception as e:
            logger.error(f"Error fetching brands with counts: {e}")
            return []

    def create_brand(
        self, name: str, description: Optional[str] = None, website: Optional[str] = None
    ) -> Tuple[bool, Optional[int], str]:
        """Create a new brand."""
        name = name.strip()
        description = description.strip() if description else None
        website = website.strip() if website else None
        if not name:
            return False, None, "Brand name is required."

        existing = self.db.execute_one("SELECT id FROM brands WHERE name = ? COLLATE NOCASE AND is_active = 1;", (name,))
        if existing:
            return False, None, f"A brand named '{name}' already exists."

        sql = "INSERT INTO brands (name, description, website, is_active) VALUES (?, ?, ?, 1);"
        try:
            brand_id = self.db.execute_update(sql, (name, description, website))
            logger.info(f"Created brand '{name}' with ID {brand_id}")
            return True, brand_id, f"Brand '{name}' created successfully."
        except Exception as e:
            logger.error(f"Failed to create brand: {e}", exc_info=True)
            return False, None, f"Database error: {e}"

    def update_brand(
        self, brand_id: int, name: str, description: Optional[str] = None, website: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Update an existing brand."""
        name = name.strip()
        description = description.strip() if description else None
        website = website.strip() if website else None
        if not name:
            return False, "Brand name is required."

        existing = self.db.execute_one(
            "SELECT id FROM brands WHERE name = ? COLLATE NOCASE AND id != ? AND is_active = 1;",
            (name, brand_id),
        )
        if existing:
            return False, f"Another brand named '{name}' already exists."

        sql = """
            UPDATE brands
            SET name = ?, description = ?, website = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """
        try:
            self.db.execute_update(sql, (name, description, website, brand_id))
            logger.info(f"Updated brand #{brand_id} ('{name}')")
            return True, f"Brand '{name}' updated successfully."
        except Exception as e:
            logger.error(f"Failed to update brand: {e}", exc_info=True)
            return False, f"Database error: {e}"

    def delete_brand(self, brand_id: int) -> Tuple[bool, str]:
        """
        Delete a brand.
        Enforces business rule: Deleting a brand that is still used by existing products
        is blocked with a clear message to prevent orphaned products.
        """
        brand = self.db.execute_one("SELECT name FROM brands WHERE id = ?;", (brand_id,))
        brand_name = brand["name"] if brand else f"#{brand_id}"

        p_row = self.db.execute_one(
            "SELECT COUNT(*) AS count FROM products WHERE brand_id = ? AND is_deleted = 0;",
            (brand_id,),
        )
        assigned_count = p_row["count"] if p_row else 0
        if assigned_count > 0:
            return (
                False,
                f"Cannot delete brand '{brand_name}': It is currently assigned to {assigned_count} active product(s).\n\n"
                f"To delete this brand, first reassign or remove the associated products in the Product Catalog.",
            )

        try:
            self.db.execute_update("DELETE FROM brands WHERE id = ?;", (brand_id,))
            logger.info(f"Deleted brand '{brand_name}' (ID {brand_id})")
            return True, f"Brand '{brand_name}' deleted successfully."
        except Exception as e:
            logger.error(f"Failed to delete brand: {e}", exc_info=True)
            return False, f"Database error: {e}"


    def get_inventory_metrics(self) -> Dict[str, Any]:
        """Fetch dashboard/inventory metrics."""
        query = """
            SELECT 
                COUNT(*) AS total_count,
                COALESCE(SUM(current_stock), 0) AS total_units,
                COALESCE(SUM(current_stock * cost_price), 0.0) AS total_inventory_cost,
                COALESCE(SUM(current_stock * selling_price), 0.0) AS total_inventory_value,
                SUM(CASE WHEN current_stock <= 0 THEN 1 ELSE 0 END) AS out_of_stock_count,
                SUM(CASE WHEN current_stock > 0 AND current_stock <= min_stock_alert THEN 1 ELSE 0 END) AS low_stock_count
            FROM products
            WHERE is_deleted = 0 AND is_active = 1;
        """
        try:
            row = self.db.execute_one(query)
            if row:
                return dict(row)
        except Exception as e:
            logger.error(f"Error computing inventory metrics: {e}")
        return {
            "total_count": 0,
            "total_units": 0,
            "total_inventory_cost": 0.0,
            "total_inventory_value": 0.0,
            "out_of_stock_count": 0,
            "low_stock_count": 0,
        }

    def create_product(
        self,
        name: str,
        brand_id: Optional[int] = None,
        model: Optional[str] = None,
        category_id: Optional[int] = None,
        min_stock_alert: int = 5,
        warranty_period_months: int = 0,
    ) -> Tuple[bool, Optional[int], str]:
        """
        Create a new product record.
        Fields: Product Name, Brand, Model, Category, Minimum Stock Level, Warranty Duration.
        Current stock is initialized to 0 (system-managed, read-only).
        """
        name = name.strip()
        model = model.strip() if model else None

        if not name:
            return False, None, "Product Name is required."
        if min_stock_alert < 0:
            return False, None, "Minimum Stock Level cannot be negative."
        if warranty_period_months < 0:
            return False, None, "Warranty Duration cannot be negative."

        import uuid
        internal_sku = f"PRD-{uuid.uuid4().hex[:10].upper()}"

        insert_sql = """
            INSERT INTO products (
                sku, name, model, category_id, brand_id,
                current_stock, min_stock_alert, warranty_period_months,
                cost_price, selling_price, is_active, is_deleted
            ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, 0.0, 0.0, 1, 0);
        """
        try:
            new_id = self.db.execute_update(
                insert_sql,
                (
                    internal_sku,
                    name,
                    model,
                    category_id if category_id and category_id > 0 else None,
                    brand_id if brand_id and brand_id > 0 else None,
                    min_stock_alert,
                    warranty_period_months,
                ),
            )
            logger.info(f"Created product '{name}' (Model: {model}) with ID {new_id}")
            return True, new_id, f"Product '{name}' created successfully."
        except Exception as e:
            logger.error(f"Failed to create product: {e}", exc_info=True)
            return False, None, f"Database error: {e}"

    def update_product(
        self,
        product_id: int,
        name: str,
        brand_id: Optional[int] = None,
        model: Optional[str] = None,
        category_id: Optional[int] = None,
        min_stock_alert: int = 5,
        warranty_period_months: int = 0,
    ) -> Tuple[bool, str]:
        """
        Update an existing product record.
        Current Stock is system-managed and not modified directly here.
        """
        name = name.strip()
        model = model.strip() if model else None

        if not name:
            return False, "Product Name is required."
        if min_stock_alert < 0:
            return False, "Minimum Stock Level cannot be negative."
        if warranty_period_months < 0:
            return False, "Warranty Duration cannot be negative."

        update_sql = """
            UPDATE products SET
                name = ?,
                model = ?,
                category_id = ?,
                brand_id = ?,
                min_stock_alert = ?,
                warranty_period_months = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
        """
        try:
            self.db.execute_update(
                update_sql,
                (
                    name,
                    model,
                    category_id if category_id and category_id > 0 else None,
                    brand_id if brand_id and brand_id > 0 else None,
                    min_stock_alert,
                    warranty_period_months,
                    product_id,
                ),
            )
            logger.info(f"Updated product #{product_id} ('{name}')")
            return True, f"Product '{name}' updated successfully."
        except Exception as e:
            logger.error(f"Failed to update product #{product_id}: {e}", exc_info=True)
            return False, f"Database error: {e}"

    def delete_product(self, product_id: int) -> Tuple[bool, str]:
        """
        Soft delete a product (is_deleted = 1, is_active = 0).
        Historical purchase/sale records referencing this product remain fully intact.
        """
        try:
            prod = self.db.execute_one("SELECT name FROM products WHERE id = ?;", (product_id,))
            prod_name = prod["name"] if prod else f"#{product_id}"

            self.db.execute_update(
                "UPDATE products SET is_deleted = 1, is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (product_id,),
            )
            logger.info(f"Soft-deleted product #{product_id} ('{prod_name}')")
            return True, f"Product '{prod_name}' deleted successfully (archived)."
        except Exception as e:
            logger.error(f"Failed to delete product #{product_id}: {e}")
            return False, f"Database error: {e}"

