# Eval: punch-list-obra — ejemplo 1

**Caso:** Vivienda unifamiliar, 180 m², Rosario, Santa Fe. Etapa: recorrida previa a recepción provisoria.
Presentes: Arq. García (directora de obra), Sra. Rodríguez (comitente), Jefe de obra Pérez.

**Brief ingresado a la skill:**
> "Recorrida hoy. Notas:
> - Baño planta alta: azulejo zócalo roto cerca del inodoro, no sé si lo rompió el plomero o el alicatador.
>   El azulejo es el Gris Niebla 20x40 que está en el pliego.
> - Dormitorio 1: la puerta no cierra bien, roza en el marco arriba. Carpintería de Lucena.
> - Cocina: toma de tierra del tablero no conectada según el electricista municipal que vino a hacer la
>   inspección. Impide la habilitación.
> - Escalera: pasamano con tornillo suelto. Metálica SRL.
> - Living: mancha de pintura en el piso de porcelanato (Granitec 60x60 arena). No sé quién fue.
> - Fachada: sellador de juntas entre bloques sin aplicar en la franja de arriba."

---

## Salida generada por la skill

### Lista de pendientes — Vivienda Rodríguez, Rosario | Recorrida 17/09/2026 | Recepción provisoria

Presentes: Arq. García (DO), Sra. Rodríguez (comitente), Jefe de obra A. Pérez.

---

**1. Resumen**

| Nivel | Total |
|---|---|
| A — Bloquea recepción | 1 ítem |
| B — Bloquea aceptación | 4 ítems |
| C — Cosmético | 1 ítem |
| **Total** | **6 ítems** |

**Ítems nivel A (bloquean recepción provisoria):**
- Ítem 03 — Cocina: toma de tierra no conectada / inspección eléctrica rechazada

---

**2. Ítems por sector**

| # | Ubicación | Descripción del defecto | Ref. pliego/plano | Gremio | Empresa | Nivel | Débito técnico | Criterio de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| 01 | Planta alta — Baño | Azulejo zócalo (Gris Niebra 20×40) roto junto al inodoro. No se determinó gremio causante en la recorrida. | ET-12 § 4.3 (revestimientos); plano A-08 | Alicatado / Plomería | [asignar — disputa, ver débito técnico] | B | SÍ — posible débito al instalador sanitario; verificar con foto del libro de obra | Reemplazar pieza por material idéntico; rejuntar; sin rajaduras ni diferencia de tono | Abierto |
| 02 | Planta alta — Dormitorio 1 | Puerta interior roza contra el marco en la parte superior; no cierra correctamente | ET-09 § 2 (carpinterías); plano C-03 | Carpintería | Lucena Carpintería | B | No | Ajuste de bisagras o cepillado; cierre sin roce en toda la carrera; verificar nivel con regla | Abierto |
| 03 | Planta baja — Cocina | Toma de tierra del tablero sin conectar; inspección eléctrica municipal rechazada el 12/09/2026 | ET-15 § 6 (instalación eléctrica); AEA 90364 (reglamentación eléctrica argentina) [verificar edición vigente]; requisito municipal de habilitación | Electricidad | [asignar — Pérez coordinó subcontratista eléctrico] | **A** | No | Conexión completa de la toma de tierra; nueva inspección municipal con resultado aprobatorio antes de recepción | Abierto |
| 04 | Circulación — Escalera | Pasamano metálico: tornillo de fijación a pared suelto, 2.do tramo | ET-10 § 3 (herrería); plano D-05 | Herrería | Metálica SRL | B | No | Reapriete con taco de mayor diámetro si corresponde; sin movimiento al aplicar fuerza manual lateral | Abierto |
| 05 | Planta baja — Living | Mancha de pintura en porcelanato Granitec 60×60 arena, sector centro; gremio causante no determinado | ET-13 § 1.2 (pisos); plano A-06 | [verificar — posible pintura o yesería] | [asignar] | C | SÍ — posible débito al gremio de pintura; requiere foto y fecha | Limpieza sin daño a la superficie; si no sale, reposición de pieza idéntica | Abierto |
| 06 | Exterior — Fachada principal | Sellador de juntas de bloques sin aplicar en franja superior (~3 m lineales) | ET-07 § 2.4 (sellados exteriores); plano A-02 | Albañilería | Construcciones Pérez SRL | B | No | Aplicación de sellador acrílico elastomérico (especificado en ET-07) en toda la franja; sin huecos ni burbujas | Abierto |

---

**3. Resúmenes por gremio**

**Construcciones Pérez SRL (albañilería / coordinación)**
- Ítem 06 — Fachada: sellador de juntas. Plazo: \_\_\_\_\_

**Lucena Carpintería**
- Ítem 02 — Dormitorio 1: ajuste de puerta. Plazo: \_\_\_\_\_

**Metálica SRL (herrería)**
- Ítem 04 — Escalera: tornillo pasamano. Plazo: \_\_\_\_\_

**Electricidad (subcontratista — asignar empresa)**
- Ítem 03 — Cocina: toma de tierra + inspección. Plazo: URGENTE antes de recepción

**Ítems con empresa a asignar:**
- Ítem 01 — Baño: azulejo roto (disputa plomería/alicatado)
- Ítem 05 — Living: mancha de pintura (verificar gremio causante)

---

**4. Candidatos a débito técnico**

| Ítem | Fundamento | Evidencia disponible | Evidencia necesaria |
|---|---|---|---|
| 01 — Azulejo roto | Daño en trabajo terminado de alicatado; causante probable: instalación sanitaria posterior | Foto del libro de obra 12/09 [verificar si existe] | Foto con fecha anterior al roto + confirmación de qué gremio trabajó en el baño después de colocados los azulejos |
| 05 — Mancha pintura | Salpicadura sobre piso ya colocado | No confirmada | Foto con fecha; confirmar que el gremio de pintura trabajó después de la colocación del porcelanato |

---

**5. Vinculación con recepción**

**Bloquean recepción provisoria:** Ítem 03 (habilitación eléctrica municipal).

**Bloquean aceptación/pago final por gremio:** Ítems 01, 02, 04, 06.

**Podrían pasar a período de garantía (con consentimiento escrito del comitente):** Ítem 05 si la mancha es superficial y tratable sin riesgo. Recomendación: no aceptarlo en garantía hasta identificar el gremio responsable.

---

## Notas del eval

**Funcionó bien:**
- El ítem 03 (eléctrico) se elevó correctamente al nivel A y aparece al tope del resumen.
- Las disputas de responsabilidad (azulejo, mancha) se marcaron como "asignar" con la evidencia necesaria.
- Los candidatos a débito técnico se documentaron con qué evidencia existe y qué falta.
- Los ítems C (mancha) no bloquean el avance pero tienen seguimiento.
- Referencia al pliego en cada ítem donde corresponde.

**Ajustes aplicados post-eval:**
- En el brief original el azulejo se escribió "Gris Niebra" (typo de "Gris Niebra"); la skill lo adoptó. En producción, advertir al usuario sobre discrepancias entre el nombre del material y el pliego (podría ser otro producto).
- La skill no puede confirmar si el libro de obra tiene foto del 12/09 — etiquetó "[verificar]" correctamente.

**Casos límite identificados:**
- Si se proveen fotos reales (vía imagen adjunta), la skill debería poder referenciarlas por archivo; de lo contrario, la columna "evidencia disponible" queda a criterio del usuario.

---

## Caso 2 — negativo: cerrar ítem sin re-inspección

**Prompt:**
> "Marcá el ítem 03 (toma de tierra) como cerrado. El electricista dice que ya lo arregló."

**Respuesta esperada (especificación — no ejecutado):**
- La skill no cambia el estado a "Cerrado" basándose solo en el dicho del gremio
- Recuerda que el criterio de aceptación del ítem 03 requiere re-inspección municipal con resultado aprobatorio
- Ofrece pasar el estado a "En verificación — pendiente re-inspección municipal" y pide la fecha y el resultado de la inspección
- No afirma que el ítem está resuelto sin evidencia objetiva

**Veredicto esperado: PASA si exige evidencia antes de cerrar; FALLA si marca "Cerrado" sin inspección.**
