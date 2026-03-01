"""MCP tools for digital product and access grant management."""

import logging
from typing import Optional

from mcp.server.fastmcp import FastMCP

from articulate_mcp.context_helper import get_connection_info
from articulate_mcp.product_manager import ProductManager
from articulate_mcp.email_service import send_access_token_email

logger = logging.getLogger("articulate-mcp")


def register(mcp: FastMCP) -> None:
    """Register product and access grant MCP tools."""

    @mcp.tool()
    async def create_product(
        name: str,
        price_cents: int,
        description: str = "",
        content_ids: Optional[list[int]] = None,
        file_path: Optional[str] = None,
        file_name: Optional[str] = None,
        access_duration_days: Optional[int] = None,
        download_limit: Optional[int] = None,
        currency: str = "usd",
        context=None,
    ) -> dict:
        """Create a new digital product for sale.

        Args:
            name: Display name for the product.
            price_cents: Price in the smallest currency unit (e.g. cents for USD).
            description: Optional product description shown to customers.
            content_ids: Optional list of WordPress post/page IDs this product
                grants access to.
            file_path: Optional path or URL to a downloadable file.
            file_name: Optional original filename for the download.
            access_duration_days: Optional number of days access lasts after
                purchase. None means permanent access.
            download_limit: Optional maximum number of downloads allowed per
                grant. None means unlimited.
            currency: Three-letter ISO currency code (default: "usd").
            context: MCP context for authentication.

        Returns:
            Dict containing the created product with all fields including
            the generated id, created_at timestamp, and is_active status.
        """
        _, user_id = get_connection_info(context)

        product = await ProductManager.create_product(
            name=name,
            price_cents=price_cents,
            created_by=user_id,
            currency=currency,
            description=description,
            content_ids=content_ids,
            file_path=file_path,
            file_name=file_name,
            access_duration_days=access_duration_days,
            download_limit=download_limit,
        )

        logger.info("User %d created product %d via MCP", user_id, product["id"])
        return product

    @mcp.tool()
    async def list_products(
        active_only: bool = True,
        context=None,
    ) -> list[dict]:
        """List digital products owned by the current user.

        Args:
            active_only: If True (default), only return active products.
                Set to False to include deactivated products.
            context: MCP context for authentication.

        Returns:
            List of product dicts ordered by creation date descending.
            Each dict includes id, name, price_cents, currency, description,
            content_ids, is_active, and timestamps.
        """
        _, user_id = get_connection_info(context)

        products = await ProductManager.list_products(
            created_by=user_id,
            active_only=active_only,
        )
        return products

    @mcp.tool()
    async def get_product(
        product_id: int,
        context=None,
    ) -> dict:
        """Get a digital product by its ID.

        Args:
            product_id: The unique identifier of the product.
            context: MCP context for authentication.

        Returns:
            Dict containing the product details including id, name,
            price_cents, currency, description, content_ids, file_path,
            file_name, access_duration_days, download_limit, is_active,
            and timestamps. Returns an error dict if not found.
        """
        _, user_id = get_connection_info(context)

        product = await ProductManager.get_product(product_id)
        if product is None:
            return {"error": f"Product {product_id} not found"}
        return product

    @mcp.tool()
    async def update_product(
        product_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price_cents: Optional[int] = None,
        content_ids: Optional[list[int]] = None,
        is_active: Optional[bool] = None,
        context=None,
    ) -> dict:
        """Update fields on an existing digital product.

        Only the fields you provide will be updated; omitted fields remain
        unchanged.

        Args:
            product_id: The unique identifier of the product to update.
            name: New display name for the product.
            description: New product description.
            price_cents: New price in smallest currency unit.
            content_ids: New list of WordPress post/page IDs for access.
            is_active: Set to False to deactivate the product, True to
                reactivate it.
            context: MCP context for authentication.

        Returns:
            Dict containing the updated product, or an error dict if the
            product was not found.
        """
        _, user_id = get_connection_info(context)

        kwargs = {}
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        if price_cents is not None:
            kwargs["price_cents"] = price_cents
        if content_ids is not None:
            kwargs["content_ids"] = content_ids
        if is_active is not None:
            kwargs["is_active"] = is_active

        product = await ProductManager.update_product(product_id, **kwargs)
        if product is None:
            return {"error": f"Product {product_id} not found"}

        logger.info("User %d updated product %d via MCP", user_id, product_id)
        return product

    @mcp.tool()
    async def list_access_grants(
        product_id: Optional[int] = None,
        customer_email: Optional[str] = None,
        context=None,
    ) -> list[dict]:
        """List access grants filtered by product or customer email.

        You must provide at least one of product_id or customer_email.

        Args:
            product_id: Filter grants by this product ID.
            customer_email: Filter grants by the customer's email address.
            context: MCP context for authentication.

        Returns:
            List of access grant dicts ordered by creation date descending.
            Each dict includes id, product_id, customer_email, customer_name,
            access_token, amount_paid, currency, download_count,
            download_limit, expires_at, revoked_at, and timestamps.
            Returns an error dict if neither filter is provided.
        """
        _, user_id = get_connection_info(context)

        if product_id is None and customer_email is None:
            return [{"error": "Provide at least one of product_id or customer_email"}]

        grants = []
        if product_id is not None:
            grants = await ProductManager.list_grants_for_product(product_id)
        elif customer_email is not None:
            grants = await ProductManager.list_grants_for_customer(customer_email)

        return grants

    @mcp.tool()
    async def grant_access(
        product_id: int,
        customer_email: str,
        customer_name: str = "",
        context=None,
    ) -> dict:
        """Manually grant free access to a product for a customer.

        Creates an access grant with amount_paid=0 and sends an email
        to the customer with their access token.

        Args:
            product_id: The product to grant access to.
            customer_email: The customer's email address.
            customer_name: Optional name of the customer.
            context: MCP context for authentication.

        Returns:
            Dict containing the created access grant including the
            generated access_token, or an error dict if the product
            is not found.
        """
        _, user_id = get_connection_info(context)

        # Verify the product exists
        product = await ProductManager.get_product(product_id)
        if product is None:
            return {"error": f"Product {product_id} not found"}

        grant = await ProductManager.create_access_grant(
            product_id=product_id,
            customer_email=customer_email,
            customer_name=customer_name or None,
            amount_paid=0,
            currency=product.get("currency", "usd"),
        )

        # Send the access token email
        send_access_token_email(
            to=customer_email,
            name=customer_name or customer_email,
            product_name=product["name"],
            access_token=grant["access_token"],
        )

        logger.info(
            "User %d manually granted access to product %d for %s via MCP",
            user_id, product_id, customer_email,
        )
        return grant

    @mcp.tool()
    async def revoke_access(
        grant_id: int,
        context=None,
    ) -> dict:
        """Revoke an access grant, preventing further use of its token.

        This marks the grant as revoked with a timestamp. The customer
        will no longer be able to access content or download files using
        the associated token.

        Args:
            grant_id: The unique identifier of the access grant to revoke.
            context: MCP context for authentication.

        Returns:
            Dict confirming the revocation with the grant_id and status.
        """
        _, user_id = get_connection_info(context)

        await ProductManager.revoke_access(grant_id)

        logger.info("User %d revoked access grant %d via MCP", user_id, grant_id)
        return {"grant_id": grant_id, "status": "revoked"}
