# 🏠 RealEstate-Intelligence-Agent

**RealEstate-Intelligence-Agent** es un sistema de inteligencia artificial avanzado diseñado para automatizar el análisis de viabilidad de inversiones inmobiliarias. El sistema transforma anuncios y datos desestructurados en estudios financieros detallados y objetivos.

## 🚀 Características del Proyecto

Este proyecto aplica los conceptos fundamentales de ingeniería de IA aprendidos:

- **Extracción Estructurada:** Conversión de anuncios de texto a datos JSON precisos (KPIs inmobiliarios) usando técnicas de *Message Prefilling*.
- **Herramientas Financieras (Tool-Use):** Integración de funciones de cálculo para ROI, impuestos (ITP, IVA) y simulaciones de hipoteca para garantizar precisión matemática.
- **Razonamiento Profundo:** Análisis de riesgo y detección de anomalías en el precio basado en contexto mediante *Thinking Mode*.
- **Marco de Evaluación:** Pruebas sistemáticas (*LLM-as-a-Judge*) para asegurar la fiabilidad de las recomendaciones.

## 🛠️ Tecnologías

- **Lenguaje:** Python 3.11+
- **Modelos:** Compatible con Claude (Anthropic), Gemini (Google) y modelos locales vía Ollama.
- **Orquestación:** Boto3 / LangChain / LiteLLM.

## 📂 Estructura del Proyecto

```text
RealEstate-Intelligence-Agent/
├── src/                # Código fuente del agente (Extracción, Análisis, Tools)
├── data/               # Ejemplos de anuncios y normativa local
├── evals/              # Datasets y reportes de evaluación
└── README.md           # Documentación del proyecto
```

---
> [!NOTE]
> Este proyecto ha sido desarrollado como una implementación práctica de técnicas avanzadas de IA Generativa.
