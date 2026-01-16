from django.urls import path
# AQUÍ ESTABA EL ERROR: Faltaba importar las nuevas vistas
from .views import (
    PortfolioView, 
    CreateOrderView, 
    dashboard_view, 
    price_htmx_view, 
    create_order_htmx_view,
    portfolio_htmx_view,
    order_book_htmx_view,
    accept_order_htmx_view,
    my_orders_htmx_view,    
    cancel_order_htmx_view,
    get_login_nonce, 
    web3_login_view
)

urlpatterns = [
    # Vista principal del Dashboard (cuando entras a /)
    path('', dashboard_view, name='dashboard'),

    # Endpoints para la API REST (JSON)
    path('portfolio/', PortfolioView.as_view(), name='portfolio'),
    path('orders/', CreateOrderView.as_view(), name='create-order'),

    # Endpoints para HTMX (HTML dinámico)
    path('price-htmx/', price_htmx_view, name='price-htmx'),
    path('orders-htmx/', create_order_htmx_view, name='orders-htmx'),
    path('portfolio-htmx/', portfolio_htmx_view, name='portfolio-htmx'),
    path('order-book-htmx/', order_book_htmx_view, name='order-book-htmx'),
    path('accept-order/<int:order_id>/', accept_order_htmx_view, name='accept-order'),
    path('my-orders-htmx/', my_orders_htmx_view, name='my-orders-htmx'),
    path('cancel-order/<int:order_id>/', cancel_order_htmx_view, name='cancel-order'),
    path('web3-nonce/', get_login_nonce, name='web3-nonce'),
    path('web3-login/', web3_login_view, name='web3-login'),
]