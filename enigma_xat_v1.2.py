import socket
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

# ------------------------------------------
# CLASSES DEL MOTOR ENIGMA
# ------------------------------------------

class Rotor:
    """Representa un rotor individual de la màquina Enigma amb Grundstellung i Ringstellung."""
    def __init__(self, wiring: str, notch: str, position: str = 'A', ring_setting: str = 'A'):
        self.wiring = wiring.upper()                        # Cablejat intern (26 lletres)
        self.notch = notch.upper()                          # Posició de l'osca
        self.position = ord(position.upper()) - 65          # Grundstellung (0-25)
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
        left, middle, right = self.rotors[0], self.rotors[1], self.rotors[2]

        # Comprovar si el rotor central o el dret estan en el notch abans del pas
        middle_in_notch = chr(middle.position + 65) in middle.notch
        right_in_notch = chr(right.position + 65) in right.notch

        # El rotor central fa double stepping si està en el notch
        if middle_in_notch:
            middle.step()
            left.step()

        # El rotor dret fa avançar el central quan arriba en el notch
        elif right_in_notch:
            middle.step()

        # El rotor dret sempre avança a cada pulsació
        right.step()

    def process_char(self, char: str) -> str:
        """Processa un sol caràcter. Si no és lletra A-Z, es retorna el caràcter sense modificacions."""
        if not char.isalpha():
            return char

        is_lower = char.islower()
        c_idx = ord(char.upper()) - 65

        # Avançar rotors
        self._rotate_rotors()

        # Claviller (Entrada)
        c_idx = self.plugboard.swap(c_idx)

        # Rotors (Directe: Dreta -> Centre -> Esquerra)
        c_idx = self.rotors[2].forward(c_idx)
        c_idx = self.rotors[1].forward(c_idx)
        c_idx = self.rotors[0].forward(c_idx)

     # Reflector
        c_idx = self.reflector.reflect(c_idx)

       # Rotors (Invers: Esquerra -> Centre -> Dreta)
        c_idx = self.rotors[0].backward(c_idx)
        c_idx = self.rotors[1].backward(c_idx)
        c_idx = self.rotors[2].backward(c_idx)

        # Claviller (Sortida)
        c_idx = self.plugboard.swap(c_idx)

        res_char = chr(c_idx + 65)
        return res_char.lower() if is_lower else res_char

    def process_text(self, text: str) -> str:
        """Xifra o desxifra una cadena sencera de text."""
        return "".join(self.process_char(c) for c in text)


# ------------------------------------------
# COLORS
# ------------------------------------------

class M3:
    PRIMARY = "#6750A4"
    ON_PRIMARY = "#FFFFFF"
    PRIMARY_CONTAINER = "#EADDFF"
    ON_PRIMARY_CONTAINER = "#21005D"

    SECONDARY = "#625B71"
    ON_SECONDARY = "#FFFFFF"
    SECONDARY_CONTAINER = "#E8DEF8"
    ON_SECONDARY_CONTAINER = "#1D192B"

    TERTIARY = "#7D5260"
    TERTIARY_CONTAINER = "#FFD8E4"

    ERROR = "#B3261E"
    ERROR_CONTAINER = "#F9DEDC"
    ON_ERROR_CONTAINER = "#410E0B"

    SUCCESS = "#2E7D32"

    SURFACE = "#FEF7FF"
    SURFACE_DIM = "#DED8E1"
    SURFACE_BRIGHT = "#FEF7FF"
    SURFACE_CONTAINER_LOWEST = "#FFFFFF"
    SURFACE_CONTAINER_LOW = "#F7F2FA"
    SURFACE_CONTAINER = "#F3EDF7"
    SURFACE_CONTAINER_HIGH = "#ECE6F0"
    SURFACE_CONTAINER_HIGHEST = "#E6E0E9"

    ON_SURFACE = "#1D1B20"
    ON_SURFACE_VARIANT = "#49454F"

    OUTLINE = "#79747E"
    OUTLINE_VARIANT = "#CAC4D0"


def _pick_font_family(preferred):
    available = set(tkfont.families())
    """Torna la primera família de la llista que existeixi al sistema."""
    for name in preferred:
        if name in available:
            return name
    return "TkDefaultFont"


# ------------------------------------------
# UI I CLIENT DE XAT
# ------------------------------------------

class EnigmaChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Xat Enigma · Criptografia Digital")
        self.root.geometry("760x800")
        self.root.minsize(700, 750)
        self.root.configure(bg=M3.SURFACE)

        self.client_socket = None
        self.connected = False

        # Fonts
        body_family = _pick_font_family(["Roboto", "Segoe UI", "Helvetica Neue", "Helvetica", "Arial"])
        mono_family = _pick_font_family(["Roboto Mono", "Consolas", "Menlo", "Courier New"])

        self.font_display = (body_family, 18, "bold")       # Top-app bar
        self.font_title = (body_family, 11, "bold")         # Títols de secció
        self.font_label = (body_family, 10)                 # Etiquetes de camp
        self.font_body = (body_family, 10)                  # Text dels inputs
        self.font_button = (body_family, 10, "bold")        # Botons
        self.font_mono = (mono_family, 10)                  # Contingut del xat

        self._configure_style()
        self._build_ui()

    # ------------------------------------------
    # ESTIL
    # ------------------------------------------
    def _configure_style(self):
        self.style = ttk.Style(self.root)
        if "clam" in self.style.theme_names():
            self.style.theme_use("clam")

        s = self.style

       # --- Contenidors ---
        s.configure("Surface.TFrame", background=M3.SURFACE)
        s.configure("TopBar.TFrame", background=M3.PRIMARY)
        s.configure("Card.TFrame", background=M3.SURFACE_CONTAINER, relief="flat")

        s.configure(
            "Card.TLabelframe",
            background=M3.SURFACE_CONTAINER,
            bordercolor=M3.OUTLINE_VARIANT,
            borderwidth=1,
            relief="solid",
        )
        s.configure(
            "Card.TLabelframe.Label",
            background=M3.SURFACE_CONTAINER,
            foreground=M3.PRIMARY,
            font=self.font_title,
        )

        # --- Etiquetes ---
        s.configure("TLabel", background=M3.SURFACE_CONTAINER, foreground=M3.ON_SURFACE_VARIANT, font=self.font_label)
        s.configure("Heading.TLabel", background=M3.SURFACE_CONTAINER, foreground=M3.ON_SURFACE, font=self.font_title)
        s.configure("OnBar.TLabel", background=M3.PRIMARY, foreground=M3.ON_PRIMARY)

        # --- Botó 1 (estàtic) ---
        s.configure(
            "Filled.TButton",
            background=M3.PRIMARY,
            foreground=M3.ON_PRIMARY,
            font=self.font_button,
            padding=(18, 10),
            borderwidth=0,
            relief="flat",
        )
        s.map(
            "Filled.TButton",
            background=[("disabled", M3.SURFACE_CONTAINER_HIGHEST), ("active", "#7A67B5"), ("pressed", "#59468F")],
            foreground=[("disabled", M3.OUTLINE)],
        )

     # --- Botó 2 (acció secundària M3, com Enviar) ---
        s.configure(
            "Tonal.TButton",
            background=M3.SECONDARY_CONTAINER,
            foreground=M3.ON_SECONDARY_CONTAINER,
            font=self.font_button,
            padding=(20, 10),
            borderwidth=0,
            relief="flat",
        )
        s.map(
            "Tonal.TButton",
            background=[("disabled", M3.SURFACE_CONTAINER_HIGHEST), ("active", "#D9CCEE"), ("pressed", "#CBBEE0")],
            foreground=[("disabled", M3.OUTLINE)],
        )

     # --- Camps de text ---
        s.configure(
            "M3.TEntry",
            fieldbackground=M3.SURFACE_CONTAINER_HIGHEST,
            background=M3.SURFACE_CONTAINER_HIGHEST,
            foreground=M3.ON_SURFACE,
            bordercolor=M3.OUTLINE,
            lightcolor=M3.SURFACE_CONTAINER_HIGHEST,
            darkcolor=M3.SURFACE_CONTAINER_HIGHEST,
            insertcolor=M3.PRIMARY,
            padding=6,
            relief="flat",
        )
        s.map(
            "M3.TEntry",
            bordercolor=[("focus", M3.PRIMARY)],
            lightcolor=[("focus", M3.PRIMARY)],
            darkcolor=[("focus", M3.PRIMARY)],
        )

       # --- Combobox ---
        s.configure(
            "M3.TCombobox",
            fieldbackground=M3.SURFACE_CONTAINER_HIGHEST,
            background=M3.SURFACE_CONTAINER_HIGHEST,
            foreground=M3.ON_SURFACE,
            arrowcolor=M3.PRIMARY,
            bordercolor=M3.OUTLINE,
            selectbackground=M3.PRIMARY_CONTAINER,
            selectforeground=M3.ON_PRIMARY_CONTAINER,
            padding=4,
            relief="flat",
        )
        self.root.option_add("*TCombobox*Listbox.background", M3.SURFACE_CONTAINER_LOWEST)
        self.root.option_add("*TCombobox*Listbox.foreground", M3.ON_SURFACE)
        self.root.option_add("*TCombobox*Listbox.selectBackground", M3.PRIMARY_CONTAINER)
        self.root.option_add("*TCombobox*Listbox.selectForeground", M3.ON_PRIMARY_CONTAINER)
        self.root.option_add("*TCombobox*Listbox.font", self.font_body)

        # --- Barra de scroll ---
        s.configure(
            "M3.Vertical.TScrollbar",
            background=M3.SURFACE_CONTAINER_HIGH,
            troughcolor=M3.SURFACE_CONTAINER,
            bordercolor=M3.SURFACE_CONTAINER,
            arrowcolor=M3.ON_SURFACE_VARIANT,
            relief="flat",
        )
        s.map("M3.Vertical.TScrollbar", background=[("active", M3.OUTLINE_VARIANT)])

    # ------------------------------------------
    # UI FRAMES
    # ------------------------------------------
    def _build_ui(self):
        # --- Barra superior ---
        top_bar = ttk.Frame(self.root, style="TopBar.TFrame", padding=(20, 16))
        top_bar.pack(fill="x", side="top")

        ttk.Label(top_bar, text="Xat Enigma", style="OnBar.TLabel", font=self.font_display).pack(anchor="w")
        ttk.Label(
            top_bar, text="Reconstruint història · Simulació de la màquina Enigma",
            style="OnBar.TLabel", font=self.font_label,
        ).pack(anchor="w", pady=(2, 0))

        # --- Contenidor (frame principal) ---
        body = ttk.Frame(self.root, style="Surface.TFrame")
        body.pack(fill="both", expand=True)

        # --- Connexió ---
        frame_conn = ttk.LabelFrame(body, text="  Connexió al servidor  ", padding=14, style="Card.TLabelframe")
        frame_conn.pack(fill="x", padx=16, pady=(16, 8))

        ttk.Label(frame_conn, text="Usuari").grid(row=0, column=0, padx=(0, 6), pady=4, sticky="e")
        self.entry_user = ttk.Entry(frame_conn, width=12, style="M3.TEntry", font=self.font_body)
        self.entry_user.insert(0, "Usuari1")
        self.entry_user.grid(row=0, column=1, padx=6, pady=4, sticky="w")

        ttk.Label(frame_conn, text="IP").grid(row=0, column=2, padx=(16, 6), pady=4, sticky="e")
        self.entry_ip = ttk.Entry(frame_conn, width=12, style="M3.TEntry", font=self.font_body)
        self.entry_ip.insert(0, "127.0.0.1")
        self.entry_ip.grid(row=0, column=3, padx=6, pady=4, sticky="w")

        ttk.Label(frame_conn, text="Port").grid(row=0, column=4, padx=(16, 6), pady=4, sticky="e")
        self.entry_port = ttk.Entry(frame_conn, width=6, style="M3.TEntry", font=self.font_body)
        self.entry_port.insert(0, "5555")
        self.entry_port.grid(row=0, column=5, padx=6, pady=4, sticky="w")

        self.btn_connect = ttk.Button(
            frame_conn, text="Connectar", command=self.connect_to_server, style="Filled.TButton"
        )
        self.btn_connect.grid(row=0, column=6, padx=(16, 0), pady=4)

        # --- Config. Enigma ---
        frame_enigma = ttk.LabelFrame(
            body, text="  Configuració de la clau Enigma  ", padding=14, style="Card.TLabelframe"
        )
        frame_enigma.pack(fill="x", padx=16, pady=8)

        alphabet = [chr(i) for i in range(65, 91)]
        rotor_options = ["I", "II", "III", "IV", "V"]

       # Reflector
        ttk.Label(frame_enigma, text="Reflector").grid(row=0, column=0, padx=(0, 6), pady=6, sticky="e")
        self.combo_reflector = ttk.Combobox(
            frame_enigma, values=["B", "C"], width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_reflector.set("B")
        self.combo_reflector.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        # Rotors (vistes)
        ttk.Label(frame_enigma, text="Esquerra (1)", style="Heading.TLabel").grid(row=0, column=2, padx=6)
        ttk.Label(frame_enigma, text="Centre (2)", style="Heading.TLabel").grid(row=0, column=3, padx=6)
        ttk.Label(frame_enigma, text="Dreta (3)", style="Heading.TLabel").grid(row=0, column=4, padx=6)

       # Selecció de Rotors
        ttk.Label(frame_enigma, text="Rotors").grid(row=1, column=0, padx=(0, 6), pady=6, sticky="e")

        self.combo_rotor_left = ttk.Combobox(
            frame_enigma, values=rotor_options, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_rotor_left.set("I")
        self.combo_rotor_left.grid(row=1, column=2, padx=6, pady=4)

        self.combo_rotor_mid = ttk.Combobox(
            frame_enigma, values=rotor_options, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_rotor_mid.set("II")
        self.combo_rotor_mid.grid(row=1, column=3, padx=6, pady=4)

        self.combo_rotor_right = ttk.Combobox(
            frame_enigma, values=rotor_options, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_rotor_right.set("III")
        self.combo_rotor_right.grid(row=1, column=4, padx=6, pady=4)

        # Grundstellung
        ttk.Label(frame_enigma, text="Grundstellung").grid(row=2, column=0, padx=(0, 6), pady=6, sticky="e")

        self.combo_pos_left = ttk.Combobox(
            frame_enigma, values=alphabet, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_pos_left.set("A")
        self.combo_pos_left.grid(row=2, column=2, padx=6, pady=4)

        self.combo_pos_mid = ttk.Combobox(
            frame_enigma, values=alphabet, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_pos_mid.set("A")
        self.combo_pos_mid.grid(row=2, column=3, padx=6, pady=4)

        self.combo_pos_right = ttk.Combobox(
            frame_enigma, values=alphabet, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_pos_right.set("A")
        self.combo_pos_right.grid(row=2, column=4, padx=6, pady=4)

        # Ringstellung
        ttk.Label(frame_enigma, text="Ringstellung").grid(row=3, column=0, padx=(0, 6), pady=6, sticky="e")

        self.combo_ring_left = ttk.Combobox(
            frame_enigma, values=alphabet, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_ring_left.set("A")
        self.combo_ring_left.grid(row=3, column=2, padx=6, pady=4)

        self.combo_ring_mid = ttk.Combobox(
            frame_enigma, values=alphabet, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_ring_mid.set("A")
        self.combo_ring_mid.grid(row=3, column=3, padx=6, pady=4)

        self.combo_ring_right = ttk.Combobox(
            frame_enigma, values=alphabet, width=5, state="readonly", style="M3.TCombobox", font=self.font_body
        )
        self.combo_ring_right.set("A")
        self.combo_ring_right.grid(row=3, column=4, padx=6, pady=4)

        # Claviller
        ttk.Label(frame_enigma, text="Claviller (ex: AB CD EX)").grid(
            row=4, column=0, columnspan=2, padx=(0, 6), pady=(10, 4), sticky="e"
        )
        self.entry_plugboard = ttk.Entry(frame_enigma, width=32, style="M3.TEntry", font=self.font_body)
        self.entry_plugboard.insert(0, "")
        self.entry_plugboard.grid(row=4, column=2, columnspan=3, padx=6, pady=(10, 4), sticky="w")

        # ------------------------------------------
        # PACK ORDER
        # ------------------------------------------

        # ÀREA ENTRADA MISSATGES -> INFERIOR
        frame_input = ttk.Frame(body, style="Surface.TFrame", padding=(16, 8))
        frame_input.pack(fill="x", side="bottom", padx=16, pady=(8, 16))

        self.entry_msg = ttk.Entry(frame_input, style="M3.TEntry", font=self.font_body)
        self.entry_msg.pack(side="left", fill="x", expand=True, padx=(0, 10), ipady=4)
        self.entry_msg.bind("<Return>", lambda event: self.send_message())

        btn_send = ttk.Button(frame_input, text="Enviar", command=self.send_message, style="Tonal.TButton")
        btn_send.pack(side="right")

        # EMPAQUETAMENT RESTA ESPAI NO OCUPAT
        # --- Àrea de xat ---
        frame_chat = tk.Frame(body, bg=M3.SURFACE_CONTAINER, highlightbackground=M3.OUTLINE_VARIANT,
                               highlightthickness=1, bd=0)
        frame_chat.pack(fill="both", expand=True, padx=16, pady=8)

        chat_inner = tk.Frame(frame_chat, bg=M3.SURFACE_CONTAINER)
        chat_inner.pack(fill="both", expand=True, padx=1, pady=1)

        self.chat_box = tk.Text(
            chat_inner,
            state="disabled",
            wrap="word",
            font=self.font_mono,
            bg=M3.SURFACE_CONTAINER_LOWEST,
            fg=M3.ON_SURFACE,
            insertbackground=M3.PRIMARY,
            relief="flat",
            padx=14,
            pady=12,
            highlightthickness=0,
            bd=0,
        )
        self.chat_box.pack(fill="both", expand=True, side="left", padx=10, pady=10)

        scrollbar = ttk.Scrollbar(chat_inner, command=self.chat_box.yview, style="M3.Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y", pady=10, padx=(0, 4))
        self.chat_box["yscrollcommand"] = scrollbar.set

        # Formats per als missatges (colors)
        self.chat_box.tag_configure(
            "system", foreground=M3.ON_SURFACE_VARIANT, font=(self.font_mono[0], 9, "italic"),
            justify="center", spacing1=4, spacing3=8,
        )
        self.chat_box.tag_configure(
            "sender", foreground=M3.PRIMARY, font=(self.font_mono[0], 10, "bold"), spacing1=10,
        )
        self.chat_box.tag_configure("cipher_label", foreground=M3.ON_SURFACE_VARIANT, font=(self.font_mono[0], 9))
        self.chat_box.tag_configure("cipher_text", foreground=M3.TERTIARY, font=self.font_mono)
        self.chat_box.tag_configure("plain_label", foreground=M3.ON_SURFACE_VARIANT, font=(self.font_mono[0], 9))
        self.chat_box.tag_configure(
            "plain_text", foreground=M3.ON_SURFACE, font=(self.font_mono[0], 10, "bold")
        )
        self.chat_box.tag_configure("error_text", foreground=M3.ERROR, font=(self.font_mono[0], 10, "bold"))
        self.chat_box.tag_configure(
            "divider", foreground=M3.OUTLINE_VARIANT, font=(self.font_mono[0], 8), spacing3=6,
        )

    def get_enigma_instance(self) -> EnigmaMachine:
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
            self._log_chat("[SISTEMA] Connectat amb èxit al servidor.\n", "system")

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

            # S'envia el missatge com "Usuari: TextoCifrado"
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

                self._log_message(sender, ciphertext, decrypted_text)

            except Exception:
                break

        self.connected = False
        self._log_chat("[SISTEMA] S'ha perdut la connexió amb el servidor.\n", "system")

    def _log_message(self, sender: str, ciphertext: str, decrypted_text: str):
        """Escriu un missatge rebut a l'àrea de xat en Material 3."""
        self.chat_box.config(state="normal")
        self.chat_box.insert(tk.END, f"{sender}\n", "sender")
        self.chat_box.insert(tk.END, "  Xifrat    ", "cipher_label")
        self.chat_box.insert(tk.END, f"{ciphertext}\n", "cipher_text")
        self.chat_box.insert(tk.END, "  Desxifrat ", "plain_label")
        if decrypted_text.startswith("[Error"):
            self.chat_box.insert(tk.END, f"{decrypted_text}\n", "error_text")
        else:
            self.chat_box.insert(tk.END, f"{decrypted_text}\n", "plain_text")
        self.chat_box.insert(tk.END, "─" * 46 + "\n", "divider")
        self.chat_box.see(tk.END)
        self.chat_box.config(state="disabled")

    def _log_chat(self, text: str, tag: str = None):
        self.chat_box.config(state='normal')
        if tag:
            self.chat_box.insert(tk.END, text, tag)
        else:
            self.chat_box.insert(tk.END, text)
        self.chat_box.see(tk.END)
        self.chat_box.config(state='disabled')


if __name__ == "__main__":
    root = tk.Tk()
    app = EnigmaChatApp(root)
    root.mainloop()
