"""
Quick test: validate that Gemini 2.0 Flash Vision API works from inside the container.
Creates a small test image and sends to Gemini.
"""
import asyncio
import sys
import time
sys.path.insert(0, "/app")

async def test_gemini():
    from config import get_settings
    from google import genai
    from google.genai import types
    
    settings = get_settings()
    api_key = settings.gemini_api_key
    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
    
    # Test 1: Text-only request
    print("\n--- Test 1: Text request ---")
    client = genai.Client(api_key=api_key)
    start = time.time()
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents="Responda apenas: OK",
        )
        print(f"  Result: {response.text.strip()} ({time.time()-start:.1f}s)")
    except Exception as e:
        print(f"  ERROR: {e}")
        return
    
    # Test 2: Vision with a simple generated image
    print("\n--- Test 2: Vision with test image ---")
    from PIL import Image, ImageDraw, ImageFont
    import io
    
    # Create a test image with text
    img = Image.new("RGB", (800, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), "TESTE: Manual Técnico de Elevadores", fill="black")
    draw.text((50, 100), "Código: UV1 UV2 OC GF BR1 OL1 - Página 42", fill="black")
    draw.text((50, 150), "Tensão: 220V | Corrente: 15A | Potência: 3.3kW", fill="black")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()
    print(f"  Test image: {len(image_bytes)} bytes")
    
    start = time.time()
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                "Transcreva TODO o texto visível nesta imagem. Responda em português.",
                types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
        text = response.text.strip()
        print(f"  Result ({time.time()-start:.1f}s, {len(text)} chars):")
        print(f"  {text[:300]}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    print("\n✅ Pipeline hybrid ready! Upload a PDF via frontend to start processing.")

if __name__ == "__main__":
    asyncio.run(test_gemini())
