"""Collect product attributes for display using a visitor."""

from functools import singledispatchmethod

import pandas as pd

from fixedincomelib.product.product_interfaces import Product, ProductVisitor
from fixedincomelib.product.linear_products import (
    ProductFixedAccruedCashflow, ProductOvernightIndexCashflow,
)

__all__ = ["ProductDisplayVisitor"]


class ProductDisplayVisitor(ProductVisitor):
    def __init__(self) -> None:
        self.nvps_ = []

    @singledispatchmethod
    def visit(self, product: Product):
        raise NotImplementedError(f"No display visitor for {product.product_type}")

    def display(self) -> pd.DataFrame:
        return pd.DataFrame(self.nvps_, columns=["Name", "Value"])

    def _common_items(self, product: Product):
        self.nvps_ = [
            ["Product Type", product.product_type],
            ["Notional", product.notional],
            ["Currency", product.currency.value_str],
            ["Long Or Short", product.long_or_short.to_string().upper()],
        ]

    @visit.register
    def _(self, product: ProductFixedAccruedCashflow):
        self._common_items(product)
        self.nvps_ += [
            ["Effective Date", product.effective_date.ISO()],
            ["Termination Date", product.termination_date.ISO()],
            ["Accrual Basis", product.accrual_basis.value_str],
            ["Payment Date", product.payment_date.ISO()],
            ["Business Day Convention", product.business_day_convention.value_str],
            ["Holiday Convention", product.holiday_convention.value_str],
        ]

    @visit.register
    def _(self, product: ProductOvernightIndexCashflow):
        self._common_items(product)
        self.nvps_ += [
            ["Effective Date", product.effective_date.ISO()],
            ["Termination Date", product.termination_date.ISO()],
            ["ON Index", product.on_index_str_],
            ["Compounding Method", product.compounding_method.to_string().upper()],
            ["Spread", product.spread],
            ["Payment Date", product.payment_date.ISO()],
        ]
