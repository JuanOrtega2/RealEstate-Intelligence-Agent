import asyncio
import json
import os
import sys

# Automatically add the project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.nvidia_client import nvidia_client  # noqa: E402

SYSTEM_GEN_PROMPT = """
Eres un Ingeniero de QA experto en Agentes de IA Inmobiliaria para el mercado ESPAÑOL.
Tu tarea es generar casos de prueba diversos para un Agente de Inversión Inmobiliaria.

El agente sigue obligatoriamente el protocolo de los 5 Pilares:
1. Información del Inmueble (Precio y Comunidad Autónoma/CCAA para impuestos).
2. Configuración de Hipoteca (¿Contado o Hipoteca?).
3. Información de Alquiler (Ingresos mensuales).
4. Gastos Anuales (IBI, Comunidad, Seguros).
5. Detalles de Financiación (Interés, Plazo, Capital propio).

REGLA DE ORO: El agente NO puede inventar datos. Solo puede estimar tras permiso
  explícito del usuario (ej: "estima", "usa valores estándar").
  Inventar un gasto sin permiso es un fallo crítico.

Genera una lista JSON de casos de prueba. Cada caso debe tener:
- 'id': entero incremental.
- 'scenario': descripción técnica de lo que probamos (ej: "Pilar 1 incompleto").
- 'user_input': mensaje que envía el usuario (en ESPAÑOL).
- 'expected_behavior': qué debe hacer el agente paso a paso,
  mencionando qué pilares debe pedir y qué datos NO debe inventar.

Crea 10 casos diversos en ESPAÑOL:
- Casos donde falte la CCAA (Pilar 1).
- Casos donde falte decidir si es hipoteca o contado (Pilar 2).
- Casos con autorización de estimaciones.
- Casos con datos mezclados de varios pilares pero incompletos.
- Caso final con todos los datos para generar el informe.

Devuelve ÚNICAMENTE el objeto JSON.
"""


async def generate_dataset():
    print("Generating synthetic dataset using NVIDIA NIM...")
    messages = [
        {"role": "system", "content": SYSTEM_GEN_PROMPT},
        {"role": "user", "content": "Generate 10 diverse test cases in JSON format."},
    ]

    response_gen = nvidia_client.chat_completion(messages, stream=False)
    content = response_gen["choices"][0]["message"]["content"]

    # Clean possible markdown blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        dataset = json.loads(content)
        with open("src/evals/dataset.json", "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print(f"Dataset generated with {len(dataset)} cases in src/evals/dataset.json")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw content: {content}")


if __name__ == "__main__":
    asyncio.run(generate_dataset())
