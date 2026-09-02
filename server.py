import socket
import threading

HOST = '0.0.0.0'
PORT = 5555

clients = []

def broadcast(message, sender_socket):
    """Envia el missatge rebut a tots els clients connectats."""
    for client in clients:
        try:
            client.send(message)
        except Exception:
            client.close()
            if client in clients:
                clients.remove(client)

def handle_client(client_socket, address):
    print(f"[NOVA CONNEXIÓ] Client connectat des de {address}")
    clients.append(client_socket)

    while True:
        try:
            message = client_socket.recv(1024)
            if not message:
                break
            # Retransmetre el missatge (Usuari + Text xifrat) a tots els clients
            broadcast(message, client_socket)
        except Exception:
            break

    print(f"[DESCONNEXIÓ] Client {address} desconnectat.")
    if client_socket in clients:
        clients.remove(client_socket)
    client_socket.close()

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[SERVIDOR EN MARXA] Escoltant al port {PORT}...")

    while True:
        client_socket, address = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_socket, address), daemon=True)
        thread.start()

if __name__ == "__main__":
    main()