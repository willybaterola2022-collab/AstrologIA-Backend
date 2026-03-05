from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import stripe
from app.config import settings

# 1. Configuración de Stripe
# Para producción, se leerá desde .env: STRIPE_SECRET_KEY
stripe.api_key = getattr(settings, "stripe_secret_key", "sk_test_PLACEHOLDER")

router = APIRouter()

class CheckoutRequest(BaseModel):
    product_id: str  # Ej: 'cosmic_blueprint_79'
    success_url: str
    cancel_url: str

@router.post("/checkout")
def create_checkout_session(req: CheckoutRequest):
    """
    IMPORTANTE: Genera la ventana de pago de Stripe.
    Lovable llamará a esto para llevar al usuario a poner su tarjeta.
    """
    try:
        # Precios hardcodeados para el MVP (Luego se puede sacar de BD)
        products = {
            "cosmic_blueprint": {"name": "Cosmic Blueprint (Rockstar)", "price": 7900}, # Centavos
            "hub_shadow": {"name": "Hub Shadow", "price": 4900},
            "hub_match": {"name": "Hub Match VIP", "price": 3900}
        }
        
        if req.product_id not in products:
            raise HTTPException(status_code=400, detail="Producto no encontrado")
            
        product = products[req.product_id]
        
        # Crear sesión en Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": product["name"],
                    },
                    "unit_amount": product["price"],
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            # metadata={"user_id": user_id} # Aquí pasaremos el ID para desbloquear luego
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    IMPORTANTE: El Robot de Stripe llama a esta URL cuando el pago es exitoso.
    Desde aquí modificamos en Supabase al usuario de 'Gratis' a 'Premium'.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = getattr(settings, "stripe_webhook_secret", "whsec_PLACEHOLDER")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Firma inválida")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Aquí el servidor se conectará a Supabase en Fase 3 y actualizará el RLS.
        # supabase.table('users').update({'has_cosmic_blueprint': True}).eq('id', session.metadata.user_id).execute()
        print(f"💰 PAGO EXITOSO: Desbloqueando producto para el usuario")

    return {"status": "success"}
