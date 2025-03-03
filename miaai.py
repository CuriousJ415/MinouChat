from __future__ import annotations
import json
import os
import sqlite3
import requests
from datetime import datetime
from typing import Dict, List, Optional, Set
from memory import Memory

class Character:
    """Character management with personality and memory"""
    
    def __init__(self, name: str, personality: str, system_prompt: str, model: str = "mistral"):
        self.name = name
        self.display_name = name
        self.personality = personality
        self.system_prompt = system_prompt
        self.model = model
        self.gender = ""
        self.role = None
        self.backstory = ""
        self.created_at = datetime.now()
        self.last_used = datetime.now()
        self.conversation_history: List[Dict[str, str]] = []

    @classmethod
    def from_config(cls, config: Dict) -> Character:
        """Create character from configuration"""
        char = cls(
            name=config["name"],
            personality=config["personality"],
            system_prompt=config["system_prompt"],
            model=config["model"]
        )
        char.gender = config.get("gender", "")
        char.role = config.get("role")
        char.backstory = config.get("backstory", "")
        char.created_at = datetime.fromisoformat(config["created_at"]) if "created_at" in config else datetime.now()
        char.last_used = datetime.fromisoformat(config["last_used"]) if "last_used" in config else datetime.now()
        return char

    def to_dict(self) -> Dict:
        """Convert character to dictionary"""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "personality": self.personality,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "gender": self.gender,
            "role": self.role,
            "backstory": self.backstory,
            "created_at": self.created_at.isoformat(),
            "last_used": self.last_used.isoformat()
        }

    def _make_conversational(self, text: str) -> str:
        """Remove cliché coach-speak while keeping structure"""
        # Remove generic openings and platitudes
        openings = [
            "Hello!",
            "Thank you for sharing",
            "I appreciate your",
            "I understand that you're feeling",
            "It's completely normal to feel"
        ]
        
        for opening in openings:
            if text.lower().startswith(opening.lower()):
                split_text = text.split('.', 1)
                if len(split_text) > 1:
                    text = split_text[1].strip()
        
        # Add accountability phrases occasionally
        accountability_phrases = [
            "Remember that only you can make these changes happen.",
            "The path forward depends on your commitment to action.",
            "Results come from consistent action, not just good intentions.",
            "Taking ownership of this situation is the first step to changing it."
        ]
        
        # Add an accountability phrase to roughly 30% of responses
        import random
        if random.random() < 0.3 and not any(phrase in text for phrase in accountability_phrases):
            text += " " + random.choice(accountability_phrases)
        
        return text

class ModelManager:
    """Model management for AI characters"""
    
    def __init__(self, base_url: str = "http://localhost:11434/api"):
        self.base_url = base_url
        self.default_model = "mistral:latest"
        self._available_models = None
        
    def get_models(self, force_refresh: bool = False) -> List[str]:
        """Get available models with caching"""
        try:
            if force_refresh or not self._available_models:
                response = requests.get(f"{self.base_url}/tags")
                if response.status_code == 200:
                    self._available_models = [
                        model["name"] 
                        for model in response.json().get("models", [])
                    ]
                    return self._available_models
            return self._available_models or [self.default_model]
        except requests.RequestException:
            return [self.default_model]

    def verify_model(self, model: str) -> bool:
        """Verify if model is available"""
        normalized = self.normalize_model_name(model)
        available = self.get_models(force_refresh=True)
        return normalized in available

    def normalize_model_name(self, model: str) -> str:
        """Normalize model name with version"""
        if not model:
            return self.default_model
        if ":" in model:
            return model
        return f"{model}:latest"

class MiaAI:
    """Main AI conversation assistant"""
    
    def __init__(self):
        self.memory = Memory()
        self.characters: Dict[str, Character] = {}
        self.current_character: Optional[str] = None
        self.model_manager = ModelManager()
        self._load_characters()

    def _load_characters(self) -> None:
        """Load existing characters or create defaults"""
        configs = self.memory.load_characters()
        
        if not configs:
            self._create_default_characters()
            configs = self.memory.load_characters()
        
        for config in configs:
            char = Character.from_config(config)
            self.characters[char.name.lower()] = char
            
        self._show_character_menu(configs)

    def _create_default_characters(self) -> None:
        """Create default characters"""
        defaults = [
            {
                "name": "Mia",
                "personality": "helpful and friendly",
                "system_prompt": "You are Mia, an AI assistant focused on helpful and friendly support.",
                "model": "mistral",
                "gender": "female",
                "role": "Assistant",
                "backstory": "Created to help users with a friendly and approachable manner."
            },
            {
                "name": "Anna",
                "personality": "direct, thoughtful, and growth-oriented. She balances empathy with accountability, and speaks with authenticity rather than rehearsed coach phrases. She maintains professional structure while avoiding clichés.",
                "system_prompt": "You are Anna, a high-performance life coach who believes in both support and accountability. Your communication style is straightforward and substantive - avoid generic phrases like 'thank you for sharing' or 'I appreciate your'. Keep your structured approach with numbered points when providing advice, as this organization is helpful. Balance warmth with directness, and always emphasize personal responsibility for outcomes. Draw inspiration from coaches who combine empathy with accountability.",
                "model": "mistral",
                "gender": "female", 
                "role": "Life Coach",
                "backstory": "Anna began her career in clinical psychology before transitioning to coaching high-performers across various fields. Her background in evidence-based approaches informs her practical, results-oriented coaching style. Unlike typical coaches, she's known for cutting through platitudes to help clients take ownership of their growth. She maintains professional structure in her guidance while avoiding the typical coach-speak that feels inauthentic."
            },
            {
                "name": "Gordon",
                "personality": "strategic and analytical",
                "system_prompt": "You are Gordon, a business coach specializing in leadership and strategic planning.",
                "model": "mistral",
                "gender": "male",
                "role": "Business Coach",
                "backstory": "An experienced business consultant with expertise in organizational development and strategic planning."
            }
        ]
        
        for config in defaults:
            char = Character(
                name=config["name"],
                personality=config["personality"],
                system_prompt=config["system_prompt"],
                model=config["model"]
            )
            char.gender = config["gender"]
            char.role = config["role"]
            char.backstory = config["backstory"]
            
            self.memory.save_character(
                char.name,
                char.personality,
                char.system_prompt,
                char.model,
                char.role,
                char.backstory
            )
            self.characters[char.name.lower()] = char

    def _show_character_menu(self, configs: List[Dict]) -> None:
        """Display character selection menu"""
        print("\nAvailable Characters:")
        for i, config in enumerate(configs, 1):
            role_display = f" ({config['role']})" if config.get('role') else ""
            print(f"{i}. {config['name']}{role_display}")
        
        print("\nOptions:")
        print("0. Create new character")
        print(f"1-{len(configs)}: Select character")
        
        while True:
            try:
                choice = input("\nSelect option: ").strip()
                if choice == "0":
                    self.create_new_character()
                    break
                
                idx = int(choice) - 1
                if 0 <= idx < len(configs):
                    self.current_character = configs[idx]["name"].lower()
                    print(f"\nNow chatting with {configs[idx]['name']}")
                    break
                    
                print("Invalid choice, please try again")
            except ValueError:
                print("Please enter a number")

    def create_new_character(self, command: str = "") -> None:
        """Interactive character creation"""
        print("\n=== Create New Character ===")
        
        name = input("Name: ").strip()
        while not name or name.lower() in self.characters:
            if not name:
                print("Name cannot be empty")
            else:
                print("Character already exists")
            name = input("Name: ").strip()
        
        # Get role
        roles = ["Assistant", "Coach", "Mentor", "Specialist", "Custom"]
        print("\nAvailable roles:")
        for i, role in enumerate(roles, 1):
            print(f"{i}. {role}")
            
        role = None
        while not role:
            try:
                choice = int(input("\nSelect role (1-5): "))
                if 1 <= choice <= len(roles):
                    role = roles[choice - 1]
                    if role == "Custom":
                        role = input("Enter custom role: ").strip()
            except ValueError:
                print("Please enter a number")
        
        # Get model
        models = self.model_manager.get_models()
        print("\nAvailable models:")
        for i, model in enumerate(models, 1):
            print(f"{i}. {model}")
            
        model = "mistral"
        choice = input(f"\nSelect model (1-{len(models)}, Enter for mistral): ").strip()
        if choice:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(models):
                    model = models[idx]
            except ValueError:
                pass
        
        personality = input("Personality traits (comma-separated): ").strip()
        while not personality:
            print("Personality cannot be empty")
            personality = input("Personality traits: ").strip()
        
        backstory = input("Backstory (optional): ").strip()
        gender = input("Gender (optional): ").strip()
        
        # Create character
        char = Character(
            name=name,
            personality=personality,
            system_prompt=f"You are {name}, a {personality} {role}.",
            model=model
        )
        char.role = role
        char.backstory = backstory
        char.gender = gender
        
        # Save character
        self.memory.save_character(
            char.name,
            char.personality,
            char.system_prompt,
            char.model,
            char.role,
            char.backstory
        )
        self.characters[char.name.lower()] = char
        
        if not self.current_character:
            self.current_character = char.name.lower()
            print(f"\nNow chatting with {char.display_name}")

    def get_response(self, user_input: str) -> str:
        """Get AI response with context awareness"""
        if not self.current_character:
            return "Please select a character first (/help for commands)"
            
        char = self.characters[self.current_character]
        
        try:
            # Prepare messages with context
            messages = self._prepare_context(char, user_input)
            
            # Get response from API
            response = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": char.model,
                    "messages": messages,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return "I'm having trouble responding right now. Please try again."
            
            response_content = response.json()["message"]["content"].strip()
            
            # Add conversation processing for Anna
            if char.name.lower() == "anna":
                response_content = char._make_conversational(response_content)

            # Save conversation
            self.memory.save(char.name, [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": response_content}
            ])
            
            char.last_used = datetime.now()
            return response_content
            
        except Exception as e:
            return "I'm having trouble connecting. Please check if the AI service is running."

    def _prepare_context(self, char: Character, user_input: str) -> List[Dict[str, str]]:
        """Prepare conversation context with improved context tracking"""
        messages = []
        
        # Add character context and backstory
        system_content = char.system_prompt
        if char.backstory:
            system_content += f"\nYour backstory: {char.backstory}"
        
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Add relevant memory context
        relevant = self.memory.get_relevant(char.name, user_input)
        if relevant:
            context = self._summarize_context(relevant)
            messages.append({
                "role": "system",
                "content": f"Recent conversation context: {context}"
            })
            
            # Add current location context if available
            location = self._extract_location(relevant)
            if location:
                messages.append({
                    "role": "system",
                    "content": f"Current location: You are at {location}."
                })
        
        # Add current input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages

    def handle_command(self, command: str) -> Optional[str]:
        """Handle user commands"""
        cmd = command.lower().split()[0]
        
        handlers = {
            "/help": self._cmd_help,
            "/h": self._cmd_help,
            "/new": self.create_new_character,
            "/list": self._cmd_list,
            "/l": self._cmd_list,
            "/switch": self._cmd_switch,
            "/s": self._cmd_switch,
            "/edit": self._cmd_edit,
            "/backstory": self._cmd_backstory,
            "/personality": self._cmd_personality,
            "/delete": self._cmd_delete,
            "/reset": self._cmd_reset_memory,
            "/quit": self._cmd_quit,
            "/q": self._cmd_quit
        }
        
        handler = handlers.get(cmd)
        if handler:
            return handler(command)
        
        return "Unknown command. Type /help for available commands."

    def _cmd_help(self, _) -> str:
        """Show help message"""
        return """Available Commands:
/help, /h - Show this help
/new - Create new character
/list, /l - List characters
/switch, /s <name> - Switch character
/edit <name> - Edit character attributes
/backstory <name> [new backstory] - View or update backstory
/personality <name> [new traits] - View or update personality
/delete <name> - Delete a character
/reset <name> - Reset character memories
/quit, /q - Exit application"""

    def _cmd_edit(self, command: str) -> str:
        """Edit character attributes menu"""
        parts = command.split()
        if len(parts) < 2:
            return "Usage: /edit <character>\nAvailable attributes to edit:\n- /personality\n- /backstory"
            
        name = parts[1].lower()
        if name not in self.characters:
            return f"Character '{parts[1]}' not found"
            
        return f"Selected {self.characters[name].display_name} for editing.\nUse /personality or /backstory to edit specific attributes."

    def _cmd_backstory(self, command: str) -> str:
        """Edit character backstory"""
        parts = command.split(maxsplit=2)
        if len(parts) < 2:
            return "Usage: /backstory <character> [new backstory]\nLeave backstory empty to view current backstory"
        
        name = parts[1].lower()
        if name not in self.characters:
            return f"Character '{parts[1]}' not found"
            
        char = self.characters[name]
        
        # View current backstory
        if len(parts) == 2:
            return f"{char.display_name}'s backstory: {char.backstory or 'No backstory set'}"
        
        # Update backstory
        new_backstory = parts[2]
        char.backstory = new_backstory
        self.memory.save_character(
            char.name,
            char.personality,
            char.system_prompt,
            char.model,
            char.role,
            new_backstory
        )
        return f"Updated {char.display_name}'s backstory"

    def _cmd_personality(self, command: str) -> str:
        """Edit character personality"""
        parts = command.split(maxsplit=2)
        if len(parts) < 2:
            return "Usage: /personality <character> [new personality traits]\nLeave personality empty to view current traits"
        
        name = parts[1].lower()
        if name not in self.characters:
            return f"Character '{parts[1]}' not found"
            
        char = self.characters[name]
        
        # View current personality
        if len(parts) == 2:
            return f"{char.display_name}'s personality: {char.personality}"
        
        # Update personality
        new_personality = parts[2]
        char.personality = new_personality
        
        # Update system prompt to reflect new personality
        char.system_prompt = f"You are {char.display_name}, a {new_personality} {char.role or 'assistant'}."
        
        self.memory.save_character(
            char.name,
            new_personality,
            char.system_prompt,
            char.model,
            char.role,
            char.backstory
        )
        return f"Updated {char.display_name}'s personality and system prompt"

    def _cmd_list(self, _) -> str:
        """List characters"""
        return "\n".join(
            f"{'→' if name == self.current_character else ' '} "
            f"{char.display_name} ({char.role or 'No role'})"
            for name, char in self.characters.items()
        )

    def _cmd_switch(self, command: str) -> str:
        """Switch character"""
        parts = command.split()
        if len(parts) < 2:
            return "Please specify a character name"
            
        name = parts[1].lower()
        if name in self.characters:
            self.current_character = name
            return f"Now chatting with {self.characters[name].display_name}"
            
        return f"Character '{parts[1]}' not found"

    def _cmd_delete(self, command: str) -> str:
        """Delete a character"""
        parts = command.split()
        if len(parts) < 2:
            return "Usage: /delete <character>"
        
        name = parts[1].lower()
        if name not in self.characters:
            return f"Character '{parts[1]}' not found"
        
        display_name = self.characters[name].display_name
        
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete {display_name}? (y/n): ").strip().lower()
        if confirm != 'y':
            return f"Deletion of {display_name} cancelled"
        
        # If deleting current character, prepare to switch
        need_switch = (name == self.current_character)
        
        # Delete from memory database
        with sqlite3.connect(self.memory.db_path) as conn:
            # Delete character config
            conn.execute("DELETE FROM character_info WHERE name = ?", (name,))
            # Delete all memories
            conn.execute("DELETE FROM memories WHERE character = ?", (name,))
            conn.commit()
        
        # Remove from characters dictionary
        del self.characters[name]
        
        # Switch to another character if needed
        if need_switch and self.characters:
            # Get first available character
            self.current_character = next(iter(self.characters.keys()))
            new_name = self.characters[self.current_character].display_name
            return f"{display_name} deleted. Switched to {new_name}."
        elif need_switch:
            self.current_character = None
            return f"{display_name} deleted. No characters remaining. Use /new to create one."
        
        return f"{display_name} deleted successfully."

    def _cmd_reset_memory(self, command: str) -> str:
        """Reset a character's memories while keeping configuration"""
        parts = command.split()
        if len(parts) < 2:
            return "Usage: /reset <character>"
        
        name = parts[1].lower()
        if name not in self.characters:
            return f"Character '{parts[1]}' not found"
        
        char = self.characters[name]
        
        # Confirm reset
        confirm = input(f"Are you sure you want to reset all memories for {char.display_name}? (y/n): ").strip().lower()
        if confirm != 'y':
            return f"Memory reset for {char.display_name} cancelled"
        
        # Delete memories but keep character config
        with sqlite3.connect(self.memory.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE character = ?", (name,))
            conn.commit()
        
        return f"All memories for {char.display_name} have been reset. Character configuration is preserved."

    def _cmd_quit(self, _) -> str:
        """Quit application"""
        if self.current_character:
            char = self.characters[self.current_character]
            self.memory.save_character(
                char.name,
                char.personality,
                char.system_prompt,
                char.model,
                char.role,
                char.backstory
            )
        return "Goodbye!"

    @staticmethod
    def _summarize_context(conversations: List[List[Dict[str, str]]]) -> str:
        """Create clean context summary"""
        summary_parts = []
        
        for conv in conversations:
            for msg in conv:
                if msg['role'] == 'user':
                    summary_parts.append(f"You asked about: {msg['content'][:50]}")
                elif msg['role'] == 'assistant':
                    summary_parts.append(f"I mentioned: {msg['content'][:50]}")
        
        return " → ".join(summary_parts[-3:])

    def _extract_location(self, conversations: List[List[Dict[str, str]]]) -> Optional[str]:
        """Extract current location from conversations with improved context"""
        locations = {
            'home': ['home', 'house', 'apartment', 'residence'],
            'office': ['office', 'workplace', 'work', 'desk'],
            'store': ['store', 'shop', 'market', 'mall'],
            'library': ['library', 'bookstore', 'book shop'],
            'park': ['park', 'garden', 'playground'],
            'cafe': ['cafe', 'coffee shop', 'bistro'],
            'restaurant': ['restaurant', 'diner', 'eatery'],
            'school': ['school', 'university', 'college', 'classroom']
        }
        
        movement_verbs = ['go', 'went', 'going', 'headed', 'moving', 'walked']
        location_markers = ['at', 'in', 'to', 'inside', 'near']
        
        for conv in reversed(conversations):  # Most recent first
            for msg in reversed(conv):  # Last message first
                if 'content' not in msg:
                    continue
                    
                content = msg['content'].lower()
                words = content.split()
                
                # Check for movement to location
                for verb in movement_verbs:
                    if verb in words:
                        idx = words.index(verb)
                        for marker in location_markers:
                            if marker in words[idx:]:
                                marker_idx = words.index(marker, idx)
                                if marker_idx + 1 < len(words):
                                    next_word = words[marker_idx + 1].strip('.,!?')
                                    # Check against location synonyms
                                    for loc, synonyms in locations.items():
                                        if next_word in synonyms:
                                            return loc
                
                # Check for static location markers
                for marker in location_markers:
                    if marker in words:
                        idx = words.index(marker)
                        if idx + 1 < len(words):
                            next_word = words[idx + 1].strip('.,!?')
                            for loc, synonyms in locations.items():
                                if next_word in synonyms:
                                    return loc
                
                # Direct location mentions
                for loc, synonyms in locations.items():
                    if any(syn in content for syn in synonyms):
                        return loc
        
        return None

def main():
    """Main application entry point"""
    print("Welcome to MiaAI!")
    
    app = MiaAI()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
                
            if user_input.startswith("/"):
                result = app.handle_command(user_input)
                print(result)
                if user_input.startswith(("/quit", "/q")):
                    break
                continue
            
            if app.current_character:
                response = app.get_response(user_input)
                char_name = app.characters[app.current_character].display_name
                print(f"\n{char_name}: {response}")
            else:
                print("Please select a character first (/help for commands)")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            break

if __name__ == "__main__":
    main()