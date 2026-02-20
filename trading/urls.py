from django.urls import path
# AQUÍ ESTABA EL ERROR: Faltaba importar las nuevas vistas
from .views import (
    PortfolioView, 
    CreateOrderView, 
    dashboard_view, 
    quant_view, # <-- Agregado
    price_htmx_view, 
    create_order_htmx_view,
    portfolio_htmx_view,
    order_book_htmx_view,
    accept_order_htmx_view,
    my_orders_htmx_view,    
    cancel_order_htmx_view,
    quant_stats_htmx_view, # <-- Agregado
    run_backtest_htmx_view, # <-- Added
    run_ml_optimization_htmx_view, # <-- Added
    quant_metrics_htmx_view, # <-- Added
    execute_live_step_htmx_view, # <-- Added
    get_login_nonce, 
    web3_login_view
)

urlpatterns = [
    # Vista principal del Dashboard (cuando entras a /)
    path('', dashboard_view, name='dashboard'),
    path('quant/', quant_view, name='quant'), # <-- Agregado

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
    path('quant-stats-htmx/', quant_stats_htmx_view, name='quant-stats-htmx'), # <-- Agregado
    path('run-backtest-htmx/', run_backtest_htmx_view, name='run-backtest-htmx'), # <-- Added
    path('run-ml-optimization-htmx/', run_ml_optimization_htmx_view, name='run-ml-optimization-htmx'), # <-- Added
    path('quant-metrics-htmx/', quant_metrics_htmx_view, name='quant-metrics-htmx'), # <-- Added
    path('execute-live-step-htmx/', execute_live_step_htmx_view, name='execute-live-step-htmx'), # <-- Added
    path('web3-nonce/', get_login_nonce, name='web3-nonce'),
    path('web3-login/', web3_login_view, name='web3-login'),
]