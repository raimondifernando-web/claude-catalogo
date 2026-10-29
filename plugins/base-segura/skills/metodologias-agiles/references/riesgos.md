# Riesgos

Un **riesgo** es algo que **todavía no pasó** y podría afectar el resultado. (Si ya pasó, es un **problema** y se resuelve, no se gestiona.)
Sirve en cualquier proyecto, campaña, negociación o apuesta de impacto. Dos herramientas: el **pre-mortem** (para encontrar riesgos antes de empezar) y
el **registro de riesgos** (para seguirlos durante el trabajo).

## 1. Pre-mortem (antes de lanzar algo que importa)

Imaginá que **ya fracasó** y respondé: ¿por qué? Pensar «hacia atrás» saca a la luz lo que nadie quiere decir.

1. Reunir al equipo: «Es dentro de unos meses y esto salió mal. Escriban en silencio todas las razones».
2. Juntar y clasificar cada riesgo:
   - **Tigre**: riesgo real que va a morder.
   - **Tigre de papel**: preocupa a alguien, pero no es real.
   - **Elefante**: algo que nadie nombra y podría ser real. El más valioso de sacar a la luz.
3. Para tigres y elefantes, decidir la **urgencia**: *bloquea el lanzamiento* · *se arregla en 30 días* · *se vigila*.
4. Armar un plan **solo para los que bloquean**: riesgo · qué hacemos · quién · para cuándo.
Salida: una tabla de 4 columnas y la decisión «se lanza / se lanza cuando…».

## 2. Registro de riesgos

Una tabla viva, una fila por riesgo:

| # | Riesgo (causa → qué pasaría) | Probabilidad (1-5) | Impacto (1-5) | Puntaje | Respuesta | Dueño | Disparador | Estado |
|---|---|---|---|---|---|---|---|---|

- **Redactar bien**: «Si [causa], entonces [consecuencia]» («Si el proveedor no entrega antes del 15, la campaña sale sin material»). «Riesgo de retrasos» no dice nada.
- **Puntaje** = probabilidad × impacto (1 a 25). Definí **antes** qué puntaje es alto, medio y bajo, y escribilo en la hoja.
- **Dueño**: una persona, no un equipo.
- **Disparador**: la señal temprana que avisa que el riesgo se está activando («el proveedor no confirmó a 10 días»). Es lo que permite actuar a tiempo.

### Las cuatro respuestas

| Respuesta | Qué es | Cuándo |
|---|---|---|
| **Evitar** | Cambiar el plan para que el riesgo no exista | Impacto muy alto y evitarlo cuesta poco |
| **Mitigar** | Bajar la probabilidad o el impacto | Lo más común: se puede hacer algo razonable |
| **Transferir** | Pasárselo a otro (seguro, contrato, proveedor) | Otro lo maneja mejor o más barato |
| **Aceptar** | Saberlo y no hacer nada ahora (o tener un plan por si pasa) | Bajo impacto o muy poco probable |

## 3. Cómo mantenerlo

- Revisarlo **en una reunión corta fija** (la semanal o la revisión del ciclo): ¿apareció algún disparador? ¿cambió algún puntaje? ¿hay riesgos nuevos?
- **Escalar** cuando un riesgo pasa de cierto puntaje o su disparador se activa: a quien puede decidir (ver `roles-y-decisiones.md`). Definí el umbral al armar el registro.
- **Sesgos a vigilar**: *optimismo* (subestimar probabilidades propias), *anclaje* (quedarse con el primer número), *efecto del grupo* (nadie contradice al jefe). Las tarjetas anónimas del pre-mortem ayudan.
- **No inventes plata ni probabilidades**: un valor monetario esperado (probabilidad × costo) solo se calcula si alguien aporta datos reales de ambos. Con la escala 1-5, el producto es un **puntaje para ordenar**, no un monto en pesos.
- Al cerrar el proyecto, lo que pasó y lo que no alimenta el próximo pre-mortem.
