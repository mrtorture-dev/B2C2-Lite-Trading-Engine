from django.urls import path
from .views import PortfolioView, CreateOrderView

urlpatterns = [
    path("portfolio/", PortfolioView.as_view(), name="portfolio"),
    path("orders/", CreateOrderView.as_view(), name="create-order"),
]
