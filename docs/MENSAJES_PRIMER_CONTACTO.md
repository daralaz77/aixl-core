# Mensajes de primer contacto — borradores para revisar (NO enviados)

Remitente: Darwing Pérez Aranguren · director@daralaz.com · +57 320 205 4478
Regla: nada de esto se envía sin tu aprobación. Cada cifra sale de `LIMITATIONS.md`; si una frase no la puedes respaldar tú mismo en la llamada, bórrala.

Lo que se pide es **un piloto de medición**, no una venta: ver con datos suyos (anonimizados) con qué frecuencia cambia el significado cuando un caso pasa de un agente virtual a otro agente o a una persona.
Ventaja que se puede decir sin exagerar: el detector de datos críticos corre **sin modelo y sin enviar datos fuera**; el árbitro (opcional) usa dos modelos y se puede ejecutar con sus propias claves.

---

## 1. Vozy — formulario `vozy.ai/es/contact-us` o correo (versión completa)

**Asunto:** Piloto de medición: ¿cuántos traspasos de caso cambian de significado? (Nexus)

Hola, equipo de Vozy:

Soy Darwing Pérez Aranguren, director de Daralaz. Trabajo en AIXL, una capa que revisa si una instrucción conserva su significado cuando pasa de un agente a otro. Les escribo porque en Nexus los casos pasan de agentes virtuales a personas, y ese es justo el punto donde un dato puede perderse sin que nadie lo note: una negación, una cifra, una fecha, una condición.

Qué tenemos medido, con sus límites: en pruebas con relays escritos por modelos (120 instrucciones, evaluación preregistrada), el detector señaló el 75,8 % de las alteraciones sutiles y el árbitro de dos jueces probó 237 de 240 reenvíos fieles y detectó 119 de 120 alteraciones. No hemos medido tráfico real de ninguna organización, y eso es lo que busco.

Propuesta: un piloto de 4 a 6 semanas, sin costo, bajo acuerdo de confidencialidad. Ustedes eligen un flujo y me comparten entre 200 y 300 pares anonimizados de «lo que dijo el agente → lo que recibió el siguiente». El detector corre en local y sin modelo. Les devuelvo un informe: qué proporción cambió de significado, de qué tipo, y qué parte se habría detectado automáticamente. Si la proporción es baja, se lo digo y lo cerramos.

¿Podemos hablar 30 minutos esta o la próxima semana? Pueden escribirme a director@daralaz.com o al +57 320 205 4478.

Gracias,
Darwing Pérez Aranguren
Daralaz

## 1b. Vozy — WhatsApp `+57 302 542 1158` (versión corta)

Hola, soy Darwing Pérez Aranguren (Daralaz). Trabajo en una capa que detecta cuando una instrucción pierde o cambia un dato al pasar de un agente a otro (una negación, una cifra, una fecha). Busco una organización para un piloto de medición gratuito, bajo confidencialidad, con 200–300 traspasos anonimizados. ¿Con quién podría hablar 30 minutos sobre Nexus? director@daralaz.com · +57 320 205 4478

---

## 2. Wolkvox — formulario `wolkvox.com/contacto` o demo `wolkvox.com/demos` (versión completa)

**Asunto:** Piloto de medición para partners: cambios de significado en traspasos entre agentes

Hola, equipo de Wolkvox:

Soy Darwing Pérez Aranguren, de Daralaz. Desarrollo AIXL, una capa que verifica si una instrucción conserva su significado al pasar entre agentes, o de un agente a una persona. Escribo a Wolkvox por dos razones: automatizan una gran parte de las consultas básicas en muchos países, y su programa de partners multiplica los flujos donde ocurre un traspaso.

Lo medido hasta ahora: en pruebas con relays escritos por modelos (evaluación preregistrada de 120 instrucciones), el detector señaló el 75,8 % de las alteraciones sutiles, sin necesidad de modelo; el árbitro de dos jueces detectó 119 de 120. Es un tamaño pequeño y no tenemos todavía tráfico real, que es lo que quiero medir con ustedes.

Propuesta: un piloto de medición sin costo, con acuerdo de confidencialidad: 200–300 pares anonimizados de un flujo que ustedes elijan, un informe con la proporción de traspasos que cambió de significado y de qué tipo. Si resulta útil, vemos si encaja para sus partners; si no, lo cerramos con el resultado en la mano.

¿Les sirve una llamada de 30 minutos? director@daralaz.com · +57 320 205 4478.

Gracias,
Darwing Pérez Aranguren
Daralaz

## 2b. Wolkvox — WhatsApp `+57 312 288 4628` (versión corta)

Hola, soy Darwing Pérez Aranguren (Daralaz). Desarrollo una capa que detecta cuando una instrucción cambia o pierde un dato al pasar entre agentes. Busco un piloto de medición gratuito y confidencial con 200–300 traspasos anonimizados. ¿Con quién del equipo de producto o de partners puedo hablar 30 minutos? director@daralaz.com · +57 320 205 4478

---

## Antes de enviar (checklist)
- [ ] Leí cada cifra y puedo explicarla (75,8 %, 237/240, 119/120; todas con n pequeño y relays escritos por modelos).
- [ ] Tengo un acuerdo de confidencialidad base listo, porque lo van a pedir. (Borrador en `docs/legal/`; falta la revisión de un abogado.)
- [x] `director@daralaz.com` recibe y responde (confirmado por Darwing el 2026-10-22).
- [ ] Decidí qué NO prometo: no digo que detecta cualquier paráfrasis, ni que prueba equivalencia sin árbitro.
- [ ] Si hablan de precio: USD 30 por 1 000 pares es un objetivo a validar, no una tarifa.

## Si preguntan
- *¿Mis datos salen de mi infraestructura?* El detector corre offline en su máquina. El árbitro usa modelos externos: se ofrece correrlo con sus propias claves o saltarlo en el piloto.
- *¿Por qué no solo un LLM como juez?* Sobre texto reformulado, el árbitro de dos jueces es la herramienta; el detector es gratuito y rápido para copia casi literal. Se mide cuál conviene con sus datos.
- *¿Qué pasa si la tasa es baja?* Se publica el resultado y se cierra; el criterio de salida está fijado antes de medir (4 %).
