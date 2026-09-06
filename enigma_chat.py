import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# ------------------------------------------
# CLASSES DEL MOTOR ENIGMA
# ------------------------------------------

class Rotor:
    """Representa un rotor individual de la màquina Enigma amb Grundstellung i Ringstellung."""
    def __init__(self, wiring: str, notch: str, position: str = 'A', ring_setting: str = 'A'):
        self.wiring = wiring.upper()          # Cablejat intern (26 lletres)
        self.notch = notch.upper()            # Posició de l'osca
        self.position = ord(position.upper()) - 65  # Grundstellung (0-25)
        self.ring_setting = ord(ring_setting.upper()) - 65  # Ringstellung (0-25)

    def step(self) -> bool:
        """Avança el rotor una posició. Retorna True si està a l'osca (notch)."""
        at_notch = (chr(self.position + 65) in self.notch)
        self.position = (self.position + 1) % 26
        return at_notch

    def forward(self, c_idx: int) -> int:
        """Entrada de dreta a esquerra tenint en compte posició i anell."""
        shift = self.position - self.ring_setting
        input_idx = (c_idx + shift) % 26
        out_char = self.wiring[input_idx]
        out_idx = ord(out_char) - 65
        return (out_idx - shift) % 26

    def backward(self, c_idx: int) -> int:
        """Entrada d'esquerra a dreta (tornada) tenint en compte posició i anell."""
        shift = self.position - self.ring_setting
        input_idx = (c_idx + shift) % 26
        out_char = chr(input_idx + 65)
        out_idx = self.wiring.index(out_char)
        return (out_idx - shift) % 26


class Reflector:
    """Representa el reflector (Umkehrwalze), una involució fixa."""
    def __init__(self, wiring: str):
        self.wiring = wiring.upper()

    def reflect(self, c_idx: int) -> int:
        out_char = self.wiring[c_idx]
        return ord(out_char) - 65


class Plugboard:
    """Representa el claviller de connexions (Steckerbrett)."""
    def __init__(self, pairs: list):
        self.mapping = {}
        for i in range(26):
            char = chr(i + 65)
            self.mapping[char] = char

        for pair in pairs:
            if len(pair) == 2:
                u, v = pair[0].upper(), pair[1].upper()
                self.mapping[u] = v
                self.mapping[v] = u

    def swap(self, c_idx: int) -> int:
        char = chr(c_idx + 65)
        swapped = self.mapping.get(char, char)
        return ord(swapped) - 65


class EnigmaMachine:
    """Mòdul central que connecta tots els components de la màquina Enigma."""
    ROTOR_DEFINITIONS = {
        'I':   ('EKMFLGDQVZNTOWYHXUSPAIBRCJ', 'Q'),
        'II':  ('AJDKSIRUXBLHWTMCQGZNPYFVOE', 'E'),
        'III': ('BDFHJLCPRTXVZNYEIWGAKMUSQO', 'V'),
        'IV':  ('ESOVPZJAYQUIRHXLNFTGKDCMWB', 'J'),
        'V':   ('VZBRGITYUPSDNHLXAWMJQOFECK', 'Z')
    }
    REFLECTOR_DEFINITIONS = {
        'B': 'YRUHQSLDPXNGOKMIEBFZCWVJAT',
        'C': 'FVPJIAOYEDRZXWGCTKUQSBNMHL'
    }

    def __init__(self, rotor_names=('I', 'II', 'III'), reflector_name='B', 
                 positions=('A', 'A', 'A'), ring_settings=('A', 'A', 'A'), plugboard_pairs=None):
        if plugboard_pairs is None:
            plugboard_pairs = []

        self.rotors = []
        for name, pos, ring in zip(rotor_names, positions, ring_settings):
            wiring, notch = self.ROTOR_DEFINITIONS[name]
            self.rotors.append(Rotor(wiring, notch, position=pos, ring_setting=ring))

        self.reflector = Reflector(self.REFLECTOR_DEFINITIONS[reflector_name])
        self.plugboard = Plugboard(plugboard_pairs)

    def _rotate_rotors(self):
        """Mecanisme de rotació (simple i en cascada)."""
        left, middle, right = self.rotors[0], self.rotors[1], self.rotors[2]

        right_at_notch = right.step()
        middle_at_notch = False

        if right_at_notch:
            middle_at_notch = middle.step()

        if middle_at_notch:
            left.step()

    def process_char(self, char: str) -> str:
        """Processa un sol caràcter. Si no és lletra A-Z, es retorna el caràcter sense modificacions."""
        if not char.isalpha():
            return char

        is_lower = char.islower()
        c_idx = ord(char.upper()) - 65

        # 1. Avançar rotors
        self._rotate_rotors()

        # 2. Claviller (Entrada)
        c_idx = self.plugboard.swap(c_idx)

        # 3. Rotors (Directe: Dreta -> Centre -> Esquerra)
        c_idx = self.rotors[2].forward(c_idx)
        c_idx = self.rotors[1].forward(c_idx)
        c_idx = self.rotors[0].forward(c_idx)

        # 4. Reflector
        c_idx = self.reflector.reflect(c_idx)

        # 5. Rotors (Invers: Esquerra -> Centre -> Dreta)
        c_idx = self.rotors[0].backward(c_idx)
        c_idx = self.rotors[1].backward(c_idx)
        c_idx = self.rotors[2].backward(c_idx)

        # 6. Claviller (Sortida)
        c_idx = self.plugboard.swap(c_idx)

        res_char = chr(c_idx + 65)
        return res_char.lower() if is_lower else res_char

    def process_text(self, text: str) -> str:
        """Xifra o desxifra una cadena sencera de text."""
        return "".join(self.process_char(c) for c in text)


# ------------------------------------------
# INTERFÍCIE GRÀFICA I CLIENT DE XAT
# ------------------------------------------

class EnigmaChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Xat Enigma - Criptografia Digital")
        self.root.geometry("720x900")
        self.root.minsize(680, 900)

        self.client_socket = None
        self.connected = False

        # Estil visual
        self.style = ttk.Style()
        if "xpnative" in self.style.theme_names():
            self.style.theme_use("xpnative")

        self._build_ui()

    def _build_ui(self):
        # --- 1. Marc de connexió i Usuari ---
        frame_conn = ttk.LabelFrame(self.root, text=" Connexió al Servidor ", padding=10)
        frame_conn.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_conn, text="Usuari:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        self.entry_user = ttk.Entry(frame_conn, width=12)
        self.entry_user.insert(0, "Usuari1")
        self.entry_user.grid(row=0, column=1, padx=5, pady=2, sticky="w")

        ttk.Label(frame_conn, text="IP:").grid(row=0, column=2, padx=5, pady=2, sticky="e")
        self.entry_ip = ttk.Entry(frame_conn, width=12)
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.grid(row=0, column=3, padx=5, pady=2, sticky="w")

        ttk.Label(frame_conn, text="Port:").grid(row=0, column=4, padx=5, pady=2, sticky="e")
        self.entry_port = ttk.Entry(frame_conn, width=6)
        self.entry_port.insert(0, "5555")
        self.entry_port.grid(row=0, column=5, padx=5, pady=2, sticky="w")

        self.btn_connect = ttk.Button(frame_conn, text="Connectar", command=self.connect_to_server)
        self.btn_connect.grid(row=0, column=6, padx=10, pady=2)

        # --- 2. Marc de la configuració d'Enigma ---
        frame_enigma = ttk.LabelFrame(self.root, text=" Configuració de la Clau Enigma ", padding=10)
        frame_enigma.pack(fill="x", padx=10, pady=5)

        alphabet = [chr(i) for i in range(65, 91)]
        rotor_options = ["I", "II", "III", "IV", "V"]

        # Reflector
        ttk.Label(frame_enigma, text="Reflector:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.combo_reflector = ttk.Combobox(frame_enigma, values=["B", "C"], width=5, state="readonly")
        self.combo_reflector.set("B")
        self.combo_reflector.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Capçaleres dels rotors
        ttk.Label(frame_enigma, text="Esquerra (1)", font=('Helvetica', 9, 'bold')).grid(row=0, column=2, padx=5)
        ttk.Label(frame_enigma, text="Centre (2)", font=('Helvetica', 9, 'bold')).grid(row=0, column=3, padx=5)
        ttk.Label(frame_enigma, text="Dreta (3)", font=('Helvetica', 9, 'bold')).grid(row=0, column=4, padx=5)

        # Selecció de Rotors
        ttk.Label(frame_enigma, text="Rotors:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        
        self.combo_rotor_left = ttk.Combobox(frame_enigma, values=rotor_options, width=5, state="readonly")
        self.combo_rotor_left.set("I")
        self.combo_rotor_left.grid(row=1, column=2, padx=5, pady=2)

        self.combo_rotor_mid = ttk.Combobox(frame_enigma, values=rotor_options, width=5, state="readonly")
        self.combo_rotor_mid.set("II")
        self.combo_rotor_mid.grid(row=1, column=3, padx=5, pady=2)

        self.combo_rotor_right = ttk.Combobox(frame_enigma, values=rotor_options, width=5, state="readonly")
        self.combo_rotor_right.set("III")
        self.combo_rotor_right.grid(row=1, column=4, padx=5, pady=2)

        # Grundstellung (Posició inicial)
        ttk.Label(frame_enigma, text="Grundstellung:").grid(row=2, column=0, padx=5, pady=5, sticky="e")

        self.combo_pos_left = ttk.Combobox(frame_enigma, values=alphabet, width=5, state="readonly")
        self.combo_pos_left.set("A")
        self.combo_pos_left.grid(row=2, column=2, padx=5, pady=2)

        self.combo_pos_mid = ttk.Combobox(frame_enigma, values=alphabet, width=5, state="readonly")
        self.combo_pos_mid.set("A")
        self.combo_pos_mid.grid(row=2, column=3, padx=5, pady=2)

        self.combo_pos_right = ttk.Combobox(frame_enigma, values=alphabet, width=5, state="readonly")
        self.combo_pos_right.set("A")
        self.combo_pos_right.grid(row=2, column=4, padx=5, pady=2)

        # Ringstellung (Configuració de l'anell)
        ttk.Label(frame_enigma, text="Ringstellung:").grid(row=3, column=0, padx=5, pady=5, sticky="e")

        self.combo_ring_left = ttk.Combobox(frame_enigma, values=alphabet, width=5, state="readonly")
        self.combo_ring_left.set("A")
        self.combo_ring_left.grid(row=3, column=2, padx=5, pady=2)

        self.combo_ring_mid = ttk.Combobox(frame_enigma, values=alphabet, width=5, state="readonly")
        self.combo_ring_mid.set("A")
        self.combo_ring_mid.grid(row=3, column=3, padx=5, pady=2)

        self.combo_ring_right = ttk.Combobox(frame_enigma, values=alphabet, width=5, state="readonly")
        self.combo_ring_right.set("A")
        self.combo_ring_right.grid(row=3, column=4, padx=5, pady=2)

        # Claviller
        ttk.Label(frame_enigma, text="Claviller (ex: AB CD EX):").grid(row=4, column=0, columnspan=2, padx=5, pady=8, sticky="e")
        self.entry_plugboard = ttk.Entry(frame_enigma, width=30)
        self.entry_plugboard.insert(0, "")
        self.entry_plugboard.grid(row=4, column=2, columnspan=3, padx=5, pady=8, sticky="w")

        # --- 3. Àrea de Xat ---
        frame_chat = ttk.Frame(self.root)
        frame_chat.pack(fill="both", expand=True, padx=10, pady=5)

        self.chat_box = tk.Text(frame_chat, state='disabled', wrap='word', font=('Consolas', 10))
        self.chat_box.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(frame_chat, command=self.chat_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.chat_box['yscrollcommand'] = scrollbar.set

        # --- 4. Entrada de missatges ---
        frame_input = ttk.Frame(self.root)
        frame_input.pack(fill="x", padx=10, pady=10)

        self.entry_msg = ttk.Entry(frame_input)
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.entry_msg.bind("<Return>", lambda event: self.send_message())

        btn_send = ttk.Button(frame_input, text="Enviar", command=self.send_message)
        btn_send.pack(side="right")

    def get_enigma_instance(self) -> EnigmaMachine:
        """Crea una instància d'EnigmaMachine basada en la selecció dels desplegables."""
        reflector_name = self.combo_reflector.get()
        rotor_names = (
            self.combo_rotor_left.get(),
            self.combo_rotor_mid.get(),
            self.combo_rotor_right.get()
        )
        positions = (
            self.combo_pos_left.get(),
            self.combo_pos_mid.get(),
            self.combo_pos_right.get()
        )
        rings = (
            self.combo_ring_left.get(),
            self.combo_ring_mid.get(),
            self.combo_ring_right.get()
        )
        plug_pairs = self.entry_plugboard.get().strip().split()

        return EnigmaMachine(
            rotor_names=rotor_names,
            reflector_name=reflector_name,
            positions=positions,
            ring_settings=rings,
            plugboard_pairs=plug_pairs
        )

    def connect_to_server(self):
        if self.connected:
            return

        username = self.entry_user.get().strip()
        if not username:
            messagebox.showwarning("Atenció", "El nom d'usuari no pot estar buit.")
            return

        ip = self.entry_ip.get().strip()
        port = int(self.entry_port.get().strip())

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((ip, port))
            self.connected = True
            self.btn_connect.config(state="disabled")
            self.entry_user.config(state="disabled")
            self._log_chat("[SISTEMA] Connectat amb èxit al servidor.\n")

            threading.Thread(target=self.receive_messages, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error de Connexió", f"No s'ha pogut connectar: {e}")

    def send_message(self):
        if not self.connected:
            messagebox.showwarning("Atenció", "Has de connectar-te primer al servidor.")
            return

        plaintext = self.entry_msg.get()
        username = self.entry_user.get().strip()

        if not plaintext:
            return

        try:
            enigma = self.get_enigma_instance()
            ciphertext = enigma.process_text(plaintext)

            # S'envia el missatge en format: "Usuari: TextoCifrado"
            payload = f"{username}: {ciphertext}"
            self.client_socket.send(payload.encode('utf-8'))
            self.entry_msg.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error de Xifratge", f"Configuració Enigma invàlida: {e}")

    def receive_messages(self):
        while self.connected:
            try:
                data = self.client_socket.recv(1024)
                if not data:
                    break
                
                raw_payload = data.decode('utf-8')

                # Separar l'usuari del text xifrat
                if ":" in raw_payload:
                    sender, ciphertext = raw_payload.split(":", 1)
                    sender = sender.strip()
                    ciphertext = ciphertext.strip()
                else:
                    sender = "Desconegut"
                    ciphertext = raw_payload

                try:
                    enigma = self.get_enigma_instance()
                    decrypted_text = enigma.process_text(ciphertext)
                except Exception:
                    decrypted_text = "[Error en el desxifratge]"

                msg_display = f"[{sender}]\n  Xifrat: {ciphertext}\n  Desxifrat: {decrypted_text}\n" + "-"*40 + "\n"
                self._log_chat(msg_display)

            except Exception:
                break

        self.connected = False
        self._log_chat("[SISTEMA] S'ha perdut la connexió amb el servidor.\n")

    def _log_chat(self, text: str):
        self.chat_box.config(state='normal')
        self.chat_box.insert(tk.END, text)
        self.chat_box.see(tk.END)
        self.chat_box.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    app = EnigmaChatApp(root)
    root.mainloop()
