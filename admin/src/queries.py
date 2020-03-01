"""Module, where all query templates are constructed"""
from sqlalchemy import func, update, delete, join, select, and_, between, or_, outerjoin, case
from admin.src.models import (db,
                              Products,
                              Businesses,
                              Orders,
                              SpecificOrders,
                              ProductsMovement,
                              CriticalLevels)
from sqlalchemy.orm import aliased
from datetime import datetime
from sqlalchemy.sql import text


def client_supplier_query(order_id: int) -> Products:
    """Return query for get inforamtions about sides in order."""

    Clients = aliased(Businesses)
    Suppliers = aliased(Businesses)
    ClientSupplier = join(Orders, Clients, Orders.client_id == Clients.name)\
        .join(Suppliers, Suppliers.name == Orders.supplier_id)
    query = aliased(select([Clients.name.label("Клиент"),
                            Suppliers.name.label("Поставщик")])
                    .where(Orders.order_id == order_id)
                    .select_from(ClientSupplier))
    return query


def types_query(owner_id):
    """Return query for proucts on storage."""
    query = Products.query.with_entities(Products.type_name.label('Тип'))\
        .filter_by(owner_id=owner_id)\
        .distinct()
    return query


def statistics_query(owner_id):
    """Return a query, that get count of each type on storage."""

    """
    WITH p_count AS (
        SELECT
            type_name,
            owner_id,
            COUNT(type_name) product_count
        FROM products
        GROUP BY (owner_id, type_name)
    ),
    """
    p_count = db.session.query(
        Products.type_name,
        Products.owner_id,
        func.count(Products.type_name).label('product_count'),
        func.count(case([
                        (Products.product_condition == True, Products.type_name)
                        ],
                        else_=None
                        )).label('valid')
    )\
        .select_from(Products)\
        .filter(Products.owner_id == owner_id)\
        .group_by(Products.owner_id, Products.type_name)\
        .subquery(name='p_count')
    """
    so AS (
        SELECT 
            type_name,
            supplier_id,
            SUM(quantity) ordered
        FROM orders 
        JOIN specific_orders USING(order_id) 
        GROUP BY (type_name, supplier_id)
    )

    """
    specific_orders = db.session.query(
        SpecificOrders.type_name,
        Orders.supplier_id,
        func.sum(SpecificOrders.quantity).label('ordered')
    )\
        .select_from(Orders)\
        .join(SpecificOrders, Orders.order_id == SpecificOrders.order_id)\
        .filter(Orders.supplier_id == owner_id)\
        .group_by(SpecificOrders.type_name, Orders.supplier_id)\
        .subquery(name='specific_orders')
    """
    SELECT 
        owner_id,
        p.type_name,
        so.ordered,
        p.product_count
    FROM p_count p
    LEFT JOIN so ON p.type_name = so.type_name AND p.owner_id = so.supplier_id
    ORDER BY 1  
    """
    stats_query = db.session.query(
        p_count.c.owner_id,
        p_count.c.type_name.label('Тип'),
        p_count.c.product_count.label('К-во'),
        p_count.c.valid.label('К-во исправных'),
        (func.coalesce(specific_orders.c.ordered, 0)).label('Заказано'),
        CriticalLevels.critical_amount.label('Критический уровень')
    )\
        .select_entity_from(p_count)\
        .outerjoin(CriticalLevels, and_(CriticalLevels.business == p_count.c.owner_id,
                                        CriticalLevels.type_name == p_count.c.type_name))\
        .outerjoin(specific_orders, and_(p_count.c.type_name == specific_orders.c.type_name,
                                         p_count.c.owner_id == specific_orders.c.supplier_id))\
        .order_by(p_count.c.owner_id)

    # query = select([Products.type_name.label('Tип'),
    #                 func.count(Products.type_name).label('Всего')])\
    #     .where(Products.owner_id == owner_id)\
    #     .group_by(Products.type_name)
    # aliased(query),
    return stats_query


def set_critical_level(owner_id, type_name, new_critical_level):
    db.session.query(CriticalLevels).filter(
        and_(
            CriticalLevels.business == owner_id,
            CriticalLevels.type_name == type_name
        ))\
        .update({CriticalLevels.critical_amount: new_critical_level
                 }, synchronize_session=False)

    db.session.commit()


def get_critical_level(owner_id, type_name):
    critical_level = select([
        CriticalLevels.critical_amount
    ])\
        .select_from(CriticalLevels)\
        .where(and_(
            CriticalLevels.business == owner_id,
            CriticalLevels.type_name.in_(type_name),
        )
    )
    return db.session.query(aliased(critical_level))


def expand_type_query_2(owner_id: str, type_name: []) -> 'session query':
    """Return query, where provide detaled info about available products for this type."""
    critical_level = get_critical_level(owner_id, type_name)

    ordered = db.session.query(
        func.sum(SpecificOrders.quantity).label('number')
    )\
        .join(Orders, Orders.order_id == SpecificOrders.order_id)\
        .filter(
        and_(
            Orders.supplier_id == owner_id,
            SpecificOrders.type_name.in_(type_name)
        )

    )

    query = select([Products.type_name.label('Тип'),
                    Products.serial_number.label('Серийный номер'),
                    Products.producent.label('Изготовитель'),
                    Products.model.label('Модель'),
                    Products.product_condition.label('Состояние'),
                    Products.additonal_info.label('Инфо'),
                    Products.appear_in_order.label('Привязан к заказу')])\
        .where(
        and_(
            Products.owner_id == owner_id,
            Products.type_name.in_(type_name)
        )
    )
    return db.session.query(aliased(query)), ordered, critical_level


def expand_type_query(owner_id: str, type_name: [], order_id) -> 'session query':
    """Return query, where provide detaled info about available products for this type."""
    query = select([Products.type_name.label('Тип'),
                    Products.serial_number.label('Серийный номер'),
                    Products.producent.label('Изготовитель'),
                    Products.model.label('Модель'),
                    Products.product_condition.label('Состояние'),
                    Products.additonal_info.label('Инфо'),
                    Products.appear_in_order.label('Привязан к заказу')])\
        .where(
        and_(
            Products.owner_id == owner_id,
            Products.type_name.in_(type_name)
        )
    )
    return db.session.query(aliased(query))


def create_product(new_product, owner_id):
    """Create new product, from provided dict."""
    if not isinstance(new_product, dict):
        raise ValueError(f"New product {new_product} is not a dict")
    new_instance = Products(
        serial_number=new_product['serial_number'],
        type_name=new_product['type_name'],
        owner_id=owner_id,
        product_condition=new_product['product_condition'] == 'true',
        model=new_product['model'],
        producent=new_product['producent'],
        additonal_info=new_product['additional_info'],
    )
    if not get_critical_level(owner_id, [new_product['type_name']]).all():
        new_critical_entry = CriticalLevels(
            business=owner_id,
            type_name=new_product['type_name']
        )
    else:
        new_critical_entry = None
    return new_instance, new_critical_entry


def businesses_query():
    query = select(
        [Businesses.name.label("name")]
    )
    return aliased(query)


# Fix. Add owner id check
def get_orders_query(history, business_id):
    """
    Create query object to get all orderrs from storage.

    Return Query
    """
    Clients = aliased(Businesses)
    Suppliers = aliased(Businesses)
    query = db.session.query(
        Orders.order_id.label("Ид заказа"),
        Orders.order_date.label("Дата заказа"),
        Clients.name.label("Клиент"),
        Suppliers.name.label("Поставщик"),
        Orders.order_id)\
        .join(Clients, Clients.name == Orders.client_id)\
        .join(Suppliers, Suppliers.name == Orders.supplier_id)\
        .filter(or_(Orders.supplier_id == business_id, Orders.client_id == business_id))
    if not history:
        query = query.filter(Orders.completion_date == None).order_by(
            Orders.order_date.desc())
    else:
        query = db.session.query(
            Orders.completion_date.label("Дата выполнения"),
            Clients.name.label("Клиент"),
            Suppliers.name.label("Поставщик"),
            Orders.order_id)\
            .join(Clients, Clients.name == Orders.client_id)\
            .join(Suppliers, Suppliers.name == Orders.supplier_id)
        query = query.filter(and_(Orders.completion_date != None,
                                  or_(Orders.supplier_id == business_id,
                                      Orders.client_id == business_id)))\
            .order_by(Orders.completion_date.desc())
    return query


"""
Super query in SQL
WITH a AS (
    SELECT type_name, supplier_id, quantity
    FROM b2b.orders
    JOIN b2b.specific_orders USING (order_id)
    WHERE order_id = 11),
    b as (
        SELECT serial_number, owner_id, quantity,
        ROW_NUMBER()  OVER (
            PARTITION BY a.type_name
        ) r_n,
    COUNT(*) OVER (
            PARTITION BY a.type_name
        ) c
    FROM b2b.products p
    JOIN a ON a.supplier_id = p.owner_id AND a.type_name = p.type_name )
SELECT *, c-quantity  AS "Left" FROM b WHERE r_n <= quantity
"""


def expand_order_query(order_id):
    """Return query object.

       Fieldes:
        type_name,
        quantity,
        serial_number,
        model,
        producent,
        additional_info,
        objects on storage

        Max number of returned rows is 100
     """
    # SupplierProducts = outerjoin(
    #     Orders, Products, Orders.supplier_id == Products.owner_id)
    # print(SupplierProducts)
    # count = aliased(
    #     select([
    #         Products.type_name,
    #         func.count().label('number')
    #     ])
    #     .select_from(SupplierProducts)
    #     .where(Orders.order_id == order_id)
    #     .group_by(Products.type_name))

    # count_of_available = aliased(
    #     select([
    #         Products.type_name,
    #         func.count().label('available_number')
    #     ])
    #     .select_from(SupplierProducts)
    #     .where(and_(Orders.order_id == order_id, or_(Products.appear_in_order == order_id, Products.appear_in_order == None)))
    #     .group_by(Products.type_name))

    # ProductsSupplierCanSupply = join(Orders, SpecificOrders, Orders.order_id == SpecificOrders.order_id)\
    #     .join(Businesses, Orders.supplier_id == Businesses.name)\
    #     .outerjoin(Products, and_(Products.owner_id == Businesses.name,
    #                               Products.type_name == SpecificOrders.type_name))\
    #     .outerjoin(count, SpecificOrders.type_name == count.c.type_name)\
    #     .outerjoin(count_of_available, SpecificOrders.type_name == count_of_available.c.type_name)

    # # 1

    """
    SELECT 
        b2b.products.type_name AS b2b_products_type_name,
        specific_orders.quantity,
        count(*) AS number, 
        count(CASE WHEN (b2b.products.appear_in_order IS NULL) THEN b2b.products.type_name END) AS available_number 
    FROM b2b.products 
    JOIN b2b.orders ON b2b.orders.order_id = 12
                    AND b2b.orders.supplier_id = b2b.products.owner_id 
    JOIN b2b.specific_orders ON b2b.specific_orders.order_id = b2b.orders.order_id 
                             AND b2b.specific_orders.type_name = b2b.products.type_name 
    GROUP BY (b2b.products.type_name, specific_orders.quantity);
    """
    order_sides = db.session.query(
        Orders.supplier_id.label('Поставщик'),
        Orders.client_id.label('Клиент')
    ).filter(Orders.order_id == order_id)

    # Select for order stats
    order_stats_query = db.session.query(SpecificOrders.type_name.label('Тип'),
                                         SpecificOrders.quantity.label(
                                             'Заказано'),
                                         func.count(
        case(
            [
                (and_(Products.appear_in_order == None,
                      Products.product_condition == True),
                 Products.type_name)
            ],
            else_=None
        )
    ).label('К-во исправных свободных'),
        func.count(Products.type_name).label('К-во на складе'),
        func.count(
            case(
                [
                    (Products.appear_in_order == order_id, Products.type_name)
                ],
                else_=None
            )
    ).label('К-во привязаных')
    )\
        .select_from(Orders)\
        .join(SpecificOrders, SpecificOrders.order_id == Orders.order_id)\
        .join(Products,
              and_(
                  Products.type_name == SpecificOrders.type_name,
                  Orders.supplier_id == Products.owner_id
              ), isouter=True)\
        .filter(Orders.order_id == order_id)\
        .group_by(SpecificOrders.type_name, SpecificOrders.quantity)

    # .join(Orders, and_(Orders.order_id == order_id,
    #                    Orders.supplier_id == Products.owner_id))\
    #     .join(SpecificOrders, and_(
    #         SpecificOrders.order_id == Orders.order_id,
    #         SpecificOrders.type_name == Products.type_name
    #     )
    # )\
    # .group_by(Products.type_name, SpecificOrders.quantity)
    # 2
    available_products_query = db.session.query(
        Products.type_name.label('Тип'),
        Products.producent.label('Производитель'),
        Products.model.label('Модель'),
        Products.serial_number.label('Серийный номер'),
        Products.appear_in_order.label('Привязан к заказу'),
        Products.additonal_info.label('Дополнительная информация'),
    )\
        .join(Orders, and_(Orders.order_id == order_id,
                           Orders.supplier_id == Products.owner_id))\
        .join(SpecificOrders, and_(
            SpecificOrders.order_id == Orders.order_id,
            SpecificOrders.type_name == Products.type_name
        )
    )\
        .filter(and_(or_(Products.appear_in_order == None,
                         Products.appear_in_order == order_id),
                     Products.product_condition == True
                     ))\
        .order_by(Products.type_name, Products.appear_in_order.asc())

    return order_sides, order_stats_query, available_products_query
    # column dublicates, that needed because of there usage in server.py
    # query = aliased(select([
    #     Orders.supplier_id,
    #     Orders.client_id,
    #     SpecificOrders.type_name.label('Тип'),
    #     Products.producent.label('Производитель'),
    #     Products.model.label('Модель'),
    #     Products.appear_in_order.label(
    #         'Привязан к заказу'),
    #     SpecificOrders.type_name,
    #     SpecificOrders.quantity,
    #     Products.serial_number,
    #     Products.serial_number.label('Серийный номер'),

    #     Products.additonal_info.label(
    #         'Дополнительная информация'),
    #     count.c.number,
    #     count_of_available.c.available_number
    # ])
    #     .select_from(ProductsSupplierCanSupply).where(and_(Orders.order_id == order_id,
    #                                                        or_(Products.appear_in_order == order_id,
    #                                                            Products.appear_in_order == None)))
    #     .order_by(Products.type_name, Products.appear_in_order.asc())
    #     .limit(100))
    # return db.session.query(query)


def orders_from_to_query(is_history, from_, to, business_id):
    if is_history is None:
        print('here')
        query = get_orders_query(is_history, business_id).filter(
            between(Orders.order_date, from_, to)
        )
    else:
        query = get_orders_query(is_history, business_id).filter(
            between(Orders.completion_date, from_, to)
        )

    return query


def change_owner(client, serial_numbers):
    db.session.query(Products).filter(Products.serial_number.in_(serial_numbers)).\
        update({Products.owner_id: client
                }, synchronize_session=False)
    db.session.commit()


def unbind_from_order(serial_numbers):
    print(serial_numbers)
    db.session.query(Products).filter(Products.serial_number.in_(serial_numbers)).\
        update({Products.appear_in_order: None
                }, synchronize_session=False)
    db.session.commit()


def unbind_all_from_order(order_id):
    db.session.query(Products).filter_by(appear_in_order=order_id).\
        update({Products.appear_in_order: None
                }, synchronize_session=False)
    db.session.commit()


def bind_to_order(order_id, serial_numbers):
    db.session.query(Products).filter(Products.serial_number.in_(serial_numbers)).\
        update({Products.appear_in_order: order_id
                }, synchronize_session=False)
    db.session.commit()


def modify_specific_orders(order_id, order_stats):
    presented_types = db.session.query(SpecificOrders.type_name)\
                        .filter(SpecificOrders.order_id == order_id)\
                        .all()

    presented_types = [p_type.type_name for p_type in presented_types]
    deleted_types = set(presented_types)
    for p_type, amount in order_stats:
        deleted_types -= set([p_type])
        if p_type in presented_types:
            db.session.query(SpecificOrders).filter(and_(SpecificOrders.type_name == p_type,
                                                         SpecificOrders.order_id == order_id))\
                .update({SpecificOrders.quantity: amount}, synchronize_session=False)
        else:
            new_specific_order = SpecificOrders(
                order_id=order_id,
                quantity=amount,
                type_name=p_type
            )
            db.session.add(new_specific_order)

    for p_type in deleted_types:
        db.session.query(SpecificOrders)\
            .filter(and_(SpecificOrders.type_name == p_type, SpecificOrders.order_id == order_id))\
            .delete()

    db.session.commit()


def add_history_record(order_id, serial_numbers):
    db.session.query(Orders).filter(Orders.order_id == order_id).\
        update({Orders.completion_date: datetime.now()
                }, synchronize_session=False)

    db.session.query(SpecificOrders)\
        .filter_by(order_id=order_id)\
        .delete()

    products = db.session.query(Products).filter(
        Products.serial_number.in_(serial_numbers)).all()
    query = aliased(select(
        [
            Products.serial_number,
            Products.type_name,
            Products.producent,
            Products.model
        ]
    )
        .select_from(Products)
        .where(Products.serial_number.in_(serial_numbers)))
    products = db.session.query(query)
    for product in products:
        history_record = ProductsMovement(
            order_id=order_id,
            serial_number=product.serial_number,
            type_name=product.type_name,
            producent=product.producent,
            model=product.model
        )
        db.session.add(history_record)
    db.session.commit()


def expand_history_order_query(order_id):
    OrderDecription = outerjoin(
        Orders, ProductsMovement, Orders.order_id == ProductsMovement.order_id)

    query = select([
        ProductsMovement.type_name.label('Тип'),
        ProductsMovement.producent.label('Производитель'),
        ProductsMovement.model.label('Модель'),
        ProductsMovement.serial_number.label('Серийный номер'),
        Orders.supplier_id,
        Orders.client_id,
        ProductsMovement.type_name,
        ProductsMovement.serial_number
    ])\
        .select_from(OrderDecription)\
        .where(ProductsMovement.order_id == order_id)\
        .order_by(ProductsMovement.type_name)

    return db.session.query(aliased(query))