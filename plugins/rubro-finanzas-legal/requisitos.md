# Requisitos — rubro-finanzas-legal

- `finanzas-personales-argentina` trae `scripts/calculos.py`: necesita **Python 3** (solo biblioteca estándar). Sin Python, la skill hace las cuentas en la conversación.
- El resto no necesita nada. Todo es orientativo: no reemplaza a un contador ni a un abogado.
- Las 5 skills de análisis de mercado con datos de Yahoo (`earnings-preview`, `earnings-recap`, `estimate-analysis`, `stock-liquidity`, `stock-correlation`) necesitan internet y `uv` (lo instala el actualizador) porque yfinance pide Python 3.10 o más y el de Apple es 3.9. `sepa-strategy` y `options-payoff` pueden usar los datos que le des o el plugin `yfinance`. Son educativas: no operan, no dan consejo de inversión.
- TradingView no viene incluido: su conector oficial es de tu cuenta de claude.ai y exige tu propio plan de pago de TradingView (Essential: 10 consultas por día; uso personal).
