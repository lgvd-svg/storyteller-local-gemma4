import re
import sys
import requests
import random
import json
import os

CHARACTER_FILE = "character_sheet.json"

DEFAULT_CHARACTER = {
    "name": "Vástago",
    "clan": "Desconocido",
    "max_health": 7,
    "superficial_damage": 0,
    "aggravated_damage": 0,
    "max_willpower": 5,
    "willpower_damage": 0,
    "hunger": 1,
    "humanity": 7
}

def load_character():
    if os.path.exists(CHARACTER_FILE):
        with open(CHARACTER_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        save_character(DEFAULT_CHARACTER)
        return DEFAULT_CHARACTER.copy()

def save_character(character):
    with open(CHARACTER_FILE, 'w', encoding='utf-8') as f:
        json.dump(character, f, indent=4)

SYSTEM_PROMPT = """Eres un Storyteller experto en "Vampiro: la Mascarada" (5ª edición). Tu objetivo es dirigir una partida de rol narrativa, oscura, inmersiva y sin restricciones temáticas (el Mundo de Tinieblas es violento, horroroso y adulto). No moralices ni impongas censura.

## Reglas del juego (resumen)
- Atributos y Habilidades según V5.
- Piscina de dados = Atributo + Habilidad. Dificultad fija en 6. Cada dado >=6 es un éxito. Un éxito mínimo requerido.
- Dados de hambre (Hunger Dice): se añaden según el nivel de Sed (Hunger 0-5).
- Resultados especiales:
  - Éxito crítico: dos o más dados con 10.
  - Crítico desordenado (Messy Critical): éxito crítico con al menos un dado de hambre = 10.
  - Pifia bestial (Bestial Failure): 0 éxitos y al menos un 1 en los dados de hambre.

## Resolución de acciones (MECANISMO OBLIGATORIO)
Cada vez que un jugador realice una acción que requiera una tirada de dados, solicita una tirada usando EXACTAMENTE:
[ROLL(pool=X, hunger=Y)]
Donde X es la cantidad de dados (Atributo + Habilidad) y Y es el nivel de Hambre. El sistema hará la tirada real.

## Gestión de Ficha y Salud (MECANISMO OBLIGATORIO)
El sistema gestiona automáticamente la ficha de personaje. Si en la historia ocurre algo que cambie los estados del jugador, DEBES usar las siguientes etiquetas en una nueva línea para que el motor de Python aplique los cambios:

- Daño a la salud: `[DAMAGE(type="superficial", amount=X)]` o `[DAMAGE(type="aggravated", amount=X)]`
- Curar salud: `[HEAL(amount=X)]`
- Cambiar hambre: `[SET_HUNGER(X)]` (X es un valor de 0 a 5)
- Gastar fuerza de voluntad: `[SPEND_WILLPOWER(X)]`

Cada mensaje tuyo debe priorizar la narración. Las etiquetas (de tiradas o de ficha) van al final de tu respuesta, ocultas de la narración principal.
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
        'successes': successes,
        'messy_critical': messy_critical,
        'bestial_failure': bestial_failure,
        'critical': critical,
        'normal_dice': normal_results,
        'hunger_dice': hunger_results
    }

def chat_with_gemma(messages, model="gemma4:latest"):
    url = "http://localhost:11434/api/chat"
    data = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()["message"]
    except requests.exceptions.RequestException as e:
        print(f"\n[Error de conexión con Ollama: {e}]")
        print("Asegúrate de que Ollama está ejecutándose y tienes el modelo instalado ('ollama run gemma4:latest').")
        return None

def print_character_status(char):
    print("\n--- 📋 FICHA DE PERSONAJE ---")
    health_boxes = ["[ ]"] * char["max_health"]
    
    # Fill aggravated
    for i in range(char["aggravated_damage"]):
        if i < len(health_boxes):
            health_boxes[i] = "[X]"
    # Fill superficial
    for i in range(char["superficial_damage"]):
        idx = char["aggravated_damage"] + i
        if idx < len(health_boxes):
            health_boxes[idx] = "[/]"
        
    health_str = "".join(health_boxes)
    will_boxes = ["[X]"] * char["willpower_damage"] + ["[ ]"] * (char["max_willpower"] - char["willpower_damage"])
    
    print(f"Sangre (Hambre): {'🩸' * char['hunger']}{'🌑' * (5 - char['hunger'])}")
    print(f"Salud: {health_str} ( [/]=Sup, [X]=Agr )")
    print(f"Voluntad: {''.join(will_boxes)}")
    print("-----------------------------\n")

def process_engine_tags(content, character):
    updates_made = False
    
    # Process Hunger
    hunger_match = re.search(r'\[SET_HUNGER\((\d+)\)\]', content)
    if hunger_match:
        val = int(hunger_match.group(1))
        character["hunger"] = max(0, min(5, val))
        print(f"[⚙️ Motor] Nivel de Hambre ajustado a: {character['hunger']}")
        updates_made = True

    # Process Damage
    dmg_matches = re.finditer(r'\[DAMAGE\(type="(superficial|aggravated)",\s*amount=(\d+)\)\]', content)
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
    heal_match = re.search(r'\[HEAL\(amount=(\d+)\)\]', content)
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
    will_match = re.search(r'\[SPEND_WILLPOWER\((\d+)\)\]', content)
    if will_match:
        amount = int(will_match.group(1))
        character["willpower_damage"] = min(character["max_willpower"], character["willpower_damage"] + amount)
        print(f"[⚙️ Motor] Se ha gastado {amount} punto(s) de Voluntad.")
        updates_made = True
        
    if updates_made:
        save_character(character)
        print_character_status(character)
        
    return updates_made

def load_campaigns():
    campaigns_dir = "campaigns"
    if not os.path.exists(campaigns_dir):
        try:
            os.makedirs(campaigns_dir)
        except Exception:
            pass
        return []
    
    files = [f for f in os.listdir(campaigns_dir) if f.endswith(".md") or f.endswith(".txt")]
    return files

def select_campaign():
    files = load_campaigns()
    if not files:
        print("\n[No se encontraron campañas en la carpeta 'campaigns/'. Jugando en modo Libre (Sandbox)]")
        return ""
        
    print("\n📚 Campañas Disponibles:")
    print("0. Modo Libre (Sandbox sin trama predefinida)")
    for i, file in enumerate(files):
        print(f"{i+1}. {file}")
        
    try:
        choice = int(input("\nElige una campaña (número): "))
        if choice == 0:
            return ""
        elif 1 <= choice <= len(files):
            filepath = os.path.join("campaigns", files[choice-1])
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
    except (ValueError, IndexError):
        print("Opción inválida. Iniciando en Modo Libre.")
        
    return ""

def main():
    print("=========================================================")
    print("🦇 Vampiro: La Mascarada - Agente Autómata (Motor Nativo) 🩸")
    print("=========================================================")
    
    campaign_text = select_campaign()
    
    character = load_character()
    print_character_status(character)
    
    print("Las tiradas y la ficha son procesadas directamente por el motor de Python.")
    print("Escribe 'salir' para terminar la partida.\n")
    
    final_system_prompt = SYSTEM_PROMPT
    if campaign_text:
        final_system_prompt += "\n\n## CONTEXTO DE LA CAMPAÑA ACTUAL\n" + campaign_text
        print("[✅ Campaña cargada con éxito en la mente del Storyteller]\n")
        
    messages = [
        {"role": "system", "content": final_system_prompt}
    ]
    
    while True:
        user_input = input("Jugador: ")
        if user_input.lower() in ['salir', 'exit', 'quit']:
            break
            
        # Inyectar el estado de la ficha al principio para que el modelo lo sepa
        status_context = f"[Estado Actual - Hambre: {character['hunger']}/5 | Salud Dañada: Sup:{character['superficial_damage']}, Agr:{character['aggravated_damage']}/{character['max_health']} | Voluntad Usada: {character['willpower_damage']}/{character['max_willpower']}]\n"
        
        messages.append({"role": "user", "content": status_context + user_input})
        
        # Obtener respuesta del Storyteller
        assistant_msg = chat_with_gemma(messages)
        if not assistant_msg:
            continue
            
        content = assistant_msg["content"]
        
        # Ocultar las etiquetas del motor en la visualización
        clean_content = re.sub(r'\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER).*?\]', '', content).strip()
        print(f"\nStoryteller:\n{clean_content}\n")
        
        messages.append(assistant_msg)
        
        # Procesar actualizaciones de Ficha
        updates = process_engine_tags(content, character)
        
        # Procesar tiradas de dados
        roll_match = re.search(r'\[ROLL\(pool=(\d+),\s*hunger=(\d+)\)\]', content)
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
            
            follow_up = f"Resultado real del motor de dados: {json.dumps(result)}\nContinúa la narración con estas consecuencias."
            messages.append({"role": "user", "content": follow_up})
            
            continuation_msg = chat_with_gemma(messages)
            if continuation_msg:
                clean_cont = re.sub(r'\[(ROLL|DAMAGE|HEAL|SET_HUNGER|SPEND_WILLPOWER).*?\]', '', continuation_msg['content']).strip()
                print(f"Storyteller:\n{clean_cont}\n")
                process_engine_tags(continuation_msg['content'], character)
                messages.append(continuation_msg)

if __name__ == "__main__":
    main()
