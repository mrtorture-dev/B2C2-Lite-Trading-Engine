from django.urls import path
# AQUÍ ESTABA EL ERROR: Faltaba importar las nuevas vistas
from .views import (
    PortfolioView, 
    CreateOrderView, 
    dashboard_view, 
    price_htmx_view, 
    create_order_htmx_view
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
]