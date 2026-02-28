"""
Deal domain models.

Contains main business entities for deals and deal items.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Any
from typing_extensions import Annotated
from uuid import UUID, uuid5
import logging

from pydantic import (
    BaseModel,
    Field,
    computed_field,
    field_validator,
    field_serializer,
    model_validator,
    ConfigDict,
    StringConstraints,
    PrivateAttr,
)

from ..value_objects import Money, Money5, SignedMoney, SignedMoney5, Period, HashKey, Status

THRESHOLD_DECIMAL = Decimal("0.01")

logger = logging.getLogger(__name__)


class DealItem(BaseModel):
    """Deal item representing a single product position within a deal.

    This entity is a child record that stores product-level operational and financial data.
    """

    # Уникальные идентификаторы  
    explicit_id: Optional[UUID] = Field(
        None, description="Поле для явного задания ID (переопределяет детерминированный)"
        )
    deal_id: Optional[UUID] = Field(
        None, description="ID родительской сделки"
        )
    # Основная информация
    product_name: str = Field(
        ..., min_length=1, max_length=500, description="Наименование товара")
    supplier_name: Optional[str] = Field(
        None, max_length=100, description="Название поставщика"
    )
    client_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(..., description="Название клиента")
    period_month: str = Field(
           ..., max_length=10, description="Название месяца"
    )
    period_year: str = Field(
           ..., max_length=4, description="Год"
    )
    seller: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(..., description="Продавец")
    invoice_info: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(..., description="Информация о счете")
    deal_key: Optional[str]= Field(
           None, max_length=255, description="Ключ сделки (заполняется из Deal)"
    )

    # Количественные показатели
    quantity: Optional[Decimal] = Field(None, ge=0, description="Количество товара")
    purchase_price: Optional[Money5] = Field(
        None,
        alias='purchase_price_amount',
        description="Цена закупки (5 знаков)",
    )
    sale_price: Optional[Money] = Field(
        None,
        alias='sale_price_amount',
        description="Цена продажи",
    )

    # Расчетные показатели
    revenue: Optional[Money] = Field(
        None,
        alias='revenue_amount',
        description="Выручка от позиции",
    )
    margin: Optional[SignedMoney5] = Field(
        None,
        alias='margin_amount',
        description="Маржа по позиции (5 знаков)",
    )
    cost: Optional[Money] = Field(
        None,
        alias='cost_amount',
        description="Стоимость закупки",
    )

    # Операционная информация
    pickup_date: Optional[str] = Field(None, description="Дата забора товара у поставщика")
    position_number: int = Field(..., ge=1, description="Номер позиции товара в сделке")

    # Метаданные
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    @computed_field
    def id(self) -> UUID:
        """Return deterministic UUID based on stable subset of fields.

        Priority is given to `explicit_id` when provided; otherwise a UUIDv5 is
        derived from `position_number`, `product_name`, and `deal_key`.

        Returns:
            UUID: Stable identifier for the deal item.
        """
        if self.explicit_id is not None:
            return self.explicit_id
            
        # Фиксированный namespace для всех позиций
        namespace = UUID('650e8400-e29b-41d4-a716-446655440000')
        # Используем тот же алгоритм что и для hash_key но для ID
        id_data = {
            "position_number": str(self.position_number),
            "product_name": self.product_name,     
            "deal_key": self.deal_key if self.deal_key else "",
        }
        # Создаем стабильную строку из всех полей
        id_string = "|".join(f"{k}:{v}" for k, v in sorted(id_data.items()))
        return uuid5(namespace, id_string)
    
    def set_id(self, value: UUID) -> None:
        """Set explicit identifier.

        Args:
            value: UUID to set as explicit identifier (used in tests/migrations).
        """
        self.explicit_id = value
        
    
    @computed_field
    def hash_key(self) -> HashKey:
        """Compute lightweight hash key used for change detection.

        Includes identity-related and mutable fields to detect meaningful changes:
        deal_key, position_number, product_name, supplier_name, quantity, prices,
        and pickup_date.

        Returns:
            HashKey: Hash of important fields.
        """
        data = {
            "deal_key": self.deal_key if self.deal_key else None,
            "position_number": str(self.position_number),
            "product_name": self.product_name,
            "supplier_name": self.supplier_name if self.supplier_name else None,
            "quantity": str(self.quantity) if self.quantity is not None else None,
            "purchase_price": str(self.purchase_price.amount) if self.purchase_price else None,
            "sale_price": str(self.sale_price.amount) if self.sale_price else None,
            "pickup_date": self.pickup_date if self.pickup_date else None,
        }
        return HashKey.from_dict(data)

    def get_full_hash_key(self, deal_key: str) -> HashKey:
        """Hash key for item uniqueness including deal_key and all financial fields.

        Includes ALL fields for complete uniqueness:
        - position_number, product_name, supplier_name, pickup_date
        - quantity, purchase_price, sale_price
        - revenue, margin, cost
        - deal_key

        Args:
            deal_key: Parent deal key.

        Returns:
            HashKey considering all item fields.
        """
        data = {
            "position_number": str(self.position_number) if self.position_number else "1",
            "product_name": self.product_name,
            "supplier_name": self.supplier_name or "",
            "pickup_date": self.pickup_date or "",
            "quantity": str(self.quantity) if self.quantity else "",
            "purchase_price": str(self.purchase_price.amount) if self.purchase_price else "",
            "sale_price": str(self.sale_price.amount) if self.sale_price else "",
            "revenue": str(self.revenue.amount) if self.revenue else "",
            "margin": str(self.margin.amount) if self.margin else "",
            "cost": str(self.cost.amount) if self.cost else "",
            "deal_key": deal_key,
        }
        return HashKey.from_dict(data)

    @field_validator("supplier_name", mode="before")
    @classmethod
    def validate_supplier_name(cls, v: str) -> str:
        """Validate and normalize supplier name.

        Args:
            v: Raw supplier name.

        Returns:
            str: Trimmed supplier name.
        """
        return v.strip() if isinstance(v, str) else v

    @field_validator('purchase_price', mode='before')
    @classmethod
    def _money5_from_scalar_or_dict(cls, v):
        """Normalize Money5-like input.

        Accepts:
        - None
        - scalar amounts like '15.50000', 15.50000, Decimal('15.50000')
        - dicts like {'amount': '15.50000'} or {'amount': Decimal(...)}
        - an existing Money5 or Money instance

        Args:
            v: Value to normalize.

        Returns:
            Money5 | None: Normalized Money5 or None.
        """
        if v is None:
            return None
        if isinstance(v, Money5):
            return v
        if isinstance(v, Money):
            # Convert Money to Money5 preserving precision
            return Money5(amount=v.amount)
        if isinstance(v, dict):
            amt = v.get('amount')
            if amt is None:
                return None
            return Money5(amount=Decimal(str(amt)))
        return Money5(amount=Decimal(str(v)))

    @field_validator('sale_price', 'revenue', 'cost', mode='before')
    @classmethod
    def _money_from_scalar_or_dict(cls, v):
        """Normalize Money-like input.

        Accepts:
        - None
        - scalar amounts like '15.50', 15.50, Decimal('15.50')
        - dicts like {'amount': '15.50'} or {'amount': Decimal(...)}
        - an existing Money instance

        Args:
            v: Value to normalize.

        Returns:
            Money | None: Normalized Money or None.
        """
        if v is None:
            return None
        if isinstance(v, Money):
            return v
        if isinstance(v, dict):
            amt = v.get('amount')
            if amt is None:
                return None
            return Money(amount=Decimal(str(amt)))
        return Money(amount=Decimal(str(v)))

    
    @field_validator('margin', mode='before')
    @classmethod
    def _signed_money5_from_scalar_or_dict(cls, v):
        """Normalize SignedMoney5-like input.

        Accepts None, dict with 'amount', scalars, SignedMoney5, or SignedMoney.

        Args:
            v: Value to normalize.

        Returns:
            SignedMoney5 | None: Normalized SignedMoney5 or None.
        """
        if v is None:
            return None
        if isinstance(v, SignedMoney5):
            return v
        if isinstance(v, SignedMoney):
            # Convert SignedMoney to SignedMoney5 preserving precision
            return SignedMoney5(amount=v.amount)
        if isinstance(v, dict):
            amt = v.get('amount')
            if amt is None:
                return None
            return SignedMoney5(amount=Decimal(str(amt)))
        return SignedMoney5(amount=Decimal(str(v)))

    @field_validator(
    "client_name", "seller", "invoice_info", "product_name",
    mode="before"
    )
    @classmethod
    def _strip_and_require_nonempty(cls, v: str) -> str:
        """Ensure non-empty string and trim whitespace.

        Args:
            v: Input value.

        Returns:
            str: Trimmed non-empty string.

        Raises:
            ValueError: If value is empty.
        """
        if not v:
            raise ValueError("Значение не может быть пустой строкой")
        return v.strip() if isinstance(v, str) else v
       

    @field_validator("period_month", mode="before")
    @classmethod
    def _normalize_period_month(cls, v: str) -> str:
        """Normalize period month using Period.normalize_month."""
        return Period.normalize_month(v)

    @field_validator("period_year", mode="before")
    @classmethod
    def _normalize_period_year(cls, v: str) -> str:
        """Normalize period year using Period.normalize_year."""
        return Period.normalize_year(v)

    
    @model_validator(mode='after')
    def auto_calculate_fields(self) -> 'DealItem':
        """Auto-calculate missing derived fields.

        Calculates revenue, cost, and margin when enough inputs are present.
        Updates `updated_at` only if at least one field was computed.

        Returns:
            DealItem: Self.
        """
        fields_calculated = False
        
        # Рассчитываем выручку (количество * цена продажи)
        if (
            self.revenue is None and self.quantity is not None and self.sale_price is not None
        ):
            self.revenue = Money(amount=self.quantity * self.sale_price.amount)
            fields_calculated = True

        # Рассчитываем стоимость закупки (количество * цена закупки)
        if (
            self.cost is None
            and self.quantity is not None
            and self.purchase_price is not None
        ):
            self.cost = Money(amount=self.quantity * self.purchase_price.amount)
            fields_calculated = True

        # Рассчитываем маржу (выручка - стоимость закупки)
        if (
            self.margin is None and self.revenue is not None and self.cost is not None
        ):
            self.margin = SignedMoney5(amount=self.revenue.amount - self.cost.amount)
            fields_calculated = True

        # Обновляем время только если были произведены вычисления
        if fields_calculated:
            self.updated_at = datetime.now(timezone.utc)
        
        return self

    def _recompute_derived_fields(self) -> bool:
        """Recompute revenue, cost, and margin based on current inputs.

        Calculates new values and assigns only when actual changes are detected.
        Uses object.__setattr__ to avoid triggering validate_assignment and
        recursive validators. Returns True if any field changed.

        Returns:
            bool: True if any derived field was updated; otherwise False.
        """
        changed = False

        previous_revenue = self.revenue
        previous_cost = self.cost
        previous_margin = self.margin

        revenue_inputs_ready = self.quantity is not None and self.sale_price is not None
        cost_inputs_ready = (
            self.quantity is not None and self.purchase_price is not None
        )

        if revenue_inputs_ready:
            new_revenue = Money(amount=self.quantity * self.sale_price.amount)
            if previous_revenue != new_revenue:
                object.__setattr__(self, "revenue", new_revenue)
                changed = True

        if cost_inputs_ready:
            new_cost = Money(amount=self.quantity * self.purchase_price.amount)
            if previous_cost != new_cost:
                object.__setattr__(self, "cost", new_cost)
                changed = True

        if self.revenue is not None and self.cost is not None:
            new_margin = SignedMoney5(amount=self.revenue.amount - self.cost.amount)
            if previous_margin != new_margin:
                object.__setattr__(self, "margin", new_margin)
                changed = True

        if changed:
            object.__setattr__(self, "updated_at", datetime.now(timezone.utc))

        return changed

    @field_validator('quantity', mode='after')
    @classmethod
    def _validate_quantity_and_trigger(cls, v):  # noqa: D401
        """Validate quantity; model-level validator will handle recomputation."""
        return v

    @field_validator('sale_price', mode='after')
    @classmethod
    def _validate_sale_price_and_trigger(cls, v):  # noqa: D401
        """Validate sale_price; model-level validator will handle recomputation."""
        return v

    @field_validator('purchase_price', mode='after')
    @classmethod
    def _validate_purchase_price_and_trigger(cls, v):  # noqa: D401
        """Validate purchase_price; model-level validator will handle recomputation."""
        return v

    @model_validator(mode='after')
    def _recalc_after_assignment(self) -> 'DealItem':
        """Recalculate derived fields after assignments to driver fields.

        Works together with validate_assignment=True so that any assignment triggers
        a recomputation, independent of model_fields_set.

        Returns:
            DealItem: Self.
        """
        try:
            self._recompute_derived_fields()
        except Exception as exc:
            # Defensive log: keep swallowing to preserve existing behavior
            logger.exception(
                (
                    "DealItem recompute failed; deal_id=%s position=%s qty=%s "
                    "sale=%s purchase=%s error=%s"
                ),
                str(self.deal_id) if self.deal_id else None,
                self.position_number,
                str(self.quantity) if self.quantity is not None else None,
                str(self.sale_price.amount) if self.sale_price else None,
                str(self.purchase_price.amount) if self.purchase_price else None,
                str(exc),
            )
            pass
        return self

    def calculate_fields(self) -> None:
        """Recalculate derived fields based on current inputs.

        Deprecated:
            Prefer automatic recomputation via model validators.

        Returns:
            None
        """
        # Рассчитываем выручку (количество * цена продажи)
        if (
            self.revenue is None and self.quantity is not None and self.sale_price is not None
        ):
            self.revenue = Money(amount=self.quantity * self.sale_price.amount)

        # Рассчитываем стоимость закупки (количество * цена закупки)
        if (
            self.cost is None
            and self.quantity is not None
            and self.purchase_price is not None
        ):
            self.cost = Money(amount=self.quantity * self.purchase_price.amount)

        # Рассчитываем маржу (выручка - стоимость закупки)
        if (
            self.margin is None and self.revenue is not None and self.cost is not None
        ):
            self.margin = SignedMoney5(amount=self.revenue.amount - self.cost.amount)

        self.updated_at = datetime.now(timezone.utc)

    @field_serializer('explicit_id', 'deal_id')
    def serialize_uuid(self, value: UUID | None) -> str | None:
        """Serialize UUID to string.

        Args:
            value: UUID value.

        Returns:
            str | None: Stringified UUID or None.
        """
        return str(value) if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO 8601 string.

        Args:
            value: Datetime value.

        Returns:
            str | None: ISO formatted string or None.
        """
        return value.isoformat() if value is not None else None

    @field_serializer('quantity')
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        """Serialize Decimal to string.

        Args:
            value: Decimal value.

        Returns:
            str | None: Stringified decimal or None.
        """
        return str(value) if value is not None else None
        
    @field_serializer('purchase_price')
    def serialize_money5(self, value: Money5 | None) -> str | None:
        """Serialize Money5 to string.

        Args:
            value: Money5 value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None

    @field_serializer('sale_price', 'revenue', 'cost')
    def serialize_money(self, value: Money | None) -> str | None:
        """Serialize Money to string.

        Args:
            value: Money value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None
        
    @field_serializer('margin')
    def serialize_signed_money5(self, value: SignedMoney5 | None) -> str | None:
        """Serialize SignedMoney5 to string.

        Args:
            value: SignedMoney5 value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None

    @field_serializer('hash_key')
    def serialize_hash_key(self, value: HashKey | None) -> str | None:
        """Serialize HashKey to string for stable dumps.

        Args:
            value: HashKey value.

        Returns:
            str | None: Hex string or None.
        """
        return value.value if value is not None else None

    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        populate_by_name=True,
        from_attributes=True,
    )


class Deal(BaseModel):
    """Deal aggregate root (master record).

    Represents a client invoice with multiple item positions and related totals.
    """

    # Уникальные идентификаторы  
    explicit_id: Optional[UUID] = Field(
        None,
        description=(
            "Поле для явного задания ID (переопределяет детерминированный)"
        ),
    )

    # Информация о клиенте и продавце
    client_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(
        ...,
        description="Название клиента",
    )

    # Документооборот
    invoice_info: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(..., description="Полная информация о счете")
    invoice_number: Optional[str] = Field(None, max_length=50, description="Номер счета")
    invoice_date: Optional[str] = Field(None, description="Дата счета")
    upd_number: Optional[str] = Field(
        None,
        max_length=50,
        description="Инфрмацие о счете на продажу",
    )

    # Статусы
    is_shipped: Optional[Status] = Field(None, description="Статус отгрузки")
    is_paid: Optional[Status] = Field(None, description="Статус оплаты")

    # Финансовые показатели
    total_revenue: Optional[Money] = Field(
        None,  
        alias='total_revenue_amount', 
        description="Общая выручка по сделке"
        )
    total_margin: Optional[SignedMoney] = Field(None, 
        alias='total_margin_amount', 
        description="Общая маржа по сделке")
    total_cost: Optional[Money] = Field(None, 
        alias='total_cost_amount', 
        description="Общая стоимость закупки")
    kickback_amount: Optional[Money] = Field(None, 
        alias='kickback_amount_value', 
        description="Сумма отката покупателю")


    # Период отчета  
    period: Period = Field(..., description="Период отчета")
    period_month: str = Field(
           ..., max_length=10, description="Название месяца"
    )
    period_year: str = Field(
           ..., max_length=4, description="Год"
    )
    seller: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ] = Field(..., description="Продавец")

    # Позиции товаров
    items: tuple[DealItem, ...] = Field(
        default_factory=tuple, description="Позиции товаров в сделке"
    )

    # Метаданные
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    # Иммутабельность бизнес-ключа: сохраняем первоначальное значение deal_key
    _frozen_deal_key: Optional[str] = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        """Store initial deal_key and stamp context on existing items."""
        if self._frozen_deal_key is None:
            self._frozen_deal_key = self.deal_key
        # Ensure items carry parent context
        if self.items:
            for it in self.items:
                if it.deal_id != self.id or it.deal_key != self.deal_key:
                    it.deal_id = self.id
                    it.deal_key = self.deal_key

    @computed_field
    def id(self) -> UUID:
        """Return deterministic UUID based on `deal_key`.

        Priority is given to `explicit_id`; otherwise a UUIDv5 is derived from `deal_key`.

        Returns:
            UUID: Stable identifier for the deal.
        """
        if self.explicit_id is not None:
            return self.explicit_id 
                     
        # Фиксированный namespace для всех сделок
        namespace = UUID('550e8400-e29b-41d4-a716-446655440000')
        return uuid5(namespace, self.deal_key)
    
    @computed_field
    def deal_key(self) -> str:
        """Compute the unique business key for the deal.

        Normalizes components by trimming whitespace and lowercasing to ensure
        case-insensitive, stable keys.

        Returns:
            str: invoice_number|invoice_date|seller|period (all lowercased/trimmed)
        """
        num = (self.invoice_number or "").strip().lower()
        date = (self.invoice_date or "").strip().lower()
        seller = (self.seller or "").strip().lower()
        period_str = str(self.period).lower()
        return f"{num}|{date}|{seller}|{period_str}"

    @computed_field
    def hash_key(self) -> HashKey:
        """Compute lightweight hash key for fast change detection.

        Returns:
            HashKey: Hash of selected fields including item hash keys.
        """
        data = {
            "client_name": self.client_name,
            "upd_number": self.upd_number or None,
            "is_shipped": self.is_shipped.value if self.is_shipped else None,
            "is_paid": self.is_paid.value if self.is_paid else None,
            "invoice_number": (
                self.invoice_number.strip().lower() if self.invoice_number else None
            ),
            "invoice_date": (
                self.invoice_date.strip().lower() if self.invoice_date else None
            ),
            "seller": (self.seller.strip().lower() if self.seller else None),
            "period": (str(self.period).lower() if self.period is not None else None),
            "kickback_amount": (
                str(self.kickback_amount.amount)
                if self.kickback_amount is not None
                else None
            ),
            "total_revenue": (
                str(self.total_revenue.amount)
                if self.total_revenue is not None
                else None
            ),
            "total_margin": (
                str(self.total_margin.amount)
                if self.total_margin is not None
                else None
            ),
            "total_cost": (
                str(self.total_cost.amount)
                if self.total_cost is not None
                else None
            ),
            "total_calc_revenue_amount": (
                str(self.calc_revenue_amount.amount)
                if self.calc_revenue_amount is not None
                else None
            ),
            "total_calc_margin_amount": (
                str(self.calc_margin_amount.amount)
                if self.calc_margin_amount is not None
                else None
            ),
            "total_calc_cost_amount": (
                str(self.calc_cost_amount.amount)
                if self.calc_cost_amount is not None
                else None
            ),
            "total_has_totals_error": (
                str(self.has_totals_error)
                if self.has_totals_error is not None
                else None
            ),
            "total_items_count": (
                str(self.items_count)
                if self.items_count is not None
                else None
            ),
            "total_quantity": (
                str(self.total_quantity)
                if self.total_quantity is not None
                else None
            ),

            'items': tuple(
                item.hash_key.value
                for item in sorted(self.items, key=lambda x: x.position_number)
            ),
        }
        return HashKey.from_dict(data)

    @computed_field
    def calc_revenue_amount(self) -> Money:
        """Calculate total revenue across items.

        Returns:
            Money: Sum of item revenues (missing values treated as zero).
        """
        total = sum(
            (item.revenue.amount for item in self.items if item.revenue),
            Decimal('0'),
        )
        return Money(amount=total)

    @computed_field
    def calc_margin_amount(self) -> SignedMoney:
        """Calculate total margin across items.

        Returns:
            SignedMoney: Sum of item margins (missing values treated as zero).
        """
        total = sum(
            (item.margin.amount for item in self.items if item.margin),
            Decimal('0'),
        )
        return SignedMoney(amount=total)

    @computed_field
    def calc_cost_amount(self) -> Money:
        """Calculate total cost across items.

        Returns:
            Money: Sum of item costs (missing values treated as zero).
        """
        total = sum(
            (item.cost.amount for item in self.items if item.cost),
            Decimal('0'),
        )
        return Money(amount=total)

    @computed_field
    def items_count(self) -> int:
        """Return number of items in the deal."""
        return len(self.items)

    @computed_field
    def total_quantity(self) -> Decimal:
        """Return total quantity aggregated across items (missing treated as 0)."""
        return (
            sum(
                (
                    (item.quantity if item.quantity is not None else Decimal("0"))
                    for item in self.items
                ),
                Decimal("0"),
            )
            if self.items
            else Decimal("0")
        )

    @computed_field
    def has_totals_error(self) -> Optional[bool]:
        """Detect mismatch between declared and calculated totals.

        Returns:
            Optional[bool]:
                - True if any provided total differs from calculated by more than THRESHOLD_DECIMAL.
                - False if provided totals match calculated within the threshold.
                - None if no totals were provided (all declared totals are None).
        """
        calc_rev = self.calc_revenue_amount.amount
        calc_mar = self.calc_margin_amount.amount
        calc_cost = self.calc_cost_amount.amount

        # If user did not provide any totals, indicate "not applicable"
        if (
            self.total_revenue is None
            and self.total_margin is None
            and self.total_cost is None
        ):
            return None

        def _mismatch(src_money: Money | SignedMoney | None, calc_amount: Decimal) -> bool:
            if src_money is None:
                return False
            return abs(src_money.amount - calc_amount) > THRESHOLD_DECIMAL

        return (
            _mismatch(self.total_revenue, calc_rev)
            or _mismatch(self.total_margin, calc_mar)
            or _mismatch(self.total_cost, calc_cost)
        )

    # client_name now validated via StringConstraints(strip_whitespace=True, min_length=1)


    @model_validator(mode='after')
    def _sync_period_fields(self) -> 'Deal':
        """Synchronize period_month/year with Period object.

        Source of truth: `self.period` (already normalized by Period validators).

        Returns:
            Deal: Self.
        """
        try:
            if self.period is not None:
                if self.period_month != self.period.month:
                    self.period_month = self.period.month
                if self.period_year != self.period.year:
                    self.period_year = self.period.year
        except Exception as exc:
            # Defensive log: keep swallowing to preserve existing behavior
            logger.exception(
                (
                    "Deal period sync failed; explicit_id=%s invoice_info=%s seller=%s "
                    "period=%s month=%s year=%s error=%s"
                ),
                str(self.explicit_id) if self.explicit_id else None,
                self.invoice_info,
                self.seller,
                str(self.period) if self.period is not None else None,
                self.period_month,
                self.period_year,
                str(exc),
            )
            pass
        return self

    @model_validator(mode='after')
    def _enforce_deal_key_immutability(self) -> 'Deal':
        """Prevent changes to deal_key after model initialization.

        Changing 'invoice_number', 'invoice_date', 'seller', or 'period' constitutes a different Deal.
        """
        current_key = self.deal_key
        if self._frozen_deal_key is None:
            self._frozen_deal_key = current_key
            return self
        if current_key != self._frozen_deal_key:
            logger.error(
                "Attempt to change immutable deal_key; explicit_id=%s old=%s new=%s",
                str(self.explicit_id) if self.explicit_id else None,
                self._frozen_deal_key,
                current_key,
            )
            raise ValueError(
                "deal_key is immutable; changing 'invoice_number', 'invoice_date', 'seller', or 'period' "
                "must create a new Deal entity."
            )
        return self

    # ---------------------------- Validators (Money/Status) ----------------------------
    @field_validator('total_revenue', 'total_cost', 'kickback_amount', mode='before')
    @classmethod
    def _money_from_scalar_or_dict_deal(cls, v):
        """Normalize Money-like input for deal totals.

        Accepts:
        - None
        - Money instance
        - dict with 'amount'
        - scalar (str/Decimal/float/int)

        Args:
            v: Value to normalize.

        Returns:
            Money | None: Normalized Money or None.
        """
        if v is None:
            return None
        if isinstance(v, Money):
            return v
        if isinstance(v, dict):
            amt = v.get('amount')
            if amt is None:
                return None
            return Money(amount=Decimal(str(amt)))
        return Money(amount=Decimal(str(v)))

    @field_validator('total_margin', mode='before')
    @classmethod
    def _signed_money_from_scalar_or_dict_deal(cls, v):
        """Normalize SignedMoney-like input for deal totals.

        Accepts None, dict with 'amount', scalars, or SignedMoney.

        Args:
            v: Value to normalize.

        Returns:
            SignedMoney | None: Normalized SignedMoney or None.
        """
        if v is None:
            return None
        if isinstance(v, SignedMoney):
            return v
        if isinstance(v, dict):
            amt = v.get('amount')
            if amt is None:
                return None
            return SignedMoney(amount=Decimal(str(amt)))
        return SignedMoney(amount=Decimal(str(v)))

    @field_validator('is_shipped', 'is_paid', mode='before')
    @classmethod
    def _status_from_scalar(cls, v):
        """Normalize value to Status enum.

        Accepts None, Status, bool, or string.

        Args:
            v: Value to normalize.

        Returns:
            Status | None: Normalized status or None.
        """
        if v is None:
            return None
        if isinstance(v, Status):
            return v
        if isinstance(v, bool):
            return Status.COMPLETED if v else Status.PENDING
        return Status.from_string(str(v))


    def set_id(self, value: UUID) -> None:
        """Set explicit identifier.

        Args:
            value: UUID to set as explicit identifier (used in tests/migrations).
        """
        self.explicit_id = value
        
    @model_validator(mode='after')
    def _validate_unique_position_numbers(self) -> 'Deal':
        """Validate uniqueness of position_number across items.

        Ensures domain invariant: within a single deal, all item position numbers
        must be unique and start from 1+ (DealItem enforces ge=1 per item).

        Returns:
            Deal: Self if validation passes.

        Raises:
            ValueError: If duplicate position numbers are found.
        """
        try:
            if self.items:
                numbers = [it.position_number for it in self.items]
                duplicates = {
                    n for n in numbers if numbers.count(n) > 1  # small lists, clarity over perf
                }
                if duplicates:
                    dup_list = ", ".join(str(n) for n in sorted(duplicates))
                    raise ValueError(
                        f"Duplicate position_number in deal '{self.deal_key}': {dup_list}"
                    )
        except Exception as exc:
            # Re-raise domain error, but log for diagnostics
            logger.error(
                "Deal validation failed for unique position_number; deal_key=%s error=%s",
                self.deal_key,
                str(exc),
            )
            raise
        return self

    def add_item(self, item: DealItem) -> None:
        """Add an item to the deal."""
        # Early duplicate check to prevent inconsistent state
        if any(existing.position_number == item.position_number for existing in self.items):
            raise ValueError(
                f"Duplicate position_number {item.position_number} in deal '{self.deal_key}'"
            )

        item.deal_id = self.id
        item.deal_key = self.deal_key
        self.items = (*self.items, item)
        self.updated_at = datetime.now(timezone.utc)

    def calculate_totals(self) -> None:
        """Deprecated: no-op. Aggregates are computed via @computed_field now.

        Kept for backward compatibility; only updates `updated_at` timestamp.
        """
        self.updated_at = datetime.now(timezone.utc)


    @field_serializer('explicit_id')
    def serialize_uuid_deal(self, value: UUID | None) -> str | None:
        """Serialize UUID to string.

        Args:
            value: UUID value.

        Returns:
            str | None: Stringified UUID or None.
        """
        return str(value) if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime_deal(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO 8601 string.

        Args:
            value: Datetime value.

        Returns:
            str | None: ISO formatted string or None.
        """
        return value.isoformat() if value is not None else None
        
    @field_serializer('total_revenue', 'total_cost', 'kickback_amount')
    def serialize_money_deal(self, value: Money | None) -> str | None:
        """Serialize Money to string.

        Args:
            value: Money value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None
        
    @field_serializer('total_margin')
    def serialize_signed_money_deal(self, value: SignedMoney | None) -> str | None:
        """Serialize SignedMoney to string.

        Args:
            value: SignedMoney value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None

    @field_serializer('hash_key')
    def serialize_hash_key_deal(self, value: HashKey | None) -> str | None:
        """Serialize HashKey to string for stable dumps.

        Args:
            value: HashKey value.

        Returns:
            str | None: Hex string or None.
        """
        return value.value if value is not None else None

    @field_serializer('calc_revenue_amount', 'calc_cost_amount')
    def serialize_calc_money_deal(self, value: Money | None) -> str | None:
        """Serialize computed Money to string.

        Args:
            value: Money value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None

    @field_serializer('calc_margin_amount')
    def serialize_calc_signed_money_deal(self, value: SignedMoney | None) -> str | None:
        """Serialize computed SignedMoney to string.

        Args:
            value: SignedMoney value.

        Returns:
            str | None: Amount as string or None.
        """
        return str(value.amount) if value is not None else None

    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True,
        populate_by_name=True,
        from_attributes=True
    ) 