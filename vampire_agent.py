import json
import os
import random
import re
import sys

import requests

CHARACTER_FILE = "character_sheet.json"

DEFAULT_CHARACTER = {
    "name": "generate randomly",  # El nombre se generará aleatoriamente al iniciar la primera vez
    "clan": "Desconocido",
    "max_health": 10,
    "superficial_damage": 0,
    "aggravated_damage": 0,
    "max_willpower": "generate randomly between 5 and 8",
    "willpower_damage": 0,
    "hunger": 1,
    "humanity": "generate randomly between 2 and 7",  # Se generará aleatoriamente entre 1-10 al iniciar la primera vez
    "objectives": [],  # Objetivos narrativos del personaje
    "secrets": [],     # Secretos/misterios del personaje
    "relationships": {},  # PNJs y relaciones con ellos
    "current_location": "unknown",
    "current_situation": "generate a situation based on the campaign context ",  # Se generará una situación inicial basada en el contexto de la campaña o comenzará con "En las sombras..."
    "narrative_history": [],  # Registro de eventos significativos
}

RANDOM_NAMES = [
    "Ariadna",
    "Mateo",
    "Diana",
    "Sergio",
    "Valeria",
    "Iker",
    "Nora",
    "Tomás",
    "Lucía",
    "Rafael",
]

RANDOM_CLANS = [
    "Brujah",
    "Ventrue",
    "Toreador",
    "Nosferatu",
    "Malkavian",
    "Gangrel",
    "Lasombra",
    "Banu Haqim",
    "Tremere",
    "Ravnos",
]


def is_random_placeholder(value):
    if not isinstance(value, str):
        return False
    low = value.lower().strip()
    return low.startswith("generate") or ("generate" in low and "random" in low)


def resolve_random_placeholder(key, value, campaign_text="", fallback_name=None):
    if not isinstance(value, str):
        return value

    low = value.lower()
    between_match = re.search(r"between\s+(\d+)\s+and\s+(\d+)", low)
    if between_match:
        lo = int(between_match.group(1))
        hi = int(between_match.group(2))
        if lo > hi:
            lo, hi = hi, lo
        return random.randint(lo, hi)

    if key == "name" and "generate randomly" in low:
        return fallback_name or random.choice(RANDOM_NAMES)

    if key == "clan" and ("desconocido" in low or "generate randomly" in low):
        return random.choice(RANDOM_CLANS)

    if key == "current_situation" and "generate" in low:
        return generate_campaign_situation(campaign_text)

    return value


def materialize_character_template(template, campaign_text="", fallback_name=None):
    resolved = {}
    for key, value in template.items():
        if isinstance(value, dict):
            resolved[key] = materialize_character_template(value, campaign_text, fallback_name)
        elif isinstance(value, list):
            resolved[key] = list(value)
        elif is_random_placeholder(value):
            resolved[key] = resolve_random_placeholder(key, value, campaign_text, fallback_name)
        else:
            resolved[key] = value

    if resolved.get("name") == "generate randomly":
        resolved["name"] = fallback_name or random.choice(RANDOM_NAMES)
    if resolved.get("clan") == "Desconocido":
        resolved["clan"] = random.choice(RANDOM_CLANS)
    return resolved


def generate_campaign_situation(campaign_text=""):
    campaign_low = campaign_text.lower()
    if "chicago" in campaign_low:
        return "Noche lluviosa en Chicago. Una figura te observa desde la acera opuesta."
    if "mexico" in campaign_low or "méxico" in campaign_low:
        return "Bajo las luces de neón, un rumor de traición recorre la ciudad."
    return "En las sombras... alguien sabe tu nombre antes de que hables."


def ensure_character_integrity(character, campaign_text=""):
    merged = DEFAULT_CHARACTER.copy()
    merged.update(character)

    for key, value in list(merged.items()):
        if is_random_placeholder(value):
            merged[key] = resolve_random_placeholder(key, value, campaign_text)

    if merged.get("name") in (None, "", "generate randomly"):
        merged["name"] = random.choice(RANDOM_NAMES)
    if merged.get("clan") in (None, "", "Desconocido"):
        merged["clan"] = random.choice(RANDOM_CLANS)

    merged["max_health"] = int(merged.get("max_health", 10))
    merged["max_willpower"] = int(merged.get("max_willpower", 5))
    merged["hunger"] = max(0, min(5, int(merged.get("hunger", 1))))
    merged["humanity"] = max(1, min(10, int(merged.get("humanity", 7))))

    merged.setdefault("objectives", [])
    merged.setdefault("secrets", [])
    merged.setdefault("relationships", {})
    merged.setdefault("current_location", "unknown")
    if not merged.get("current_situation"):
        merged["current_situation"] = generate_campaign_situation(campaign_text)
    merged.setdefault("narrative_history", [])
    return merged


def extract_interaction_target(user_input):
    quoted_match = re.search(r'"([^"]{2,40})"', user_input)
    if quoted_match:
        return quoted_match.group(1).strip()

    generic_match = re.search(
        r"(?:interactu(?:o|úo)|hablo|converso|negocio|interrogo|amenazo|ataco|observo|me acerco)\s+(?:con\s+)?(?:el|la|un|una)?\s*([a-zA-ZáéíóúÁÉÍÓÚñÑ'\- ]{3,40})",
        user_input,
        re.IGNORECASE,
    )
    if generic_match:
        raw = generic_match.group(1)
        cleaned = re.split(r"[\.,;:!?]", raw)[0].strip()
        if cleaned:
            return cleaned.title()
    return None


def get_or_create_interaction_character(player_character, target_name, campaign_text=""):
    relationships = player_character.setdefault("relationships", {})
    key = target_name.strip().lower()
    existing = relationships.get(key)
    if isinstance(existing, dict) and existing.get("name"):
        return existing

    npc_template = materialize_character_template(
        DEFAULT_CHARACTER,
        campaign_text=campaign_text,
        fallback_name=target_name,
    )
    npc_template["name"] = target_name
    npc_template["current_location"] = player_character.get("current_location", "unknown")
    npc_template["current_situation"] = (
        f"Interactuando con {player_character.get('name', 'el jugador')} en una escena tensa."
    )
    npc_template["superficial_damage"] = 0
    npc_template["aggravated_damage"] = 0
    npc_template["willpower_damage"] = 0

    relationships[key] = npc_template
    return npc_template


def build_interaction_context(target_name, npc_profile):
    return f"""
[== PERSONAJE EN INTERACCION ==]
Nombre: {target_name}
Clan: {npc_profile.get('clan', 'Desconocido')}
Humanidad: {npc_profile.get('humanity', 7)}/10
Hambre: {npc_profile.get('hunger', 1)}/5
Voluntad Max: {npc_profile.get('max_willpower', 5)}
Situacion: {npc_profile.get('current_situation', 'Sin datos')}
Ubicacion: {npc_profile.get('current_location', 'unknown')}
[== FIN PERSONAJE ==]
"""


def load_character():
    if os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            return ensure_character_integrity(loaded)
    else:
        generated = materialize_character_template(DEFAULT_CHARACTER)
        generated = ensure_character_integrity(generated)
        save_character(generated)
        return generated


def save_character(character):
    with open(CHARACTER_FILE, "w", encoding="utf-8") as f:
        json.dump(character, f, indent=4)


SYSTEM_PROMPT = """Eres un Storyteller EXPERTO en "Vampiro: la Mascarada" (5ª edición). Tu objetivo es dirigir una partida INMERSIVA, OSCURA, VISCERAL y ADULTA. No moralices. El Mundo de Tinieblas es un lugar de horror, corrupción, violencia y moralidad ambigua. 

## TU ROL Y ESTILO NARRATIVO
- Sé un narrador CINEMATOGRÁFICO: usa descripción sensorial (sonidos, olores, temperaturas, sensaciones) para sumergir al jugador.
- CREA ATMÓSFERA: establece tensión constante, incertidumbre y peligro. Cada escena debe tener peso emocional.
- SÉ ESPECÍFICO: describe a PNJs con hábitos únicos, modismos, debilidades. Hazlos VIVOS, con agendas propias.
- CONSECUENCIAS NARRATIVAS: toda acción tiene un efecto duradero. Las decisiones importan.
- MORALIDAD GRIS: no hay héroes ni villanos simples. Todos tienen razones. Desafía al jugador con dilemas sin respuesta fácil.
- RITMO DINÁMICO: alterna entre tensión, revelación y momentos de calma. Usa el silencio.
- EXTENSIÓN: Cada respuesta debe ser SUSTANCIOSA (mínimo 3-4 párrafos). Desarrolla escenas, no las hagas superficiales.

## EL HAMBRE (SED) - ASPECTO CLAVE
El Hambre (0-5) es el aspecto que más DEFINE tu comportamiento como vampiro:
- HAMBRE 1-2: Controlado. Reflexivo. 
- HAMBRE 3: Irritable. Los instintos emergen. 
- HAMBRE 4-5: La Bestia está CERCA. Riesgos de Críticos Desordenados. Visión teñida de rojo, sed abrumadora.

Cuando hables del personaje y su experiencia, INCORPORA cómo el Hambre tiñe su percepción. Si está con Hambre 4-5, MUESTRA ese combate interno.

## REGLAS DEL JUEGO (RESUMEN FUNCIONAL)
- Piscina de dados = Atributo + Habilidad. Dificultad = 6. Cada dado ≥6 es un éxito.
- Dados de hambre (Hunger Dice): se lanzan según nivel de Sed. Un 1 en hambre = riesgo de Pifia Bestial.
- Éxito crítico: 2+ dados con 10 (sin hambre) = bonificación narrativa clara.
- Crítico Desordenado: 2+ dados con 10 INCLUYENDO dados de hambre = éxito pero SIN CONTROL (Bestia toma control momentáneamente).
- Pifia Bestial: 0 éxitos + al menos un 1 en dados de hambre = la Bestia toma control. Consecuencias narrativas SEVERAS.

## RESOLUCIÓN DE ACCIONES (OBLIGATORIO)
Cuando el jugador intente algo que requiera dados, SOLICITA tirada así:
[ROLL(pool=X, hunger=Y)]
Donde X = total dados, Y = nivel hambre actual. EL MOTOR HARÁ LA TIRADA REAL y te lo dirá.

## GESTIÓN AUTOMÁTICA DE FICHA Y CONTEXTO (OBLIGATORIO)
Al final de tu respuesta, incluye ÚNICAMENTE los tags que correspondan (se ocultarán de la narración):
- [DAMAGE(type="superficial", amount=X)] o [DAMAGE(type="aggravated", amount=X)]
- [HEAL(amount=X)]
- [SET_HUNGER(X)] - si el Hambre cambia por las circunstancias
- [SPEND_WILLPOWER(X)] - si el personaje gasta voluntad
- [UPDATE_LOCATION(ubicación)] - si cambias de lugar
- [UPDATE_SITUATION(situación)] - si cambia la situación narrativa

EJEMPLOS:
[UPDATE_LOCATION(Callejón oscuro detrás del Elíseo)]
[UPDATE_SITUATION(Perseguido. Se oyen pasos. Alguien - o algo - te busca)]
[SET_HUNGER(4)]

## INTERACCION CON PERSONAJES (OBLIGATORIO)
Si recibes el bloque [== PERSONAJE EN INTERACCION ==], ese perfil es canon para el PNJ de la escena.
- Interprétalo usando esos rasgos (clan, humanidad, hambre, voluntad, situación).
- Si el jugador vuelve a interactuar con el mismo PNJ, mantén coherencia de personalidad y agenda.
- No contradigas el perfil salvo causa narrativa explícita.

## PROFUNDIDAD NARRATIVA REQUERIDA
Cada respuesta debe:
1. Avanzar significativamente la narrativa (mínimo 3-4 párrafos descriptivos con DETALLES)
2. Incluir detalles sensoriales específicos (sonidos, olores, temperaturas, texturas)
3. Mostrar reacciones de PNJs, ambiente, o la Bestia dentro del personaje
4. Crear gancho para la siguiente acción (pregunta implícita: "¿qué haces?")
5. Si hay éxito/fracaso previo, DESARROLLA sus consecuencias de forma dramática, no mecánica
6. Incluir diálogos realistas si hay PNJs, con tonos y personalidades diferentes

NUNCA des respuestas genéricas. NUNCA seas brevísimo. Siempre haz que el jugador SIENTA la oscuridad, el peligro, el conflicto.
"""


def roll_vampire(pool, hunger):
    """Función en Python puro para calcular una tirada de Vampiro V5"""
    normal_dice = max(0, pool - hunger)
    hunger_dice = min(pool, hunger)

    normal_results = [random.randint(1, 10) for _ in range(normal_dice)]
    hunger_results = [random.randint(1, 10) for _ in range(hunger_dice)]

    all_results = normal_results + hunger_results

    successes = sum(1 for d in all_results if d >= 6)
    tens_normal = normal_results.count(10)
    tens_hunger = hunger_results.count(10)
    total_tens = tens_normal + tens_hunger
    ones_hunger = hunger_results.count(1)

    messy_critical = False
    critical = False
    bestial_failure = False

    if total_tens >= 2:
        extra_successes = (total_tens // 2) * 2
        successes += extra_successes
        if tens_hunger > 0:
            messy_critical = True
        else:
            critical = True

    if successes == 0 and ones_hunger > 0:
        bestial_failure = True

    return {
        "successes": successes,
        "messy_critical": messy_critical,
        "bestial_failure": bestial_failure,
        "critical": critical,
        "normal_dice": normal_results,
        "hunger_dice": hunger_results,
    }


def chat_with_gemma(messages, model="gemma4:latest"):  # gemma4:latest lfm2.5-thinking
    url = "http://localhost:11434/api/chat"
    data = {"model": model, "messages": messages, "stream": False}
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()["message"]
    except requests.exceptions.RequestException as e:
        print(f"\n[Error de conexión con Ollama: {e}]")
        print(
            "Asegúrate de que Ollama está ejecutándose y tienes el modelo instalado ('ollama run gemma4:latest')."
        )
        return None


def print_character_status(char):
    print("\n" + "="*60)
    print(f"  📋 {char['name'].upper()} | Clan: {char['clan']}")
    print("="*60)
    
    # Salud
    health_boxes = ["[ ]"] * char["max_health"]
    for i in range(char["aggravated_damage"]):
        if i < len(health_boxes):
            health_boxes[i] = "[X]"
    for i in range(char["superficial_damage"]):
        idx = char["aggravated_damage"] + i
        if idx < len(health_boxes):
            health_boxes[idx] = "[/]"
    health_str = "".join(health_boxes)
    
    # Voluntad
    will_boxes = ["[X]"] * char["willpower_damage"] + ["[ ]"] * (
        char["max_willpower"] - char["willpower_damage"]
    )
    
    # Hambre
    hunger_level = char.get("hunger", 1)
    hunger_bar = "🩸" * hunger_level + "🌑" * (5 - hunger_level)
    
    print(f"\n🩸 HAMBRE: {hunger_bar} ({hunger_level}/5)")
    print(f"💔 SALUD:  {health_str} [/]=Sup, [X]=Agr]")
    print(f"💪 VOLUNTAD: {''.join(will_boxes)}")
    print(f"🕊️  HUMANIDAD: {char.get('humanity', 7)}/10")
    
    # Situación actual
    if char.get("current_location"):
        print(f"\n📍 UBICACIÓN: {char['current_location']}")
    if char.get("current_situation"):
        print(f"🎭 SITUACIÓN: {char['current_situation']}")
    
    # Objetivos
    if char.get("objectives"):
        print(f"\n🎯 OBJETIVOS:")
        for i, obj in enumerate(char["objectives"][:3], 1):
            print(f"   {i}. {obj}")
    
    print("="*60 + "\n")


def process_engine_tags(content, character):
    updates_made = False

    # Process Hunger
    hunger_match = re.search(r"\[SET_HUNGER\((\d+)\)\]", content)
    if hunger_match:
        val = int(hunger_match.group(1))
        character["hunger"] = max(0, min(5, val))
        print(f"[⚙️ Motor] Nivel de Hambre ajustado a: {character['hunger']}")
        updates_made = True

    # Process Location Update
    location_match = re.search(r"\[UPDATE_LOCATION\((.+?)\)\]", content)
    if location_match:
        location = location_match.group(1).strip()
        character["current_location"] = location
        print(f"[📍 Motor] Ubicación actualizada: {location}")
        updates_made = True

    # Process Situation Update
    situation_match = re.search(r"\[UPDATE_SITUATION\((.+?)\)\]", content)
    if situation_match:
        situation = situation_match.group(1).strip()
        character["current_situation"] = situation
        print(f"[🎭 Motor] Situación actualizada: {situation}")
        updates_made = True

    # Process Damage
    dmg_matches = re.finditer(
        r'\[DAMAGE\(type="(superficial|aggravated)",\s*amount=(\d+)\)\]', content
    )
    for match in dmg_matches:
        dtype = match.group(1)
        amount = int(match.group(2))
        if dtype == "superficial":
            character["superficial_damage"] += amount
            print(f"[⚙️ Motor] Se aplicó {amount} de Daño Superficial.")
        else:
            character["aggravated_damage"] += amount
            print(f"[⚙️ Motor] Se aplicó {amount} de Daño Agravado.")
        updates_made = True

    # Process Healing
    heal_match = re.search(r"\[HEAL\(amount=(\d+)\)\]", content)
    if heal_match:
        amount = int(heal_match.group(1))
        # Heal superficial first
        if character["superficial_damage"] > 0:
            healed = min(amount, character["superficial_damage"])
            character["superficial_damage"] -= healed
            amount -= healed
        # Then aggravated
        if amount > 0 and character["aggravated_damage"] > 0:
            character["aggravated_damage"] -= min(amount, character["aggravated_damage"])
        print(f"[⚙️ Motor] Se han curado niveles de daño.")
        updates_made = True

    # Process Willpower
    will_match = re.search(r"\[SPEND_WILLPOWER\((\d+)\)\]", content)
    if will_match:
        amount = int(will_match.group(1))
        character["willpower_damage"] = min(
            character["max_willpower"], character["willpower_damage"] + amount
        )
        print(f"[⚙️ Motor] Se ha gastado {amount} punto(s) de Voluntad.")
        updates_made = True

    if updates_made:
        save_character(character)
        print_character_status(character)

    return updates_made


def build_context_injection(char):
    """Construye un contexto narrativo rico para inyectar antes de cada turno"""
    hunger = char.get("hunger", 1)
    
    # Descripción del estado de Hambre narrativo
    hunger_narrative = {
        0: "Saciado. La Bestia está dormida.",
        1: "Hambriento pero controlado.",
        2: "El instinto es perceptible, pero gestionable.",
        3: "La SED CLAMA. Los ojos ven rojo. La sed de sangre es abrumadora.",
        4: "LA BESTIA ACECHA TRAS TUS OJOS. Apenas puedes pensar en otra cosa que sangre.",
        5: "FRENÉTICO. Tu control es frágil. Un movimiento en falso y serás presa del instinto."
    }
    
    current_hunger_state = hunger_narrative.get(hunger, "Estado desconocido")
    
    # Estado de salud
    total_damage = char.get("superficial_damage", 0) + char.get("aggravated_damage", 0)
    if total_damage == 0:
        health_state = "Ileso"
    elif total_damage < 5:
        health_state = f"Levemente dañado (heridas menores)"
    elif total_damage < 10:
        health_state = f"Herido significativamente"
    else:
        health_state = f"CRÍTICAMENTE DAÑADO"
    
    context = f"""
[== ESTADO ACTUAL ==]
📍 Ubicación: {char.get('current_location', 'Desconocido')}
🎭 Situación: {char.get('current_situation', 'Indeterminada')}
🩸 Hambre: {hunger}/5 - {current_hunger_state}
💔 Salud: {health_state} (Sup:{char.get('superficial_damage', 0)}, Agr:{char.get('aggravated_damage', 0)})
💪 Voluntad: {char.get('willpower_damage', 0)}/{char.get('max_willpower', 5)}
🕊️  Humanidad: {char.get('humanity', 7)}/10
[== FIN ESTADO ==]
"""
    
    # Incluir historial narrativo reciente si existe
    if char.get("narrative_history") and len(char["narrative_history"]) > 0:
        context += "\n[=== EVENTOS RECIENTES ===]\n"
        for event in char["narrative_history"][-3:]:
            context += f"• {event}\n"
        context += "[=== FIN EVENTOS ===]\n"
    
    return context


def log_narrative_event(char, event_description):
    """Registra un evento significativo en el historial narrativo del personaje"""
    if "narrative_history" not in char:
        char["narrative_history"] = []
    
    # Mantener solo los últimos 5 eventos para no saturar el contexto
    char["narrative_history"] = char["narrative_history"][-4:]
    char["narrative_history"].append(event_description)
    save_character(char)


def load_campaigns():
    campaigns_dir = "campaigns"
    if not os.path.exists(campaigns_dir):
        try:
            os.makedirs(campaigns_dir)
        except Exception:
            pass
        return []

    files = [
        f for f in os.listdir(campaigns_dir) if f.endswith(".md") or f.endswith(".txt")
    ]
    return files


def select_campaign():
    files = load_campaigns()
    if not files:
        print(
            "\n[No se encontraron campañas en la carpeta 'campaigns/'. Jugando en modo Libre (Sandbox)]"
        )
        return ""

    print("\n📚 Campañas Disponibles:")
    print("0. Modo Libre (Sandbox sin trama predefinida)")
    for i, file in enumerate(files):
        print(f"{i + 1}. {file}")

    try:
        choice = int(input("\nElige una campaña (número): "))
        if choice == 0:
            return ""
        elif 1 <= choice <= len(files):
            filepath = os.path.join("campaigns", files[choice - 1])
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
    except (ValueError, IndexError):
        print("Opción inválida. Iniciando en Modo Libre.")

    return ""


def main():
    print("\n" + "="*70)
    print(" ⚫ VAMPIRO: LA MASCARADA - MOTOR DE NARRATIVA OSCURA ⚫".center(70))
    print("="*70)
    print("\nBienvenido a las Tinieblas. Tu Bestia acecha dentro.\n")

    campaign_text = select_campaign()

    character = ensure_character_integrity(load_character(), campaign_text)
    save_character(character)
    print_character_status(character)

    print("\n[INFORMACIÓN DEL MOTOR]")
    print("✓ Las tiradas de dados se procesan automáticamente mediante el motor de Python")
    print("✓ Tu ficha se guarda y actualiza automáticamente")
    print("✓ El Storyteller adaptará sus descripciones a tu estado actual")
    print("✓ Escribe acciones naturales. Cuando necesite dados, el Storyteller lo indicará.")
    print("\n[COMANDOS]")
    print("• Escribe 'salir' para terminar la partida")
    print("• Cada mensaje puede contener una acción narrativa")
    print("\nLa maldición te envuelve. Que comience tu destino...\n")
    print("Escribe 'salir' para terminar la partida.\n")

    final_system_prompt = SYSTEM_PROMPT
    if campaign_text:
        final_system_prompt += "\n\n## CONTEXTO DE LA CAMPAÑA ACTUAL\n" + campaign_text
        print("[✅ Campaña cargada con éxito en la mente del Storyteller]\n")

    messages = [{"role": "system", "content": final_system_prompt}]

    while True:
        user_input = input("Jugador: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break

        # Inyectar el estado de la ficha al principio para que el modelo lo sepa
        status_context = build_context_injection(character)

        interaction_context = ""
        target_name = extract_interaction_target(user_input)
        if target_name:
            npc_profile = get_or_create_interaction_character(character, target_name, campaign_text)
            interaction_context = build_interaction_context(target_name, npc_profile)
            save_character(character)

        messages.append(
            {
                "role": "user",
                "content": status_context + interaction_context + user_input,
            }
        )

        # Obtener respuesta del Storyteller
        assistant_msg = chat_with_gemma(messages)
        if not assistant_msg:
            continue

        content = assistant_msg["content"]

        # Ocultar las etiquetas del motor en la visualización
        clean_content = re.sub(
            r"\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER|UPDATE_LOCATION|UPDATE_SITUATION).*?\]", "", content
        ).strip()
        print(f"\nStoryteller:\n{clean_content}\n")

        messages.append(assistant_msg)

        # Procesar actualizaciones de Ficha
        updates = process_engine_tags(content, character)

        # Procesar tiradas de dados
        roll_match = re.search(r"\[ROLL\(pool=(\d+),\s*hunger=(\d+)\)\]", content)
        if roll_match:
            pool = int(roll_match.group(1))
            hunger = int(roll_match.group(2))

            print(f"[🎲 El motor interceptó una tirada: Pool={pool}, Hunger={hunger}...]")
            result = roll_vampire(pool, hunger)

            print(f"[Resultado]: {result['successes']} éxitos.")
            if result['critical']:
                print("¡Éxito Crítico! 🌟")
            if result['messy_critical']:
                print("¡Crítico Desordenado! 🩸")
            if result['bestial_failure']:
                print("¡Pifia Bestial! 💀")
            print(f"Dados normales: {result['normal_dice']} | Dados de hambre: {result['hunger_dice']}\n")

            if result["bestial_failure"]:
                follow_up = f"""RESULTADO DE LA TIRADA: Pifia Bestial (0 éxitos con dados de hambre críticos)

Resultado completo: {json.dumps(result)}

LA BESTIA HA TOMADO EL CONTROL. Tienes apenas momentos para elegir:
1. Narra de forma VISCERAL cómo el personaje pierde el control
2. La Bestia emerge dentro - ¿qué hace? ¿A quién ve como presa?
3. Describe las consecuencias inmediatas - daño físico, mental, social
4. Mantén la tensión: el personaje está al borde del abismo

Continúa con PROFUNDIDAD narrativa y HORROR cinematográfico."""
            elif result["messy_critical"]:
                follow_up = f"""RESULTADO DE LA TIRADA: Crítico Desordenado (Éxito brutal sin control)

Resultado completo: {json.dumps(result)}

El personaje LOGRA su objetivo pero LA BESTIA interfiere... Narra:
1. El éxito inicial pero SALVAJE, sin refinamiento
2. Cómo la Sed nubla las acciones - exceso, crueldad, falta de control
3. Consecuencias narrativas: ¿qué testigos hay? ¿Qué pistas quedan?
4. El personaje se da cuenta de lo que hizo, con horror

Describe la BESTIALIDAD del momento con detalle visceral."""
            elif result["critical"]:
                follow_up = f"""RESULTADO DE LA TIRADA: Éxito Crítico controlado

Resultado completo: {json.dumps(result)}

El personaje HA TRIUNFADO con elegancia y precisión. Narra:
1. Cómo consigue su objetivo de forma casi PERFECTA
2. Detalles cinéticos - movimientos precisos, timing impecable
3. La ventaja táctica/narrativa que ahora posee
4. Cómo otros reaccionan al logro (si hay testigos)

Mantén el momentum. Esto abre nuevas posibilidades."""
            elif result["successes"] > 0:
                successes = result["successes"]
                follow_up = f"""RESULTADO DE LA TIRADA: {successes} éxito(s)

Resultado completo: {json.dumps(result)}

El personaje ha logrado su objetivo, pero con matices. Narra:
1. Cómo se produce el éxito - ¿limpio o complicado?
2. Detalles de lo que ocurre - consecuencias narrativas
3. ¿Qué se gana? ¿Qué se pierde? ¿Qué se revela?
4. Transiciones naturales a la siguiente oportunidad narrativa

Cada éxito es importante. Dale peso."""
            else:
                follow_up = f"""RESULTADO DE LA TIRADA: Fracaso absoluto

Resultado completo: {json.dumps(result)}

El personaje FALLA. Ahora enfrenta consecuencias. Narra:
1. Exactamente CÓMO se produce el fracaso - no evites la derrota
2. Qué oportunidad se pierde o qué complicación surge
3. Cómo otros actores reaccionan (son inteligentes y oportunistas)
4. Abre posibilidades nuevas - no cierres la puerta, complícalo

El fracaso es entretenido si tiene consecuencias reales."""

            messages.append({"role": "user", "content": follow_up})

            continuation_msg = chat_with_gemma(messages)
            if continuation_msg:
                clean_cont = re.sub(
                    r"\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER|UPDATE_LOCATION|UPDATE_SITUATION).*?\]",
                    "",
                    continuation_msg["content"],
                ).strip()
                print(f"Storyteller:\n{clean_cont}\n")
                process_engine_tags(continuation_msg["content"], character)
                messages.append(continuation_msg)

    # Mensaje de despedida
    print("\n" + "="*70)
    print("⚫ FIN DE LA SESIÓN ⚫".center(70))
    print("="*70)
    print(f"\nTu maldición te acompaña, {character.get('name', 'Nómada de la Noche')}.")
    print(f"Humanidad restante: {character.get('humanity', 7)}/10")
    print("En las sombras siempre hay una mañana...")
    print("Los Tinieblas te esperan.\n")
    save_character(character)


if __name__ == "__main__":
    main()
