from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import OrderService
from .models import Wallet, Asset
from .serializers import OrderCreateSerializer, WalletSerializer
from django.http import HttpResponse, JsonResponse
from django.core.cache import cache
from .models import Order # Asegúrate de importar Order
from django.contrib.auth import get_user_model, login, authenticate # <--- Asegura login y authenticate
from django.views.decorators.csrf import ensure_csrf_cookie # <--- ¡ESTA FALTABA!
import uuid # <--- Para el nonce
import json # <--- Para leer el body del request
# --- IMPORTANTE: Agrega estos para la criptografía ---
from eth_account.messages import encode_defunct
from eth_account import Account
# --- VISTAS DEL DASHBOARD ---

def dashboard_view(request):
    
    # 1. ELIMINAMOS LA LÍNEA TRAIDORA (user = ...first())
    # Ahora usaremos 'request.user', que es el usuario de la sesión actual (Tu Wallet)
    
    available_assets = Asset.objects.filter(is_crypto=True)
    
    # 2. Buscamos las wallets del usuario ACTUAL (request.user)
    wallets = Wallet.objects.filter(user=request.user, balance__gt=0)
    
    context = {
        # No hace falta pasar 'user' explícitamente, Django ya lo inyecta.
        # Pero si quieres asegurarte, pasas request.user, NO el .first()
        'assets': available_assets,
        'wallets': wallets
    }
    return render(request, 'trading/dashboard.html', context)
# --- VISTAS HTMX ---

def price_htmx_view(request):
    """Devuelve una GRILLA HTML con todos los precios"""
    prices = cache.get('market_prices') # Ahora es un diccionario {'BTC': 95000, 'ETH': 2500}
    
    if not prices:
        return HttpResponse('<div class="text-hackerRed">CONNECTING TO BINANCE...</div>')
    
    # Construimos el HTML dinámicamente
    html_content = '<div class="grid grid-cols-2 gap-4">'
    
    for code, price in prices.items():
        # Estilo condicional (rojo/verde) se podría agregar comparando con precio anterior
        # Por ahora simple:
        html_content += f"""
        <div class="flex justify-between border-b border-hackerRed/30 pb-1">
            <span class="text-hackerRed font-bold">{code}</span>
            <span class="text-white">${price:,.2f}</span>
        </div>
        """
    
    html_content += '</div>'
    return HttpResponse(html_content)

def create_order_htmx_view(request):
    """Esta ahora es solo para QUICK TRADE con el BOT"""
    from django.contrib.auth import get_user_model
    user = request.user

    if request.method == 'POST':
        try:
            order_type = request.POST.get('order_execution_type') # 'INSTANT' o 'LIMIT'
            
            if order_type == 'INSTANT':
                # Ejecuta contra el LP con 1% spread
                OrderService.execute_lp_trade(
                    user=user,
                    asset_code=request.POST.get('asset_code'),
                    side=request.POST.get('side'),
                    amount=request.POST.get('amount')
                )
                return HttpResponse('<div class="text-green-500">> INSTANT TRADE EXECUTED (1% SPREAD APPLIED).</div>')
            
            elif order_type == 'LIMIT':
                # Crea orden P2P
                OrderService.create_p2p_limit_order(
                    user=user,
                    asset_code=request.POST.get('asset_code'),
                    side=request.POST.get('side'),
                    amount=request.POST.get('amount'),
                    price=request.POST.get('price')
                )
                return HttpResponse('<div class="text-blue-500">> ORDER PLACED IN BOOK. WAITING FOR MATCH...</div>')

        except ValueError as e:
            return HttpResponse(f'<div class="text-hackerRed">> ERROR: {str(e)}</div>')
    return HttpResponse('')

def portfolio_htmx_view(request):
    """Devuelve el HTML actualizado de las billeteras"""
    from django.contrib.auth import get_user_model
    user = request.user
    
    # Traemos TODAS las billeteras que tengan algo de saldo (mayor a 0)
    # y ordenamos para que USD salga siempre primero.
    wallets = Wallet.objects.filter(user=user, balance__gt=0).order_by('asset__code')
    
    return render(request, 'trading/partials/portfolio_partial.html', {'wallets': wallets})

# ... (Las clases APIView de DRF se quedan igual) ...
class PortfolioView(APIView):
    def get(self, request):
        from django.contrib.auth import get_user_model
        user = request.user 
        wallets = Wallet.objects.filter(user=user)
        serializer = WalletSerializer(wallets, many=True)
        return Response(serializer.data)

class CreateOrderView(APIView):
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            from django.contrib.auth import get_user_model
            user = request.user
            try:
                order = OrderService.create_order(
                    user=user,
                    asset_code=data['asset_code'],
                    side=data['side'],
                    amount=data['amount'],
                    price=data['price']
                )
                return Response({"status": "success", "order_id": order.id}, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # --- VISTA NUEVA: ORDER BOOK (P2P) ---
def order_book_htmx_view(request):
    """Muestra todas las órdenes PENDING de otros usuarios"""
    from django.contrib.auth import get_user_model
    current_user = request.user
    
    # Buscamos órdenes pendientes que NO sean mías
    pending_orders = Order.objects.filter(status='PENDING').exclude(user=current_user).order_by('-created_at')
    
    return render(request, 'trading/partials/order_book_partial.html', {'orders': pending_orders})

# --- VISTA NUEVA: ACEPTAR ORDEN P2P ---
def accept_order_htmx_view(request, order_id):
    from django.contrib.auth import get_user_model
    user = request.user
    
    try:
        OrderService.execute_p2p_match(user, order_id)
        # Devolvemos un mensaje y header para recargar el book y el portafolio
        response = HttpResponse('<div class="text-green-500">> P2P MATCH SUCCESSFUL!</div>')
        response['HX-Trigger'] = 'updatePortfolio, updateOrderBook'
        return response
    except Exception as e:
         return HttpResponse(f'<div class="text-hackerRed">> ERROR: {str(e)}</div>')
# --- VISTA: MIS ÓRDENES ABIERTAS ---
def my_orders_htmx_view(request):
    from django.contrib.auth import get_user_model
    user = request.user
    
    # Solo mostramos las PENDING mías
    my_orders = Order.objects.filter(user=user, status='PENDING').order_by('-created_at')
    
    return render(request, 'trading/partials/my_orders_partial.html', {'orders': my_orders})

# --- VISTA: ACCIÓN DE CANCELAR ---
def cancel_order_htmx_view(request, order_id):
    from django.contrib.auth import get_user_model
    user = request.user
    
    try:
        OrderService.cancel_order(user, order_id)
        # HX-Trigger avisa al frontend que recargue la tabla de "Mis Órdenes"
        response = HttpResponse('<div class="text-yellow-500">> ORDER CANCELLED.</div>')
        response['HX-Trigger'] = 'updateMyOrders' 
        return response
    except ValueError as e:
        return HttpResponse(f'<div class="text-hackerRed">> ERROR: {str(e)}</div>')

@ensure_csrf_cookie
def get_login_nonce(request):
    """Genera un Nonce SIMPLE (Solo UUID) para evitar errores de encoding"""
    
    # CAMBIO: Usamos solo el UUID hex limpio. Sin espacios, sin \n.
    nonce = uuid.uuid4().hex 
    
    request.session['login_nonce'] = nonce
    request.session.modified = True 
    
    print(f"🎫 NONCE SIMPLIFICADO: {nonce}")
    
    return JsonResponse({'nonce': nonce})

# trading/views.py

from django.contrib.auth import logout # <--- ¡IMPORTANTE! Agrega este import arriba

def web3_login_view(request):
    """Login Web3: Limpieza total de sesión previa + Login nuevo"""
    
    if request.method == "POST":
        # 1. AMNESIA FORZADA: Borramos cualquier sesión existente (Admin, User, etc)
        # Esto elimina la cookie 'sessionid' vieja inmediatamente.
        if request.user.is_authenticated:
            print(f"👋 Cerrando sesión anterior de: {request.user.username}")
            request.session.flush()
        
        # Limpiamos la sesión pero mantenemos el nonce temporalmente si es necesario, 
        # o mejor aún, recuperamos el nonce ANTES de hacer logout si estaba en la sesión.
        # PROBLEMA: Si hago logout, pierdo el 'login_nonce'.
        # SOLUCIÓN: Leemos el nonce primero, luego logout, luego verificamos.
        
        try:
            # A. Leer datos entrantes
            data = json.loads(request.body)
            address = data.get('address', '').lower()
            signature = data.get('signature')
            
            # B. Recuperar Nonce (Antes de borrar la sesión)
            nonce = request.session.get('login_nonce')
            
            print("\n📩 PROCESANDO LOGIN WEB3...")
            print(f"   - Address: {address}")
            
            if not nonce:
                 print("   ❌ ERROR: No hay nonce (Sesión expirada o borrada antes de tiempo)")
                 return JsonResponse({'error': 'SESSION_EXPIRED_REFRESH_PAGE'}, status=400)

            # C. Criptografía
            msg = encode_defunct(text=nonce)
            recovered_address = Account.recover_message(msg, signature=signature).lower()
            
            if recovered_address == address:
                print(f"   ✅ FIRMA VÁLIDA. Address: {recovered_address}")
                
                # D. AHORA SÍ: LOGOUT EXPLÍCITO para matar al Admin "WHITEALFA"
                # Guardamos el backend que vamos a usar antes de limpiar
                logout(request) 
                # Ahora request.user es AnonymousUser y la sesión está limpia
                
                # E. Buscar o Crear Usuario Wallet
                User = get_user_model()
                user, created = User.objects.get_or_create(username=address)
                
                if created:
                    print("   ✨ USUARIO NUEVO CREADO")
                    # Opcional: Darle Assets iniciales
                    # from .models import Wallet, Asset
                    # usd, _ = Asset.objects.get_or_create(code='USD')
                    # Wallet.objects.create(user=user, asset=usd, balance=0)
                
                # F. Login Limpio
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                print(f"   🚀 SESIÓN INICIADA PARA: {user.username}")
                
                # --- AGREGAR ESTO: Forzar escritura en Base de Datos ---
                request.session.save() 
                # -------------------------------------------------------

                return JsonResponse({'status': 'success'})
            
            else:
                print("   ❌ FIRMA INVÁLIDA")
                return JsonResponse({'error': 'INVALID_SIGNATURE'}, status=400)
                
        except Exception as e:
            print(f"   💥 EXCEPCIÓN: {str(e)}")
            return JsonResponse({'error': str(e)}, status=400)
            
    return JsonResponse({'error': 'METHOD_NOT_ALLOWED'}, status=405)