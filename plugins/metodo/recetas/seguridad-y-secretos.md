---
name: seguridad-y-secretos
triggers: seguridad security credenciales token tokens api key clave secretos login autenticacion passkey password deploy publicar produccion
---
Receta para cualquier trabajo que toque claves, accesos o publicar algo en internet.
1. Las contraseñas, claves y tokens los pone la persona, donde corresponde; Claude trabaja con el NOMBRE de la variable, nunca con el valor (regla 2). Para comprobar que existe, usá una prueba que solo diga sí/no, nunca imprimas el valor.
2. Antes de publicar o poner algo en internet, aplicá la skill `decisiones-tecnicas` (regla 21) y revisá el código con `security-and-hardening` si la tenés.
3. Si una clave se mostró en pantalla o en el chat, tratála como filtrada: hay que rotarla.
4. Un subagente NO hereda estas reglas: repetilas en SU prompt.
