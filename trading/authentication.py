from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from eth_account.messages import encode_defunct
from eth_account import Account

class Web3Backend(ModelBackend):
    def authenticate(self, request, address=None, signature=None):
        if not address or not signature:
            return None
        
        nonce = request.session.get('login_nonce')
        if not nonce:
            return None

        # Normalizamos address a minúsculas
        address = address.lower()

        try:
            # --- ESTRATEGIA MULTI-INTENTO ---
            
            # Intento 1: Verificar el texto plano (Lo estándar)
            # MetaMask recibe Hex -> Muestra Texto -> Firma Texto
            msg1 = encode_defunct(text=nonce)
            rec1 = Account.recover_message(msg1, signature=signature).lower()
            
            if rec1 == address:
                print(f"✅ MATCH (Estrategia 1 - Texto Puro)")
                return self.get_or_create_user(address)

            # Intento 2: Verificar asumiendo que MetaMask firmó el HEX literal
            # Convertimos el nonce a hex string manualmente
            nonce_hex = "0x" + "".join("{:02x}".format(ord(c)) for c in nonce)
            msg2 = encode_defunct(text=nonce_hex)
            rec2 = Account.recover_message(msg2, signature=signature).lower()
            
            if rec2 == address:
                print(f"✅ MATCH (Estrategia 2 - Hex Literal)")
                return self.get_or_create_user(address)

            print(f"❌ FALLO CRIPTOGRÁFICO:")
            print(f"   - Esperado: {address}")
            print(f"   - Recup 1 : {rec1}")
            print(f"   - Recup 2 : {rec2}")

        except Exception as e:
            print(f"❌ Excepción Crypto: {e}")
            return None
            
        return None

    def get_or_create_user(self, address):
        User = get_user_model()
        # Creamos usuario con el address como username
        user, created = User.objects.get_or_create(username=address)
        return user