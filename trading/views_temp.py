@login_required
def execute_live_step_htmx_view(request):
    try:
        user = request.user
        btc_asset = Asset.objects.filter(code='BTC').first()
        usd_asset = Asset.objects.filter(code='USD').first()
        btc_wallet, _ = Wallet.objects.get_or_create(user=user, asset=btc_asset)
        usd_wallet, _ = Wallet.objects.get_or_create(user=user, asset=usd_asset)
        
        inventory_q, usd_balance = float(btc_wallet.balance), float(usd_wallet.balance)
        
        prices = cache.get('market_prices', {})
        current_price = float(prices.get('BTC', 0.0))
        if current_price == 0: return HttpResponse('<p class="text-gray-500">[WAITING_FEED]</p>')

        # 1. INITIALIZE SESSION
        if 'ai_start_equity' not in request.session:
            request.session['ai_start_equity'] = usd_balance + (inventory_q * current_price)
            request.session['ai_trade_pnl'] = 0.0
            request.session['ai_avg_cost'] = current_price
            request.session['ai_pos_size'] = 0.0 
        
        start_equity = request.session.get('ai_start_equity')
        trade_pnl = request.session.get('ai_trade_pnl', 0.0)
        avg_cost = request.session.get('ai_avg_cost', current_price)
        pos_size = request.session.get('ai_pos_size', 0.0)
        current_gamma = request.session.get('ai_gamma', 0.5)

        # 2. MARKET ANALYSIS
        trades = Trade.objects.filter(buy_order__asset=btc_asset).order_by('-timestamp')[:30]
        import pandas as pd
        trades_df = pd.DataFrame(list(trades.values('price')))
        if not trades_df.empty: trades_df['price'] = trades_df['price'].apply(float)
        
        engine = B2C2QuantEngine(skew_coefficient=current_gamma)
        ml = engine.run_adaptive_optimization(trades_df, current_gamma, trade_pnl)
        
        # 3. DECISION
        action = engine.decide_live_action(current_price, trades_df, pos_size, ml['momentum'])
        
        if action['side'] == 'WAIT':
            return HttpResponse(f'<div class="text-gray-600 text-[9px] font-mono">> STEP_IDLE: {action["reason"]}</div>')

        # 4. EXECUTE & PNL LOGIC
        OrderService.execute_lp_trade(user=user, asset_code="BTC", side=action['side'], amount=str(action['amount']))
        
        if action['side'] == 'BUY':
            new_pos = pos_size + action['amount']
            request.session['ai_avg_cost'] = ((avg_cost * pos_size) + (current_price * action['amount'])) / (new_pos if new_pos > 0 else 1)
            request.session['ai_pos_size'] = new_pos
        else: # SELL
            if pos_size > 0:
                realized = (current_price - avg_cost) * action['amount']
                trade_pnl += realized
                request.session['ai_trade_pnl'] = trade_pnl
            request.session['ai_pos_size'] = pos_size - action['amount']

        # 5. PERSIST & RESPOND
        request.session['ai_gamma'] = ml['new_gamma']
        request.session.modified = True 
        
        equity_pnl = (usd_balance + (inventory_q * current_price)) - start_equity
        now = timezone.now().strftime('%H:%M:%S')
        p_class = "text-green-500" if equity_pnl >= 0 else "text-hackerRed"
        a_class = "text-green-500" if trade_pnl >= 0 else "text-hackerRed"
        
        html = f"""
        <div class="border-l-2 border-purple-500 pl-2 py-1 mb-1 bg-purple-900/10 text-[10px] font-mono">
            <div class="flex justify-between">
                <span class="text-gray-500">[{now}] {ml['regime']}</span>
                <span class="text-purple-400 font-bold">Î³={ml['new_gamma']}</span>
            </div>
            <div class="flex justify-between">
                <span class="text-white font-bold">>> {action['side']} {action['amount']} BTC</span>
                <span class="text-blue-400 font-bold">ALPHA: ${trade_pnl:,.2f}</span>
            </div>
            <div class="text-[8px] text-gray-400 uppercase">REASON: {action['reason']} | POS: {request.session['ai_pos_size']:.2f}</div>
            
            <div id="total-pnl-val" hx-swap-oob="true" class="text-lg {p_class} font-bold tabular-nums">${equity_pnl:,.2f}</div>
            <div id="trade-pnl-val" hx-swap-oob="true" class="text-lg {a_class} font-bold tabular-nums">${trade_pnl:,.2f}</div>
        </div>
        """
        return HttpResponse(html)
    except Exception as e:
        return HttpResponse(f'<div class="text-red-500 text-[9px]">> ITERATION_FAILED: {str(e)}</div>')
