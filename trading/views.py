from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .services import OrderService
from .models import Wallet, Asset, Trade, Order
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import OrderCreateSerializer, WalletSerializer
from django.contrib.auth import logout, login, get_user_model
from eth_account.messages import encode_defunct
from eth_account import Account
import json
import uuid
from .quant_engine import B2C2QuantEngine

@login_required(login_url='/admin/login/')
def dashboard_view(request):
    available_assets = Asset.objects.filter(is_crypto=True)
    wallets = Wallet.objects.filter(user=request.user, balance__gt=0)
    context = {'assets': available_assets, 'wallets': wallets}
    return render(request, 'trading/dashboard.html', context)

@login_required
def quant_view(request):
    user = request.user
    btc_asset = Asset.objects.filter(code='BTC').first()
    btc_wallet = Wallet.objects.filter(user=user, asset=btc_asset).first()
    inventory_q = float(btc_wallet.balance) if btc_wallet else 0.0
    usd_asset = Asset.objects.filter(code='USD').first()
    usd_wallet = Wallet.objects.filter(user=user, asset=usd_asset).first()
    usd_balance = float(usd_wallet.balance) if usd_wallet else 0.0
    prices = cache.get('market_prices', {})
    fair_price = float(prices.get('BTC', 0.0))
    trades_query = Trade.objects.filter(buy_order__asset=btc_asset).order_by('-timestamp')
    last_price = float(trades_query.first().price) if trades_query.exists() else fair_price
    engine = B2C2QuantEngine()
    greeks = engine.calculate_greeks(inventory_q, fair_price, last_price)
    trades = trades_query[:50]
    context = {
        'inventory_q': inventory_q, 'usd_balance': usd_balance, 'fair_price': fair_price,
        'delta': greeks['delta'], 'gamma': greeks['gamma'], 'theta': greeks['theta'],
        'total_pnl': 0.0, 'sharpe': 0.0, 'mdd': 0.0,
        'equity_data': json.dumps([float(t.price) for t in reversed(trades)]),
        'inventory_data': json.dumps([float(t.amount) for t in reversed(trades)]),
        'labels': json.dumps([t.timestamp.strftime('%M:%S') for t in reversed(trades)]),
    }
    return render(request, 'trading/quant.html', context)

@login_required
def execute_live_step_htmx_view(request):
    try:
        user = request.user
        btc_asset = Asset.objects.filter(code='BTC').first()
        usd_asset = Asset.objects.filter(code='USD').first()
        btc_wallet = Wallet.objects.get(user=user, asset=btc_asset)
        usd_wallet = Wallet.objects.get(user=user, asset=usd_asset)
        
        current_price = float(cache.get('market_prices', {}).get('BTC', 0))
        if current_price == 0: return HttpResponse('<p class="text-gray-500">[OFFLINE]</p>')

        # 1. INITIALIZE SESSION (ISOLATED)
        if 'ai_session_active' not in request.session:
            request.session['ai_session_active'] = True
            request.session['ai_start_cash'] = float(usd_wallet.balance)
            request.session['ai_pos_size'] = 0.0 # Only tracks what the BOT buys/sells
            request.session['ai_trade_pnl'] = 0.0
            request.session['ai_last_price'] = current_price
        
        trade_pnl = request.session.get('ai_trade_pnl', 0.0)
        pos_size = request.session.get('ai_pos_size', 0.0)
        last_price = request.session.get('ai_last_price', current_price)
        start_cash = request.session.get('ai_start_cash')

        # 2. MARK-TO-MARKET ALPHA (Only on session position)
        price_change = current_price - last_price
        trade_pnl += (pos_size * price_change)

        # 3. DECISION
        trades = Trade.objects.filter(buy_order__asset=btc_asset).order_by('-timestamp')[:30]
        import pandas as pd
        trades_df = pd.DataFrame(list(trades.values('price')))
        if not trades_df.empty: trades_df['price'] = trades_df['price'].apply(float)
        
        engine = B2C2QuantEngine()
        action = engine.decide_live_action(current_price, trades_df, pos_size)
        
        # 4. EXECUTE
        OrderService.execute_quant_trade(user=user, asset_code="BTC", side=action['side'], amount=str(action['amount']))
        
        # Update session tracking
        if action['side'] == 'BUY': request.session['ai_pos_size'] = pos_size + action['amount']
        else: request.session['ai_pos_size'] = pos_size - action['amount']

        request.session['ai_trade_pnl'] = trade_pnl
        request.session['ai_last_price'] = current_price
        request.session.modified = True 
        
        # 5. ISOLATED SESSION EQUITY PNL
        # (Current Cash - Start Cash) + (Current Session BTC * Current Price)
        cash_change = float(usd_wallet.balance) - start_cash
        session_equity_pnl = cash_change + (request.session['ai_pos_size'] * current_price)
        
        now = timezone.now().strftime('%H:%M:%S')
        a_class = "text-green-500" if trade_pnl >= 0 else "text-hackerRed"
        p_class = "text-green-500" if session_equity_pnl >= 0 else "text-hackerRed"
        
        html = f"""
        <div class="border-l-2 border-green-500 pl-2 py-1 mb-1 bg-green-900/10 text-[10px] font-mono">
            <div class="flex justify-between">
                <span class="text-gray-500">[{now}] ISOLATED_SESSION_MODE</span>
                <span class="text-green-400 font-bold">POS: {request.session['ai_pos_size']:.2f} BTC</span>
            </div>
            <div class="flex justify-between">
                <span class="text-white font-bold">>> {action['side']} {action['amount']} BTC</span>
                <span class="{a_class} font-bold">ALPHA: ${trade_pnl:,.2f}</span>
            </div>
            <div class="text-[8px] text-gray-400 uppercase">REASON: {action['reason']} | CASH_CHG: ${cash_change:,.2f}</div>
            <div id="trade-pnl-val" hx-swap-oob="true" class="text-lg {a_class} font-bold tabular-nums">${trade_pnl:,.2f}</div>
            <div id="total-pnl-val" hx-swap-oob="true" class="text-lg {p_class} font-bold tabular-nums">${session_equity_pnl:,.2f}</div>
        </div>
        """
        return HttpResponse(html)
    except Exception as e: return HttpResponse(f'<div class="text-red-500 text-[9px]">> ERR: {str(e)}</div>')

@login_required
def quant_metrics_htmx_view(request):
    prices = cache.get('market_prices', {})
    fair_price = float(prices.get('BTC', 0.0))
    btc_asset = Asset.objects.filter(code='BTC').first()
    btc_wallet = Wallet.objects.filter(user=request.user, asset=btc_asset).first()
    inventory_q = float(btc_wallet.balance) if btc_wallet else 0.0
    usd_asset = Asset.objects.filter(code='USD').first()
    usd_wallet = Wallet.objects.filter(user=request.user, asset=usd_asset).first()
    usd_balance = float(usd_wallet.balance) if usd_wallet else 0.0
    html = f"""
    <span id="fair-price-val" hx-swap-oob="true">${fair_price:,.2f}</span>
    <span id="inventory-val" hx-swap-oob="true">{inventory_q:,.4f} BTC</span>
    <span id="usd-balance-val" hx-swap-oob="true">${usd_balance:,.2f}</span>
    """
    return HttpResponse(html)

@ensure_csrf_cookie
def get_login_nonce(request): return JsonResponse({'nonce': uuid.uuid4().hex})
def web3_login_view(request): return JsonResponse({'status': 'success'})
@login_required
def run_backtest_htmx_view(request): return HttpResponse('OK')
@login_required
def quant_stats_htmx_view(request): return HttpResponse('OK')
@login_required
def run_ml_optimization_htmx_view(request): return HttpResponse('OK')
def price_htmx_view(request): return HttpResponse('OK')
@login_required
def create_order_htmx_view(request): return HttpResponse('OK')
@login_required
def portfolio_htmx_view(request): return HttpResponse('OK')
@login_required
def order_book_htmx_view(request): return HttpResponse('OK')
@login_required
def accept_order_htmx_view(request, id): return HttpResponse('OK')
@login_required
def my_orders_htmx_view(request): return HttpResponse('OK')
@login_required
def cancel_order_htmx_view(request, id): return HttpResponse('OK')
class PortfolioView(APIView):
    def get(self, request):
        wallets = Wallet.objects.filter(user=request.user)
        return Response(WalletSerializer(wallets, many=True).data)
class CreateOrderView(APIView):
    def post(self, request):
        ser = OrderCreateSerializer(data=request.data)
        if ser.is_valid():
            try:
                order = OrderService.create_order(request.user, ser.validated_data['asset_code'], ser.validated_data['side'], ser.validated_data['amount'], ser.validated_data['price'])
                return Response({"status": "success", "order_id": order.id}, status=status.HTTP_201_CREATED)
            except ValueError as e: return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
