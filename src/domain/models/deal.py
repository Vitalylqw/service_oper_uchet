"""
Deal domain models.

Contains main business entities for deals and deal items.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from uuid import UUID, uuid4, uuid5

from pydantic import BaseModel, Field, computed_field, field_validator, field_serializer, ConfigDict

from ..value_objects import Money, SignedMoney, Period, HashKey, Status


class DealItem(BaseModel):
    """Позиция товара в сделке (подчиненная запись)."""

    # Уникальные идентификаторы  
    explicit_id: Optional[UUID] = Field(None, description="Поле для явного задания ID (переопределяет детерминированный)")
    deal_id: Optional[UUID] = Field(None, description="ID родительской сделки")

    # Основная информация
    product_name: str = Field(..., min_length=1, max_length=500, description="Наименование товара")
    supplier_name: Optional[str] = Field(
        None, max_length=300, description="Название поставщика"
    )

    # Количественные показатели
    quantity: Optional[Decimal] = Field(None, ge=0, description="Количество товара")
    purchase_price: Optional[Money] = Field(None, description="Цена закупки")
    sale_price: Optional[Money] = Field(None, description="Цена продажи")

    # Расчетные показатели
    revenue: Optional[Money] = Field(None, description="Выручка от позиции")
    margin: Optional[SignedMoney] = Field(None, description="Маржа по позиции")
    cost: Optional[Money] = Field(None, description="Стоимость закупки")

    # Операционная информация
    pickup_date: Optional[str] = Field(None, description="Дата забора товара у поставщика")
    position_number: Optional[int] = Field(None, ge=1, description="Номер позиции товара в сделке")

    # Метаданные
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def id(self) -> UUID:
        """Детерминированный ID на основе расширенного набора полей."""
        if self.explicit_id is not None:
            return self.explicit_id
            
        # Фиксированный namespace для всех позиций
        namespace = UUID('650e8400-e29b-41d4-a716-446655440000')
        # Используем тот же алгоритм что и для hash_key но для ID
        id_data = {
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
            "deal_id": str(self.deal_id) if self.deal_id else "",
        }
        # Создаем стабильную строку из всех полей
        id_string = "|".join(f"{k}:{v}" for k, v in sorted(id_data.items()))
        return uuid5(namespace, id_string)
    
    def set_id(self, value: UUID) -> None:
        """Позволяет явно установить ID (для тестов и миграции)."""
        self.explicit_id = value
        
    @computed_field
    @property
    def item_key(self) -> str:
        """Уникальный ключ позиции для обнаружения изменений."""
        return f"{self.product_name}|{self.supplier_name or ''}"

    @computed_field
    @property
    def hash_key(self) -> HashKey:
        """Hash ключ для быстрого сравнения изменений (расширенный набор полей)."""
        data = {
            "position_number": str(self.position_number) if self.position_number else None,
            "product_name": self.product_name,
            "supplier_name": self.supplier_name,
            "pickup_date": self.pickup_date,
            "quantity": str(self.quantity) if self.quantity else None,
            "purchase_price": str(self.purchase_price.amount) if self.purchase_price else None,
            "sale_price": str(self.sale_price.amount) if self.sale_price else None,
            "revenue": str(self.revenue.amount) if self.revenue else None,
            "margin": str(self.margin.amount) if self.margin else None,
            "cost": str(self.cost.amount) if self.cost else None,
        }
        return HashKey.from_dict(data)

    def get_full_hash_key(self, deal_key: str) -> HashKey:
        """
        Hash ключ для уникальности позиции включая deal_key и все финансовые поля.
        
        Теперь включает ВСЕ поля для полной уникальности:
        - position_number, product_name, supplier_name, pickup_date
        - quantity, purchase_price, sale_price 
        - revenue, margin, cost (новые поля!)
        - deal_key
        
        Args:
            deal_key: Ключ родительской сделки
            
        Returns:
            HashKey с учетом всех полей позиции
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

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, v: str) -> str:
        """Validate and normalize product name."""
        return v.strip()

    def calculate_fields(self) -> None:
        """Рассчитывает недостающие поля на основе имеющихся данных."""
        # Рассчитываем выручку (количество * цена продажи)
        if self.revenue is None and self.quantity and self.sale_price:
            self.revenue = Money(amount=self.quantity * self.sale_price.amount)

        # Рассчитываем стоимость закупки (количество * цена закупки)
        if self.cost is None and self.quantity and self.purchase_price:
            self.cost = Money(amount=self.quantity * self.purchase_price.amount)

        # Рассчитываем маржу (выручка - стоимость закупки)
        if self.margin is None and self.revenue and self.cost:
            self.margin = SignedMoney(amount=self.revenue.amount - self.cost.amount)

        self.updated_at = datetime.now()

    @field_serializer('explicit_id', 'deal_id')
    def serialize_uuid(self, value: UUID | None) -> str | None:
        """Serialize UUID fields to string."""
        return str(value) if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value is not None else None

    @field_serializer('quantity')
    def serialize_decimal(self, value: Decimal | None) -> str | None:
        """Serialize Decimal fields to string."""
        return str(value) if value is not None else None
        
    @field_serializer('purchase_price', 'sale_price', 'revenue', 'cost')
    def serialize_money(self, value: Money | None) -> dict | None:
        """Serialize Money fields to dict."""
        if value is None:
            return None
        return {"amount": str(value.amount)}
        
    @field_serializer('margin')
    def serialize_signed_money(self, value: SignedMoney | None) -> dict | None:
        """Serialize SignedMoney fields to dict."""
        if value is None:
            return None
        return {"amount": str(value.amount)}

    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True
    )


class Deal(BaseModel):
    """Сделка с клиентом (мастер-запись)."""

    # Уникальные идентификаторы  
    explicit_id: Optional[UUID] = Field(None, description="Поле для явного задания ID (переопределяет детерминированный)")

    # Информация о клиенте и продавце
    client_name: str = Field(..., min_length=1, max_length=300, description="Название клиента")
    seller: Optional[str] = Field(None, max_length=200, description="Продавец")

    # Документооборот
    invoice_info: str = Field(..., description="Полная информация о счете")
    invoice_number: Optional[str] = Field(None, max_length=50, description="Номер счета")
    invoice_date: Optional[str] = Field(None, description="Дата счета")
    upd_number: Optional[str] = Field(None, max_length=50, description="Номер УПД на реализацию")

    # Статусы
    is_shipped: Optional[Status] = Field(None, description="Статус отгрузки")
    is_paid: Optional[Status] = Field(None, description="Статус оплаты")

    # Финансовые показатели
    total_revenue: Optional[Money] = Field(None, description="Общая выручка по сделке")
    total_margin: Optional[SignedMoney] = Field(None, description="Общая маржа по сделке")
    total_cost: Optional[Money] = Field(None, description="Общая стоимость закупки")
    kickback_amount: Optional[Money] = Field(None, description="Сумма отката покупателю")

    # Период отчета  
    period: Any = Field(..., description="Период отчета")

    # Позиции товаров
    items: list[DealItem] = Field(default_factory=list, description="Позиции товаров в сделке")

    # Метаданные
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    @computed_field
    @property
    def id(self) -> UUID:
        """Детерминированный ID на основе deal_key."""
        if self.explicit_id is not None:
            return self.explicit_id
            
        # Фиксированный namespace для всех сделок
        namespace = UUID('550e8400-e29b-41d4-a716-446655440000')
        return uuid5(namespace, self.deal_key)
    
    @computed_field
    @property
    def deal_key(self) -> str:
        """Уникальный ключ сделки для обнаружения изменений."""
        return f"{self.client_name}|{self.invoice_number or ''}|{self.invoice_date or ''}|{self.seller or ''}|{str(self.period)}"

    @computed_field
    @property
    def hash_key(self) -> HashKey:
        """Hash ключ для быстрого сравнения изменений."""
        data = {
            "client_name": self.client_name,
            "invoice_info": self.invoice_info,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "upd_number": self.upd_number,
            "is_shipped": str(self.is_shipped) if self.is_shipped else None,
            "is_paid": str(self.is_paid) if self.is_paid else None,
            "seller": self.seller,
            "kickback_amount": str(self.kickback_amount) if self.kickback_amount else None,
            "period": str(self.period),
        }
        return HashKey.from_dict(data)

    @field_validator("client_name")
    @classmethod
    def validate_client_name(cls, v: str) -> str:
        """Validate and normalize client name."""
        return v.strip()

    def set_id(self, value: UUID) -> None:
        """Позволяет явно установить ID (для тестов и миграции)."""
        self.explicit_id = value
        
    def add_item(self, item: DealItem) -> None:
        """Добавляет позицию товара к сделке."""
        item.deal_id = self.id
        self.items.append(item)
        self.updated_at = datetime.now()

    def calculate_totals(self) -> None:
        """Рассчитывает итоговые показатели сделки на основе позиций."""
        if not self.items:
            return

        # Суммируем показатели по всем позициям
        total_revenue = sum(
            item.revenue.amount for item in self.items if item.revenue
        )
        total_cost = sum(
            item.cost.amount for item in self.items if item.cost
        )
        total_margin = sum(
            item.margin.amount for item in self.items if item.margin
        )

        # Обновляем только если значения не были установлены вручную
        if self.total_revenue is None and total_revenue > 0:
            self.total_revenue = Money(amount=total_revenue)

        if self.total_cost is None and total_cost > 0:
            self.total_cost = Money(amount=total_cost)

        if self.total_margin is None:
            self.total_margin = SignedMoney(amount=total_margin)

        self.updated_at = datetime.now()

    @field_serializer('explicit_id')
    def serialize_uuid_deal(self, value: UUID | None) -> str | None:
        """Serialize UUID fields to string."""
        return str(value) if value is not None else None

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime_deal(self, value: datetime | None) -> str | None:
        """Serialize datetime fields to ISO format."""
        return value.isoformat() if value is not None else None
        
    @field_serializer('total_revenue', 'total_cost', 'kickback_amount')
    def serialize_money_deal(self, value: Money | None) -> dict | None:
        """Serialize Money fields to dict."""
        if value is None:
            return None
        return {"amount": str(value.amount)}
        
    @field_serializer('total_margin')
    def serialize_signed_money_deal(self, value: SignedMoney | None) -> dict | None:
        """Serialize SignedMoney fields to dict."""
        if value is None:
            return None
        return {"amount": str(value.amount)}

    model_config = ConfigDict(
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True
    ) 