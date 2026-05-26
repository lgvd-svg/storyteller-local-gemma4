# 🎲 REFERENCIA RÁPIDA: TAGS Y MECANISMOS

## TAGS DE MOTOR DISPONIBLES

El Storyteller puede usar estos tags al final de sus mensajes para controlar el motor:

### Gestión de Salud
```
[DAMAGE(type="superficial", amount=X)]    # Daño superficial
[DAMAGE(type="aggravated", amount=X)]     # Daño agravado (más grave)
[HEAL(amount=X)]                           # Curar daño
```

### Gestión de Recursos
```
[SET_HUNGER(X)]                           # Cambiar Hambre (0-5)
[SPEND_WILLPOWER(X)]                      # Gastar Voluntad
```

### Tiradas de Dados
```
[ROLL(pool=X, hunger=Y)]                  # Solicitar tirada
                                          # X = dados totales (Atributo + Habilidad)
                                          # Y = nivel de Hambre actual
```

### Contexto Narrativo (NUEVO)
```
[UPDATE_LOCATION(ubicación)]              # Cambiar ubicación
[UPDATE_SITUATION(situación)]             # Cambiar situación narrativa
```

---

## EJEMPLOS DE USO

### Ejemplo 1: Combate
```
Storyteller: "El atacante te golpea con su arma blanca..."

[UPDATE_LOCATION(Callejón del distrito de The Loop)]
[UPDATE_SITUATION(Bajo ataque. Un asaltante armado)]
[DAMAGE(type="superficial", amount=2)]
[SET_HUNGER(3)]
```

### Ejemplo 2: Tirada de Destreza
```
Storyteller: "Para esquivar los disparos necesitarás una tirada. 
Destreza 3 + Atletismo 2 = Pool 5"

[ROLL(pool=5, hunger=2)]

[Motor ejecuta la tirada automáticamente]

Storyteller continúa según resultado...

[SET_HUNGER(2)]  # La tensión baja un poco
```

### Ejemplo 3: Cambio de Escena
```
Storyteller: "Logras escapar de los cazadores y te refugias en 
un edificio abandonado en el barrio antiguo..."

[UPDATE_LOCATION(Edificio abandonado - Barrio antiguo de Chicago)]
[UPDATE_SITUATION(Seguro, por ahora. Pero debes encontrar refugio antes del amanecer)]
[SPEND_WILLPOWER(1)]  # Gastaste voluntad huyendo
```

### Ejemplo 4: Interacción con PNJ
```
Storyteller: "Anita te observa desde las sombras. Sus ojos reflejan 
la sed de poder. 'Creí que no llegarías aquí con vida', susurra."

[UPDATE_SITUATION(Reunido con Anita. Actitud cuidadosa pero potencialmente aliada)]
[SET_HUNGER(4)]  # Tu Hambre aumenta por la presencia de alguien tan poderoso
```

---

## CONTEXTO INYECTADO AUTOMÁTICAMENTE

Antes de cada turno, el sistema inyecta automáticamente:

```
[== ESTADO ACTUAL ==]
📍 Ubicación: [Tu ubicación actual]
🎭 Situación: [Situación narrativa]
🩸 Hambre: X/5 - [Interpretación narrativa]
💔 Salud: [Estado resumido]
💪 Voluntad: X/5
🕊️  Humanidad: X/10

[=== EVENTOS RECIENTES ===]
• [Último evento]
• [Penúltimo evento]
• [Antepenúltimo evento]
[=== FIN EVENTOS ===]
```

---

## NIVELES DE HAMBRE Y SUS EFECTOS NARRATIVOS

| Hambre | Descripción | Implicaciones Narrativas |
|--------|-------------|-------------------------|
| 0 | Saciado. La Bestia duerme | Compostura, reflexión, decisiones racionales |
| 1 | Hambriento pero controlado | Normal, ligeramente alerta a sangre |
| 2 | El instinto es perceptible | Comienzas a notar a mortales como "presa" |
| 3 | LA SED CLAMA. Ojos ven rojo | Irritabilidad, sed abrumadora, tentaciones |
| 4 | LA BESTIA ACECHA TRAS TUS OJOS | Apenas controlas, deseos violentos, peligro |
| 5 | FRENÉTICO. Control frágil | Riesgo extremo, Bestia casi en control total |

**El modelo adapta automáticamente la narrativa según tu Hambre actual.**

---

## TIPOS DE RESULTADOS DE TIRADA

### Pifia Bestial
- **Condición**: 0 éxitos + al menos un 1 en dados de hambre
- **Narrativa**: La Bestia toma el control momentáneamente
- **Ejemplo**: Intentas controlar tu ira pero fallas y atacas brutalmente

### Crítico Desordenado  
- **Condición**: 2+ dados con 10, incluyendo dados de hambre
- **Narrativa**: Logras tu objetivo pero SIN CONTROL, brutal y salvaje
- **Ejemplo**: Consigues el arma del enemigo pero lo desgarras brutalmente sin querer

### Éxito Crítico
- **Condición**: 2+ dados con 10, sin dados de hambre
- **Narrativa**: Victoria elegante, controlada, perfecta
- **Ejemplo**: Esquivas los ataques con precisión casi sobrenatural

### Éxito Corriente
- **Condición**: 1+ éxitos normales
- **Narrativa**: Logras tu objetivo con algunos matices
- **Ejemplo**: Consigues la información pero el contacto sospechar algo

### Fracaso
- **Condición**: 0 éxitos totales
- **Narrativa**: Las circunstancias cambian en tu contra, nuevas complicaciones
- **Ejemplo**: Buscas pistas pero en su lugar das con algo peligroso

---

## MEJORES PRÁCTICAS

✅ **SÍ**:
- Describe acciones específicas: "Intento colarme sin ser visto"
- Pregunta al Storyteller cuando no sepas pools de dados
- Usa tu Hambre como aliado narrativo
- Explora dilemas morales

❌ **NO**:
- Esperes que el Storyteller cuente solo lo importante
- Ignores la injusticia del Mundo de Tinieblas
- Pidas al Storyteller que te haga ganar automáticamente
- Olvides que las consecuencias son REALES

---

## CONSEJO FINAL

**El Storyteller está diseñado para:**
- Darte respuestas largas, cinematográficas y desarrolladas
- Mantener coherencia con tu estado actual
- Adaptar la narración a tu Hambre
- Crear atmósfera oscura y tensa
- Hacer que tus acciones IMPORTEN

**Tu rol es:**
- Ser específico y detallado en tus acciones
- Explorar el horror del Mundo de Tinieblas
- Abrazar las consecuencias de tus decisiones
- Divertirte en la oscuridad

---

**Ahora: Que comience tu maldición. 🩸**
