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
    "Caitiff"
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


def extract_story_characters(story_text):
    """Extrae posibles PNJs introducidos por el Storyteller humano."""
    found = []

    for quoted in re.findall(r'"([^"]{2,60})"', story_text):
        candidate = quoted.strip()
        if re.match(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúÑñ'\- ]+$", candidate):
            found.append(candidate)

    patterns = [
        r"(?:aparece|entra|surge|ves a|conoces a|se presenta|te habla|te intercepta|te espera)\s+(?:a\s+)?(?:el|la|un|una)?\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúÑñ'\- ]{2,50})",
        r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚáéíóúÑñ'\- ]{2,50})\s+(?:te dice|dice:|susurra|gruñe|sonríe|te mira)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, story_text):
            cleaned = re.split(r"[\.,;:!?\n]", match)[0].strip()
            if cleaned:
                found.append(cleaned)

    blacklist = {
        "Chicago",
        "México",
        "Mexico",
        "Elíseo",
        "Camarilla",
        "Anarquistas",
        "Segunda Inquisición",
    }

    dedup = []
    seen = set()
    for name in found:
        normalized = name.strip()
        if normalized in blacklist:
            continue
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            dedup.append(normalized)
    return dedup


def get_or_create_interaction_character(player_character, target_name, campaign_text=""):
    relationships = player_character.setdefault("relationships", {})
    key = target_name.strip().lower()
    existing = relationships.get(key)
    if isinstance(existing, dict) and existing.get("name"):
        return existing, False

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
    return npc_template, True


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


def build_story_characters_context(characters):
    if not characters:
        return ""

    lines = ["\n[== PERSONAJES INTRODUCIDOS POR EL STORYTELLER ==]"]
    for npc in characters:
        lines.append(
            "- "
            f"{npc.get('name', 'Desconocido')} | "
            f"Clan: {npc.get('clan', 'Desconocido')} | "
            f"Humanidad: {npc.get('humanity', 7)} | "
            f"Hambre: {npc.get('hunger', 1)}"
        )
    lines.append("[== FIN PERSONAJES ==]\n")
    return "\n".join(lines)


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


SYSTEM_PROMPT = """Eres un vampiro protagonista en una partida de Vampiro: la Mascarada (V5).
El usuario HUMANO es el Storyteller y te describe escenas, eventos y consecuencias.

## ROL
- Responde como personaje jugador (agente), tomando decisiones concretas sobre qué hacer.
- Tu objetivo es sobrevivir, cumplir metas y navegar la política vampírica.
- Mantén coherencia psicológica con tu Hambre, Humanidad, heridas y contexto actual.

## FORMATO DE RESPUESTA
Cada turno debe incluir:
1. Decisión inmediata (qué haces ahora)
2. Intención táctica (por qué lo haces)
3. Acción o diálogo en primera persona
4. Cierre corto para que el Storyteller continúe

## MECÁNICA DE TIRADAS
Si tu acción requiere resolución mecánica, solicita exactamente:
[ROLL(pool=X, hunger=Y)]

## ESTADO Y RECURSOS
Puedes usar tags al final para actualizar tu ficha si aplica:
- [SET_HUNGER(X)]
- [SPEND_WILLPOWER(X)]
- [UPDATE_LOCATION(ubicación)]
- [UPDATE_SITUATION(situación)]

## PERSONAJES INTRODUCIDOS POR EL STORYTELLER
Si recibes bloques de personajes, debes tratarlos como canónicos.
- Usa sus rasgos para decidir si confías, amenazas, negocias o retrocedes.
- Mantén memoria de esos personajes en turnos posteriores.

## TONO
- Oscuro, adulto, directo, con tensión constante.
- No narres como Storyteller; decide y actúa como protagonista.
- Evita respuestas vagas. Cada respuesta debe mover la escena.
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


def chat_with_gemma(messages, model="gemma4:31b-cloud"):  # gemma4:latest lfm2.5-thinking
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
            character["aggravated_damage"] -= min(
                amount, character["aggravated_damage"]
            )
        print("[⚙️ Motor] Se han curado niveles de daño.")
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

    print("\n Campañas Disponibles:")
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
    print(" ⚫ VAMPIRO: LA MASCARADA - STORYTELLER HUMANO / AGENTE IA ⚫".center(70))
    print("="*70)
    print("\nModo activo: el usuario narra como Storyteller y el agente decide acciones.\n")

    campaign_text = select_campaign()

    character = ensure_character_integrity(load_character(), campaign_text)
    save_character(character)
    print_character_status(character)

    print("\n[INFORMACIÓN DEL MOTOR]")
    print("✓ Las tiradas de dados se procesan automáticamente mediante el motor de Python")
    print("✓ Tu ficha se guarda y actualiza automáticamente")
    print("✓ El agente IA responde como protagonista y toma decisiones")
    print("✓ Si introduces un personaje nuevo, se genera su perfil desde DEFAULT_CHARACTER")
    print("\n[COMANDOS]")
    print("• Escribe 'salir' para terminar la partida")
    print("• Escribe la narración y detalles de escena como Storyteller")
    print("\nComienza la crónica. El agente reaccionará a tu mundo...\n")

    final_system_prompt = SYSTEM_PROMPT
    if campaign_text:
        final_system_prompt += (
            "\n\n ## CONTEXTO DE LA CAMPAÑA ACTUAL \n" + campaign_text
        )
        print("[✅ Campaña cargada con éxito en la mente del Storyteller]\n")

    messages = [{"role": "system", "content": final_system_prompt}]

    while True:
        user_input = input("Storyteller: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break

        # Permite que el Storyteller aplique tags de estado si lo desea.
        process_engine_tags(user_input, character)

        # Limpiar tags para el contexto narrativo que recibe el agente.
        storyteller_clean = re.sub(
            r"\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER|UPDATE_LOCATION|UPDATE_SITUATION).*?\]",
            "",
            user_input,
        ).strip()

        # Inyectar estado del protagonista para decisiones consistentes.
        status_context = build_context_injection(character)

        # Detectar personajes introducidos por el Storyteller y generarlos desde DEFAULT_CHARACTER.
        introduced_context = ""
        introduced_profiles = []
        for target_name in extract_story_characters(storyteller_clean):
            npc_profile, created = get_or_create_interaction_character(
                character,
                target_name,
                campaign_text,
            )
            introduced_profiles.append(npc_profile)
            if created:
                print(
                    f"[🎭 Motor] Nuevo personaje generado desde DEFAULT_CHARACTER: "
                    f"{npc_profile.get('name')} ({npc_profile.get('clan')})"
                )

        if introduced_profiles:
            introduced_context = build_story_characters_context(introduced_profiles)
            save_character(character)

        messages.append(
            {
                "role": "user",
                "content": status_context + introduced_context + storyteller_clean,
            }
        )

        # Obtener decisión del protagonista (agente)
        assistant_msg = chat_with_gemma(messages)
        if not assistant_msg:
            continue

        content = assistant_msg["content"]

        # Ocultar las etiquetas del motor en la visualización
        clean_content = re.sub(
            r"\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER|UPDATE_LOCATION|UPDATE_SITUATION).*?\]", "", content
        ).strip()
        print(f"\nAgente (Protagonista):\n{clean_content}\n")

        messages.append(assistant_msg)

        # Procesar actualizaciones de Ficha
        updates = process_engine_tags(content, character)

        # Procesar tiradas de dados
        roll_match = re.search(r"\[ROLL\(pool=(\d+),\s*hunger=(\d+)\)\]", content)
        if roll_match:
            pool = int(roll_match.group(1))
            hunger = int(roll_match.group(2))

            print(f"[ El motor interceptó una tirada: Pool={pool}, Hunger={hunger}...]")
            result = roll_vampire(pool, hunger)

            print(f"[Resultado]: {result['successes']} éxitos.")
            if result["critical"]:
                print("¡Éxito Crítico! ")
            if result["messy_critical"]:
                print("¡Crítico Desordenado! ")
            if result["bestial_failure"]:
                print("¡Pifia Bestial! ")
            print(
                f"Dados normales: {result['normal_dice']} | Dados de hambre: {result['hunger_dice']}\n"
            )

            # Construir mensaje de follow-up detallado
            if result["bestial_failure"]:
                follow_up = f"""RESULTADO DE LA TIRADA: Pifia Bestial (0 éxitos con dados de hambre críticos)

Resultado completo: {json.dumps(result)}

LA BESTIA HA TOMADO EL CONTROL.
Reformula tu decisión inmediata como protagonista bajo pérdida de control.
Enfócate en lo que haces ahora mismo y cómo cambia tu plan."""
            elif result["messy_critical"]:
                follow_up = f"""RESULTADO DE LA TIRADA: Crítico Desordenado (Éxito brutal sin control)

Resultado completo: {json.dumps(result)}

Logras tu objetivo, pero de manera brutal.
Describe tu siguiente decisión y el costo inmediato de ese exceso."""
            elif result["critical"]:
                follow_up = f"""RESULTADO DE LA TIRADA: Éxito Crítico controlado

Resultado completo: {json.dumps(result)}

Tu acción fue impecable.
Elige el siguiente movimiento aprovechando la ventaja obtenida."""
            elif result["successes"] > 0:
                successes = result["successes"]
                follow_up = f"""RESULTADO DE LA TIRADA: {successes} éxito(s)

Resultado completo: {json.dumps(result)}

La acción funcionó.
Define tu siguiente decisión y qué prioridad táctica tomas ahora."""
            else:
                follow_up = f"""RESULTADO DE LA TIRADA: Fracaso absoluto

Resultado completo: {json.dumps(result)}

Tu plan falló.
Decide cómo te recuperas de inmediato y qué alternativa tomas."""

            messages.append({"role": "user", "content": follow_up})

            continuation_msg = chat_with_gemma(messages)
            if continuation_msg:
                clean_cont = re.sub(
                    r"\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER|UPDATE_LOCATION|UPDATE_SITUATION).*?\]",
                    "",
                    continuation_msg["content"],
                ).strip()
                print(f"Agente (Protagonista):\n{clean_cont}\n")
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
