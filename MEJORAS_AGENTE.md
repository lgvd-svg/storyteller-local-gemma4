# 🩸 MEJORAS AL AGENTE DE VAMPIRO: LA MASCARADA 🩸

## Resumen de Mejoras Realizadas

El agente ha sido **completamente rediseñado** para generar respuestas narrativas **INMERSIVAS, DESARROLLADAS y CINÉTICAS**. Las mejoras están enfocadas en profundidad narrativa, coherencia contextual y estimular respuestas prolongadas y detalladas.

---

## 📋 MEJORAS PRINCIPALES

### 1. **Prompt del Sistema RADICALMENTE MEJORADO**
- ✅ **Instrucciones cinematográficas explícitas**: Énfasis en descripción sensorial (sonidos, olores, temperaturas, texturas)
- ✅ **Guía detallada sobre HAMBRE**: Cómo el nivel de Hambre (0-5) afecta el comportamiento y percepción narrativa
- ✅ **Requisito de extensión**: Mínimo 3-4 párrafos por respuesta
- ✅ **Moralidad gris**: Enfatiza que el Mundo de Tinieblas NO tiene respuestas simples
- ✅ **Impacto duradero**: Todas las acciones tienen consecuencias reales

### 2. **Gestión Contextual Avanzada**
La ficha de personaje ahora incluye:
- 📍 **current_location**: Ubicación actual (ej: "Callejón oscuro detrás del Elíseo")
- 🎭 **current_situation**: Descripción dinámica de la situación (ej: "Perseguido. Se oyen pasos")
- 🎯 **objectives**: Objetivos narrativos del personaje
- 🤝 **relationships**: Conexiones con PNJs y estados de relaciones
- 📖 **narrative_history**: Registro de últimos 5 eventos significativos

### 3. **Inyección de Contexto Rica**
Nueva función `build_context_injection()` que antes de cada turno envía:
- Estado del Hambre con **narración interpretativa** (no solo número)
- Estado de salud detallado
- Ubicación y situación actual
- Últimos 3 eventos significativos (para coherencia narrativa)

**Ejemplo de contexto inyectado:**
```
[== ESTADO ACTUAL ==]
📍 Ubicación: Callejón oscuro detrás del Elíseo
🎭 Situación: Perseguido. Se oyen pasos. Alguien te busca
🩸 Hambre: 4/5 - LA BESTIA ACECHA TRAS TUS OJOS...
...
```

### 4. **Seguimiento de Tiradas CINEMATOGRÁFICO**
Cuando el motor ejecuta una tirada, el modelo recibe **instrucciones narrativas específicas** según el resultado:

- **PIFIA BESTIAL**: Instrucciones para describir cómo pierdes el control, cómo emerges la Bestia
- **CRÍTICO DESORDENADO**: Éxito pero salvaje, sin control, brutal
- **ÉXITO CRÍTICO**: Victoria elegante y controlada, detalle cinético
- **ÉXITO NORMAL**: Logro con matices, consecuencias narrativas
- **FRACASO**: Cómo cambian las circunstancias en tu contra, nuevas complicaciones

Cada mensaje de follow-up es **específico y detallado**, no genérico.

### 5. **Nuevas Etiquetas de Motor**
Además de los tags existentes, ahora soporta:
- `[UPDATE_LOCATION(nueva ubicación)]` - El modelo puede cambiar tu ubicación
- `[UPDATE_SITUATION(nueva situación)]` - Actualiza el contexto narrativo

**Ejemplo:**
```
[UPDATE_LOCATION(Azotea del edificio. La lluvia te salpica)]
[UPDATE_SITUATION(Escapando. Tus perseguidores están en el piso inferior)]
[SET_HUNGER(5)]
```

### 6. **Ficha de Personaje Mejorada**
La visualización ahora es mucho más **visual y descriptiva**:
```
============================================================
  📋 ROMU VAL | Clan: Desconocido
============================================================

🩸 HAMBRE: 🩸🩸🩸🌑🌑 (3/5)
💔 SALUD:  [/][/][ ][ ][ ] [/]=Sup, [X]=Agr]
💪 VOLUNTAD: [ ][ ][ ][ ][ ]
🕊️  HUMANIDAD: 7/10

📍 UBICACIÓN: Callejón oscuro
🎭 SITUACIÓN: Perseguido

🎯 OBJETIVOS:
   1. Encontrar a Anita antes del amanecer
   2. Desvelar quién te está utilizando
============================================================
```

### 7. **Interfaz Mejorada**
- ✅ Mensaje de bienvenida teatral y oscuro
- ✅ Instrucciones claras sobre cómo interactuar
- ✅ Mensaje de despedida narrativo cuando terminas
- ✅ Recordatorio de humanidad restante

---

## 🎮 CÓMO INTERACTUAR CON EL AGENTE MEJORADO

### Acciones Simples
```
Jugador: Intento abrir la puerta del edificio sin llamar la atención
```
El Storyteller describirá exactamente qué ocurre, cómo se siente, quién podría verte, etc.

### Cuando Necesita Tirada
```
Storyteller: ...Para deslizarte sin ser visto, necesitaré una tirada de Subterfugio...
[ROLL(pool=6, hunger=2)]
```
El motor procesa automáticamente la tirada y continúa la narrativa.

### Acciones que Cambian la Escena
```
Jugador: Abandono el callejón y me dirijo al próximo Elíseo en el barrio
```
El Storyteller actualizará:
- Tu ubicación
- Quién ves
- Qué peligros acechan
- Cómo ha cambiado tu Hambre

---

## 💡 CONSEJOS PARA APROVECHAR LAS MEJORAS

1. **Sé específico**: En lugar de "Investigo", di "Busco evidencias de lo que sucedió aquí anoche"
2. **Refuerza la emoción**: El contexto inyectado refleja tu estado. Usa eso en tu narración
3. **Prepárate para tiradas**: Cuando pidas hacer algo riesgoso, el Storyteller pedirá dados
4. **Explora la Hambre**: Conforme aumenta, el modelo adaptará la narrativa para que sientas la presión
5. **Crea objetivos**: Menciona tus metas. El Storyteller las usará para tejer la trama

---

## 📊 CAMBIOS TÉCNICOS

### Estructura de Ficha Expandida
```json
{
  "name": "Romu Val",
  "clan": "Desconocido",
  "current_location": "Callejón oscuro",
  "current_situation": "Perseguido",
  "objectives": ["Encontrar a Anita"],
  "relationships": {},
  "narrative_history": ["Despertaste con sangre en las manos"],
  "hunger": 1,
  "humanity": 7,
  "max_health": 20,
  "superficial_damage": 0,
  "aggravated_damage": 0,
  "max_willpower": 5,
  "willpower_damage": 0
}
```

### Funciones Nuevas
- `build_context_injection()` - Construye contexto narrativo rico
- `log_narrative_event()` - Registra eventos significativos

### Mejoras a Funciones Existentes
- `process_engine_tags()` - Ahora soporta UPDATE_LOCATION y UPDATE_SITUATION
- `print_character_status()` - Visualización completamente rediseñada
- `main()` - Interfaz mejorada, mejor flujo narrativo

---

## 🎭 EJEMPLOS DE NARRACIÓN MEJORADA

### Antes (Genérico)
```
Entras al callejón. Está oscuro. Ves a alguien en la distancia.
```

### Después (Cinematográfico)
```
El callejón te envuelve como una tumba de concreto y herrumbre. La lluvia 
cae en diagonal, empapándote los hombros. El olor metálico de sangre - 
SANGRE - llena tus fosas nasales. Tu visión se tiñe de rojo por un momento.

A treinta metros, siluetuada contra las luces de la avenida lejana, hay 
una figura. No se mueve. Espera. SABE que estás aquí.

Tu Hambre crece. 4/5. La Bestia susurra en tu mente: "Es tan débil que 
puedo olerlo".

¿Qué haces?

[UPDATE_LOCATION(Callejón detrás del Elíseo - Noche lluvia)]
[UPDATE_SITUATION(Descubierto. Algo o alguien te acecha)]
[SET_HUNGER(4)]
```

---

## 🔧 PERSONALIZACIONES FUTURAS

Posibles mejoras adicionales:
- Disciplinas vampíricas interactivas
- Sistema de Humanidad más profundo
- Puntos de "presagio" narrativo
- PNJs persistentes con memoria
- Sistema de "marcas" (víctimas anteriores)

---

**El Mundo de Tinieblas nunca fue tan vívido. Que disfrutes tu maldición.**

⚫ 🩸 ⚫
